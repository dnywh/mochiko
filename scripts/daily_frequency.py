import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from daily_german_frequency import top_german_words
from daily_spanish_frequency import (
    card_sentence,
    iter_cards,
    load_state,
    mochi_api_key,
    parse_api_date,
    parse_api_day,
    post_json,
    write_state,
)
from spanish_frequency import top_spanish_words


MELBOURNE = ZoneInfo("Australia/Melbourne")
CAP_RANK = 500
VARIANTS_PER_WORD = 3
SOURCE_FIELDS = ["rank", "variant", "word", "sentence", "tags"]


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    source: Path
    bank: Path
    deck_id: str
    template_id: str
    daily_word_cap: int


LANGUAGES = (
    Language(
        code="es",
        name="Spanish",
        source=Path("languages/es/frequency.csv"),
        bank=Path("languages/es/frequency_sentence_bank.csv"),
        deck_id="K7f2W8MO",
        template_id="tq51slCp",
        daily_word_cap=1,
    ),
    Language(
        code="de",
        name="German",
        source=Path("languages/de/frequency.csv"),
        bank=Path("languages/de/frequency_sentence_bank.csv"),
        deck_id="r2i5qXk7",
        template_id="xo7aEe7Q",
        daily_word_cap=3,
    ),
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], check=check, capture_output=True, text=True
    )


def git_preflight(fetch: bool) -> None:
    if git("branch", "--show-current").stdout.strip() != "main":
        raise RuntimeError("Git preflight failed: current branch is not main.")
    if fetch:
        git("fetch", "origin", "main")
    behind = int(
        git("rev-list", "--right-only", "--count", "main...origin/main")
        .stdout.strip()
    )
    if behind:
        raise RuntimeError(f"Git preflight failed: main is behind origin/main by {behind}.")
    if git("diff", "--cached", "--name-only").stdout.strip():
        raise RuntimeError("Git preflight failed: staged changes are present.")
    changed = git(
        "status",
        "--short",
        "--",
        *(str(language.source) for language in LANGUAGES),
    ).stdout.strip()
    if changed:
        raise RuntimeError("Git preflight failed: a frequency source has existing changes.")


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            sorted(rows, key=lambda row: (int(row["rank"]), int(row["variant"])))
        )


def words_for(language: Language) -> dict[int, str]:
    words = (
        top_spanish_words(CAP_RANK)
        if language.code == "es"
        else top_german_words(CAP_RANK)
    )
    return dict(enumerate(words, start=1))


def validate_sentence(word: str, sentence: str) -> None:
    markers = ("{{" + word + "}}", "{{" + word.capitalize() + "}}")
    if sum(sentence.count(marker) for marker in markers) != 1:
        raise ValueError(f"{word!r} must appear in exactly one cloze: {sentence!r}")
    if sentence.count("{{") != 1 or sentence.count("}}") != 1:
        raise ValueError(f"Expected one cloze pair: {sentence!r}")
    visible = sentence
    for marker in markers:
        visible = visible.replace(marker, "")
    if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", visible, re.IGNORECASE):
        raise ValueError(f"{word!r} also appears outside the cloze: {sentence!r}")


def next_rank(language: Language) -> int | None:
    ranks = [int(row["rank"]) for row in read_rows(language.source) if row.get("rank")]
    rank = max(ranks or ([40] if language.code == "es" else [0])) + 1
    return rank if rank <= CAP_RANK else None


def bank_slice(language: Language, ranks: list[int]) -> list[dict[str, str]]:
    expected_words = words_for(language)
    selected = [row for row in read_rows(language.bank) if int(row["rank"]) in ranks]
    expected = [(rank, variant) for rank in ranks for variant in range(1, 4)]
    actual = [(int(row["rank"]), int(row["variant"])) for row in selected]
    if actual != expected:
        raise RuntimeError(f"{language.name} sentence bank does not contain complete trios for {ranks}.")
    sentences: set[str] = set()
    for row in selected:
        rank = int(row["rank"])
        variant = int(row["variant"])
        if row["word"] != expected_words[rank]:
            raise RuntimeError(f"{language.name} rank {rank} has the wrong frequency word.")
        if variant not in (1, 2, 3):
            raise RuntimeError(f"{language.name} rank {rank} has invalid variant {variant}.")
        validate_sentence(row["word"], row["sentence"])
        if row["sentence"] in sentences:
            raise RuntimeError(f"{language.name} sentence bank contains a duplicate sentence.")
        sentences.add(row["sentence"])
    return selected


def tags(card: dict) -> set[str]:
    raw = card.get("manual-tags", card.get("tags", []))
    if isinstance(raw, dict):
        raw = raw.values()
    if not isinstance(raw, (list, tuple, set)):
        return set()
    result = set()
    for item in raw:
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, dict):
            value = item.get("name") or item.get("value")
            if isinstance(value, str):
                result.add(value)
    return result


def card_deck_id(card: dict) -> str | None:
    value = card.get("deck-id")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        nested = value.get("id")
        return nested if isinstance(nested, str) else None
    return None


def recent_activity(cards: list[dict], hours: int, now: datetime) -> tuple[bool, int, str | None]:
    since = now - timedelta(hours=hours)
    latest = None
    count = 0
    recent = False
    for card in cards:
        reviews = card.get("reviews")
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            count += 1
            day = parse_api_day(review if isinstance(review, dict) else None)
            if day and (latest is None or day > latest):
                latest = day
            if day and day >= since.date():
                recent = True
    return recent, count, latest.isoformat() if latest else None


def observe_activity(count: int, hours: int, now: datetime) -> bool:
    state = load_state()
    activity = state.setdefault("activity", {})
    previous = activity.get("review_count")
    observed_raw = activity.get("review_count_increased_at")
    observed = datetime.fromisoformat(observed_raw) if isinstance(observed_raw, str) else None
    if isinstance(previous, int) and count > previous:
        observed = now
        activity["review_count_increased_at"] = now.isoformat()
    activity["review_count"] = count
    write_state(state)
    return bool(observed and observed >= now - timedelta(hours=hours))


def rank_tag(rank: int) -> str:
    return f"frequency-rank-{rank:03d}"


def started_today(cards: list[dict], language: Language, now: datetime) -> set[int]:
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ranks: set[int] = set()
    prefix = "frequency-rank-"
    for card in cards:
        if card_deck_id(card) != language.deck_id:
            continue
        created = parse_api_date(card.get("created-at"))
        if not created or created.astimezone(MELBOURNE) < day_start:
            continue
        for tag in tags(card):
            if tag.startswith(prefix) and tag.removeprefix(prefix).isdigit():
                ranks.add(int(tag.removeprefix(prefix)))
    return ranks


def deck_sentences(cards: list[dict], deck_id: str) -> set[str]:
    return {
        sentence
        for card in cards
        if card_deck_id(card) == deck_id
        if (sentence := card_sentence(card))
    }


def approved_ranks(first: int, started: set[int], daily_cap: int) -> list[int]:
    unfinished = sorted(rank for rank in started if rank >= first)
    new_slots = max(0, daily_cap - len(started))
    last = max(unfinished, default=first - 1) + new_slots
    if unfinished:
        last = max(last, unfinished[-1])
    if last < first:
        return []
    return list(range(first, min(last, CAP_RANK) + 1))


def payload(language: Language, row: dict[str, str]) -> dict:
    rank = int(row["rank"])
    variant = int(row["variant"])
    base_tags = [tag for tag in row["tags"].split(";") if tag]
    return {
        "content": "",
        "deck-id": language.deck_id,
        "template-id": language.template_id,
        "fields": {"name": {"id": "name", "value": row["sentence"]}},
        "manual-tags": [*base_tags, rank_tag(rank), f"variant-{variant}"],
    }


def append_source(language: Language, rows: list[dict[str, str]]) -> None:
    existing = read_rows(language.source)
    normalised = [
        {**row, "variant": row.get("variant") or "1"}
        for row in existing
    ]
    keys = {(int(row["rank"]), int(row["variant"])) for row in normalised}
    for row in rows:
        key = (int(row["rank"]), int(row["variant"]))
        if key not in keys:
            normalised.append(row)
            keys.add(key)
    write_rows(language.source, normalised)


def publish(date: str) -> str:
    allowed = [str(language.source) for language in LANGUAGES]
    git("diff", "--check", "--", *allowed)
    git("add", *allowed)
    staged = git("diff", "--cached", "--name-only").stdout.splitlines()
    if not staged:
        return "no source changes"
    if set(staged) - set(allowed):
        raise RuntimeError(f"Refusing unexpected staged files: {staged}")
    git("commit", "-m", f"daily frequency cards: {date}")
    git("push", "origin", "main")
    return git("rev-parse", "--short", "HEAD").stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run both governed daily frequency workflows.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--validate-banks", action="store_true")
    parser.add_argument("--api-base", default="https://app.mochi.cards/api")
    parser.add_argument("--require-recent-study-hours", type=int, default=24)
    args = parser.parse_args()
    if args.publish and not args.apply:
        raise SystemExit("--publish requires --apply")

    if args.validate_banks:
        for language in LANGUAGES:
            rows = read_rows(language.bank)
            ranks = sorted({int(row["rank"]) for row in rows})
            bank_slice(language, ranks)
        print(json.dumps({"status": "ok", "banks": "valid"}))
        return

    git_preflight(fetch=not args.skip_fetch)
    api_key = mochi_api_key()
    if not api_key:
        raise SystemExit("Blocked: MOCHI_API_KEY is unavailable.")

    cards = iter_cards(args.api_base, api_key)
    now = datetime.now(MELBOURNE)
    recent, review_count, latest = recent_activity(
        cards, args.require_recent_study_hours, now
    )
    recently_increased = observe_activity(
        review_count, args.require_recent_study_hours, now
    )
    if not recent and not recently_increased:
        raise SystemExit(f"Blocked: no recent Mochi review activity. Latest review day: {latest}.")

    results = []
    for language in LANGUAGES:
        first = next_rank(language)
        if first is None:
            results.append(f"{language.name}: complete through rank {CAP_RANK}")
            continue
        started = started_today(cards, language, now)
        ranks = approved_ranks(first, started, language.daily_word_cap)
        if not ranks:
            results.append(f"{language.name}: daily word cap reached")
            continue
        rows = bank_slice(language, ranks)
        if not args.apply:
            results.append(f"{language.name}: ready ranks {ranks[0]}-{ranks[-1]} ({len(rows)} cards)")
            continue
        existing = deck_sentences(cards, language.deck_id)
        created = skipped = 0
        for row in rows:
            if row["sentence"] in existing:
                skipped += 1
                continue
            post_json(args.api_base, "cards/", api_key, payload(language, row))
            existing.add(row["sentence"])
            created += 1
        append_source(language, rows)
        results.append(
            f"{language.name}: ranks {ranks[0]}-{ranks[-1]}, created {created}, skipped {skipped}"
        )

    commit = publish(now.date().isoformat()) if args.publish else "not requested"
    print(json.dumps({"status": "ok", "results": results, "commit": commit}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or str(error)).strip()
        print(json.dumps({"status": "blocked", "error": detail}))
        raise SystemExit(1) from None
    except (RuntimeError, OSError, ValueError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        raise SystemExit(1) from None
