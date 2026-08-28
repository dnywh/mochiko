import argparse
import base64
import csv
import json
import os
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib import request
from urllib.error import HTTPError

from spanish_frequency import top_spanish_words


LANGUAGE = "es"
LANGUAGE_DIR = Path("languages") / LANGUAGE
SOURCE_PATH = LANGUAGE_DIR / "frequency.csv"
WORK_DIR = Path("work")
STATE_PATH = WORK_DIR / "daily_spanish_frequency_state.json"
DEFAULT_API_BASE = "https://app.mochi.cards/api"
DEFAULT_DECK_ID = "K7f2W8MO"
DEFAULT_TEMPLATE_ID = "tq51slCp"
DEFAULT_DAILY_LIMIT = 5
DEFAULT_CAP_RANK = 500
RANK_TAG_SIZE = 20
INITIAL_COMPLETED_RANK = 40
FIELDNAMES = ["rank", "word", "sentence", "tags"]


def repo_env_value(name: str) -> str | None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.removeprefix("export ").strip() == name:
            return value.strip().strip("\"'")
    return None


def mochi_api_key() -> str | None:
    env_key = os.environ.get("MOCHI_API_KEY")
    if env_key:
        return env_key
    repo_key = repo_env_value("MOCHI_API_KEY")
    if repo_key:
        return repo_key
    config_path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    if not config_path.exists():
        return None
    with config_path.open("rb") as f:
        config = tomllib.load(f)
    return (
        config.get("mcp_servers", {})
        .get("mochi", {})
        .get("env", {})
        .get("MOCHI_API_KEY")
    )


def auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def request_json(
    api_base: str,
    path: str,
    api_key: str,
    method: str = "GET",
    payload: dict | None = None,
) -> dict | list:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{api_base.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        method=method,
        headers={
            "Authorization": auth_header(api_key),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mochi API error {error.code}: {detail}") from error
    return json.loads(raw) if raw else {}


def post_json(api_base: str, path: str, api_key: str, payload: dict) -> dict:
    data = request_json(api_base, path, api_key, method="POST", payload=payload)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected object response from POST {path}, got: {data}")
    return data


def flatten_items(response: dict | list) -> list[dict]:
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    for key in ("docs", "items", "data", "decks", "cards"):
        value = response.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def parse_api_date(value: dict | None) -> datetime | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("date")
    if not isinstance(raw, str):
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def parse_api_day(value: dict | None):
    parsed = parse_api_date(value)
    if not parsed:
        return None
    return parsed.date()


def parse_state_date(value: str | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"decks": {}}
    with STATE_PATH.open(encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("decks", {})
    return state


def write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def rolling_range(rank: int) -> tuple[int, int]:
    zero_based = rank - INITIAL_COMPLETED_RANK - 1
    start = (
        INITIAL_COMPLETED_RANK
        + (zero_based // RANK_TAG_SIZE) * RANK_TAG_SIZE
        + 1
    )
    end = start + RANK_TAG_SIZE - 1
    return start, end


def tags_for_rank(rank: int) -> str:
    start, end = rolling_range(rank)
    return f"frequency;generated;rank-{start:03d}-{end:03d}"


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(";") if tag.strip()]


def read_source_rows() -> list[dict[str, str]]:
    if not SOURCE_PATH.exists():
        return []
    with SOURCE_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_source_rows(rows: list[dict[str, str]]) -> None:
    SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SOURCE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: int(row["rank"])))


def existing_source_ranks() -> set[int]:
    return {
        int(row["rank"])
        for row in read_source_rows()
        if row.get("rank")
    }


def iter_cards(api_base: str, api_key: str, deck_id: str | None = None) -> list[dict]:
    cards: list[dict] = []
    bookmark = None
    seen_bookmarks: set[str] = set()
    while True:
        query = {"limit": "100"}
        if deck_id:
            query["deck-id"] = deck_id
        if bookmark:
            query["bookmark"] = bookmark
        path = f"cards/?{urlencode(query)}"
        response = request_json(api_base, path, api_key)
        page_items = flatten_items(response)
        cards.extend(page_items)
        next_bookmark = response.get("bookmark") if isinstance(response, dict) else None
        if next_bookmark in (None, "", "nil"):
            return cards
        if next_bookmark == bookmark or next_bookmark in seen_bookmarks:
            return cards
        if not page_items:
            return cards
        seen_bookmarks.add(next_bookmark)
        bookmark = next_bookmark


def review_within_hours(card: dict, since: datetime) -> bool:
    since_day = since.date()
    reviews = card.get("reviews")
    if not isinstance(reviews, list):
        return False
    for review in reviews:
        review_day = parse_api_day(review.get("date") if isinstance(review, dict) else None)
        if review_day and review_day >= since_day:
            return True
    return False


def recent_activity_snapshot(
    api_base: str,
    api_key: str,
    recent_study_hours: int,
) -> dict[str, int | bool | str | None]:
    now = datetime.now().astimezone()
    study_since = now - timedelta(hours=recent_study_hours)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    recent_study = False
    created_today = 0
    latest_review_day = None
    review_count = 0

    for card in iter_cards(api_base, api_key):
        created_at = parse_api_date(card.get("created-at"))
        if created_at and created_at.astimezone(now.tzinfo) >= day_start:
            created_today += 1
        reviews = card.get("reviews")
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            review_count += 1
            review_day = parse_api_day(review.get("date") if isinstance(review, dict) else None)
            if not review_day:
                continue
            if latest_review_day is None or review_day > latest_review_day:
                latest_review_day = review_day
            if not recent_study and review_day >= study_since.date():
                recent_study = True

    return {
        "created_today": created_today,
        "recent_study": recent_study,
        "latest_review_day": latest_review_day.isoformat() if latest_review_day else None,
        "review_count": review_count,
    }


def observe_review_count_increase(
    state: dict,
    review_count: int,
    recent_study_hours: int,
    now: datetime,
) -> bool:
    activity_state = state.setdefault("activity", {})
    previous_count = activity_state.get("review_count")
    observed_at = parse_state_date(activity_state.get("review_count_increased_at"))

    if isinstance(previous_count, int) and review_count > previous_count:
        observed_at = now
        activity_state["review_count_increased_at"] = now.isoformat()

    activity_state["review_count"] = review_count
    write_state(state)

    if not observed_at:
        return False
    return observed_at >= now - timedelta(hours=recent_study_hours)


def next_ranks(limit: int, cap_rank: int) -> list[int]:
    ranks = existing_source_ranks()
    start = max(ranks or {INITIAL_COMPLETED_RANK}) + 1
    if start > cap_rank:
        return []
    return list(range(start, min(start + limit - 1, cap_rank) + 1))


def frequency_words(cap_rank: int) -> dict[int, str]:
    return {rank: word for rank, word in enumerate(top_spanish_words(cap_rank), start=1)}


def load_sentence_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Sentence JSON must be a list or an object with a rows list.")
    normalised = []
    for row in rows:
        normalised.append(
            {
                "rank": str(row["rank"]),
                "word": str(row["word"]),
                "sentence": str(row["sentence"]),
                "tags": str(row.get("tags") or tags_for_rank(int(row["rank"]))),
            }
        )
    return normalised


def validate_sentence(word: str, sentence: str) -> None:
    markers = {"{{" + word + "}}", "{{" + word.capitalize() + "}}"}
    total = sum(sentence.count(marker) for marker in markers)
    if total != 1:
        raise ValueError(f"{word!r} must appear as exactly one cloze in {sentence!r}")
    if sentence.count("{{") != 1 or sentence.count("}}") != 1:
        raise ValueError(f"{word!r} must have exactly one cloze pair in {sentence!r}")


def validate_rows(rows: list[dict[str, str]], expected_ranks: list[int], words: dict[int, str]) -> None:
    seen_ranks = [int(row["rank"]) for row in rows]
    if seen_ranks != expected_ranks:
        raise ValueError(f"Expected ranks {expected_ranks}, got {seen_ranks}")
    sentences: set[str] = set()
    for row in rows:
        rank = int(row["rank"])
        expected_word = words[rank]
        if row["word"] != expected_word:
            raise ValueError(f"Rank {rank} must use {expected_word!r}, got {row['word']!r}")
        validate_sentence(row["word"], row["sentence"])
        if row["sentence"] in sentences:
            raise ValueError(f"Duplicate sentence in batch: {row['sentence']!r}")
        sentences.add(row["sentence"])


def build_payload(row: dict[str, str], deck_id: str, template_id: str) -> dict:
    validate_sentence(row["word"], row["sentence"])
    return {
        "content": "",
        "deck-id": deck_id,
        "template-id": template_id,
        "fields": {
            "name": {
                "id": "name",
                "value": row["sentence"],
            }
        },
        "manual-tags": parse_tags(row["tags"]),
    }


def card_sentence(card: dict) -> str | None:
    fields = card.get("fields")
    if isinstance(fields, dict):
        name = fields.get("name")
        if isinstance(name, dict) and isinstance(name.get("value"), str):
            return name["value"]
    return None


def existing_deck_sentences(api_base: str, api_key: str, deck_id: str) -> set[str]:
    sentences: set[str] = set()
    for card in iter_cards(api_base, api_key, deck_id=deck_id):
        sentence = card_sentence(card)
        if sentence:
            sentences.add(sentence)
    return sentences


def append_source_rows(rows: list[dict[str, str]]) -> None:
    existing = read_source_rows()
    by_rank = {int(row["rank"]): row for row in existing}
    for row in rows:
        rank = int(row["rank"])
        if rank in by_rank:
            raise ValueError(f"Rank {rank} already exists in {SOURCE_PATH}")
        by_rank[rank] = row
    write_source_rows(list(by_rank.values()))


def apply_rows(
    rows: list[dict[str, str]],
    api_base: str,
    api_key: str,
    deck_id: str,
    template_id: str,
) -> None:
    deck_sentences = existing_deck_sentences(api_base, api_key, deck_id)
    created_count = 0
    skipped_count = 0
    for row in rows:
        if row["sentence"] in deck_sentences:
            skipped_count += 1
            print(f"Skipped existing card for rank {row['rank']}: {row['sentence']}")
            continue
        created = post_json(
            api_base,
            "cards/",
            api_key,
            build_payload(row, deck_id, template_id),
        )
        created_count += 1
        print(
            f"Created card {created.get('id', '<missing id>')} for rank "
            f"{row['rank']}: {row['sentence']}"
        )
    print(
        f"Deck Frequency ({deck_id}): created {created_count} card(s); "
        f"skipped {skipped_count} duplicate(s)."
    )
    append_source_rows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare or apply the next daily Spanish wordfreq flashcard slice."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_DAILY_LIMIT)
    parser.add_argument("--cap-rank", type=int, default=DEFAULT_CAP_RANK)
    parser.add_argument("--sentences-json", type=Path)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--deck-id", default=DEFAULT_DECK_ID)
    parser.add_argument("--template-id", default=DEFAULT_TEMPLATE_ID)
    parser.add_argument("--require-recent-study-hours", type=int, default=0)
    parser.add_argument("--daily-created-cap", type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    api_key = None
    effective_limit = args.limit
    if args.require_recent_study_hours or args.daily_created_cap is not None or args.apply:
        api_key = mochi_api_key()
    if args.require_recent_study_hours or args.daily_created_cap is not None:
        if not api_key:
            print("Skipped: MOCHI_API_KEY is required to inspect recent Mochi activity.")
            return
        try:
            activity = recent_activity_snapshot(
                args.api_base,
                api_key,
                recent_study_hours=max(args.require_recent_study_hours, 0),
            )
        except RuntimeError as error:
            print(f"Skipped: could not inspect recent Mochi activity: {error}")
            return

        if args.require_recent_study_hours:
            state = load_state()
            review_count_increased_recently = observe_review_count_increase(
                state,
                int(activity["review_count"]),
                args.require_recent_study_hours,
                datetime.now().astimezone(),
            )
            if not activity["recent_study"] and not review_count_increased_recently:
                latest_review_note = ""
                latest_review_day = activity.get("latest_review_day")
                if isinstance(latest_review_day, str) and latest_review_day:
                    latest_review_note = (
                        " Latest review day visible via the Mochi API: "
                        f"{latest_review_day}."
                    )
                print(
                    "Skipped: no Mochi review activity found in the last "
                    f"{args.require_recent_study_hours} hour(s).{latest_review_note}"
                )
                return
            if activity["recent_study"]:
                print(
                    "Recent Mochi review activity found in the last "
                    f"{args.require_recent_study_hours} hour(s), using Mochi's "
                    "day-level review dates."
                )
            else:
                print(
                    "Recent Mochi review activity found from newly synced review "
                    "records since the previous activity inspection."
                )

        if args.daily_created_cap is not None:
            created_today = int(activity["created_today"])
            remaining = max(0, args.daily_created_cap - created_today)
            print(
                f"Mochi cards created today: {created_today}. "
                f"Remaining scheduled slots today: {remaining}."
            )
            if remaining <= 0:
                print(
                    f"Skipped: daily created-card cap of {args.daily_created_cap} "
                    "has already been reached."
                )
                return
            effective_limit = min(effective_limit, remaining)

    ranks = next_ranks(effective_limit, args.cap_rank)
    words = frequency_words(args.cap_rank)
    if not ranks:
        print(f"Approved frequency range is complete through rank {args.cap_rank}.")
        return

    print("Next ranks:")
    for rank in ranks:
        print(f"{rank:03d}. {words[rank]}")

    if not args.sentences_json:
        print("\nNo sentence JSON supplied. No Mochi writes performed.")
        return

    rows = load_sentence_rows(args.sentences_json)
    validate_rows(rows, ranks, words)
    print("\nValidated rows:")
    for row in rows:
        print(f"{int(row['rank']):03d}. {row['word']}: {row['sentence']} -> {row['tags']}")

    if not args.apply:
        print(f"\nPrepared {len(rows)} row(s). No Mochi writes performed.")
        return

    if not api_key:
        raise SystemExit(
            "Set MOCHI_API_KEY before using --apply, in the process environment, "
            "the repo-local .env file, or ~/.codex/config.toml under [mcp_servers.mochi.env]."
        )
    apply_rows(rows, args.api_base, api_key, args.deck_id, args.template_id)


if __name__ == "__main__":
    main()
