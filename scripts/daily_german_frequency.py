import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from wordfreq import top_n_list

from daily_spanish_frequency import (
    card_sentence,
    iter_cards,
    load_state,
    mochi_api_key,
    observe_review_count_increase,
    parse_api_date,
    post_json,
    recent_activity_snapshot,
    validate_sentence,
)


LANGUAGE_DIR = Path("languages/de")
SOURCE_PATH = LANGUAGE_DIR / "frequency.csv"
DEFAULT_API_BASE = "https://app.mochi.cards/api"
DEFAULT_DECK_ID = "r2i5qXk7"
DEFAULT_TEMPLATE_ID = "xo7aEe7Q"
DEFAULT_DAILY_LIMIT = 3
DEFAULT_CAP_RANK = 500
FIELDNAMES = ["rank", "word", "sentence", "tags"]
TAGS = "frequency;generated;german"


def top_german_words(limit: int) -> list[str]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit == 0:
        return []
    candidate_limit = limit
    while True:
        candidates = top_n_list("de", candidate_limit)
        words = [word for word in candidates if word.isalpha()]
        if len(words) >= limit:
            return words[:limit]
        if len(candidates) < candidate_limit:
            raise ValueError(f"wordfreq returned only {len(words)} German word tokens")
        candidate_limit *= 2


def read_source_rows() -> list[dict[str, str]]:
    if not SOURCE_PATH.exists():
        return []
    with SOURCE_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def next_ranks(limit: int, cap_rank: int) -> list[int]:
    ranks = {int(row["rank"]) for row in read_source_rows() if row.get("rank")}
    start = max(ranks or {0}) + 1
    if start > cap_rank:
        return []
    return list(range(start, min(start + limit - 1, cap_rank) + 1))


def load_sentence_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Sentence JSON must be a list or an object with a rows list.")
    return [
        {
            "rank": str(row["rank"]),
            "word": str(row["word"]),
            "sentence": str(row["sentence"]),
            "tags": str(row.get("tags") or TAGS),
        }
        for row in rows
    ]


def validate_rows(
    rows: list[dict[str, str]],
    expected_ranks: list[int],
    words: dict[int, str],
) -> None:
    seen_ranks = [int(row["rank"]) for row in rows]
    if seen_ranks != expected_ranks:
        raise ValueError(f"Expected ranks {expected_ranks}, got {seen_ranks}")
    sentences: set[str] = set()
    for row in rows:
        rank = int(row["rank"])
        if row["word"] != words[rank]:
            raise ValueError(
                f"Rank {rank} must use {words[rank]!r}, got {row['word']!r}"
            )
        validate_sentence(row["word"], row["sentence"])
        if row["sentence"] in sentences:
            raise ValueError(f"Duplicate sentence in batch: {row['sentence']!r}")
        sentences.add(row["sentence"])


def created_in_deck_today(api_base: str, api_key: str, deck_id: str) -> int:
    now = datetime.now().astimezone()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    created_today = 0
    for card in iter_cards(api_base, api_key, deck_id=deck_id):
        created_at = parse_api_date(card.get("created-at"))
        if created_at and created_at.astimezone(now.tzinfo) >= day_start:
            created_today += 1
    return created_today


def build_payload(row: dict[str, str], deck_id: str, template_id: str) -> dict:
    return {
        "content": "",
        "deck-id": deck_id,
        "template-id": template_id,
        "fields": {"name": {"id": "name", "value": row["sentence"]}},
        "manual-tags": [tag for tag in row["tags"].split(";") if tag],
    }


def append_source_rows(rows: list[dict[str, str]]) -> None:
    existing = read_source_rows()
    by_rank = {int(row["rank"]): row for row in existing}
    for row in rows:
        rank = int(row["rank"])
        if rank in by_rank:
            raise ValueError(f"Rank {rank} already exists in {SOURCE_PATH}")
        by_rank[rank] = row
    SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SOURCE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(by_rank[rank] for rank in sorted(by_rank))


def apply_rows(
    rows: list[dict[str, str]],
    api_base: str,
    api_key: str,
    deck_id: str,
    template_id: str,
) -> None:
    existing_sentences = {
        sentence
        for card in iter_cards(api_base, api_key, deck_id=deck_id)
        if (sentence := card_sentence(card))
    }
    created_count = 0
    skipped_count = 0
    for row in rows:
        if row["sentence"] in existing_sentences:
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
    append_source_rows(rows)
    print(
        f"Deck Frequency ({deck_id}): created {created_count} card(s); "
        f"skipped {skipped_count} duplicate(s)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare or apply the next daily German wordfreq flashcard slice."
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
        activity = recent_activity_snapshot(
            args.api_base,
            api_key,
            recent_study_hours=max(args.require_recent_study_hours, 0),
        )
        if args.require_recent_study_hours:
            state = load_state()
            increased_recently = observe_review_count_increase(
                state,
                int(activity["review_count"]),
                args.require_recent_study_hours,
                datetime.now().astimezone(),
            )
            if not activity["recent_study"] and not increased_recently:
                latest = activity.get("latest_review_day")
                note = (
                    f" Latest review day visible via the Mochi API: {latest}."
                    if latest
                    else ""
                )
                print(
                    "Skipped: no Mochi review activity found in the last "
                    f"{args.require_recent_study_hours} hour(s).{note}"
                )
                return
            source = (
                "day-level review dates"
                if activity["recent_study"]
                else "newly synced review records"
            )
            print(f"Recent Mochi review activity found from {source}.")
        if args.daily_created_cap is not None:
            created_today = created_in_deck_today(
                args.api_base, api_key, args.deck_id
            )
            remaining = max(0, args.daily_created_cap - created_today)
            print(
                f"German frequency cards created today: {created_today}. "
                f"Remaining scheduled slots today: {remaining}."
            )
            if remaining <= 0:
                print(
                    f"Skipped: German daily created-card cap of "
                    f"{args.daily_created_cap} has already been reached."
                )
                return
            effective_limit = min(effective_limit, remaining)

    ranks = next_ranks(effective_limit, args.cap_rank)
    words = {
        rank: word
        for rank, word in enumerate(top_german_words(args.cap_rank), start=1)
    }
    if not ranks:
        print(f"Approved German frequency range is complete through rank {args.cap_rank}.")
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
        print(
            f"{int(row['rank']):03d}. {row['word']}: "
            f"{row['sentence']} -> {row['tags']}"
        )
    if not args.apply:
        print(f"\nPrepared {len(rows)} row(s). No Mochi writes performed.")
        return
    if not api_key:
        raise SystemExit("Set MOCHI_API_KEY before using --apply.")
    apply_rows(rows, args.api_base, api_key, args.deck_id, args.template_id)


if __name__ == "__main__":
    main()
