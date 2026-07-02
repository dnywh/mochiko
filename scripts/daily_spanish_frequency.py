import argparse
import base64
import csv
import json
import os
import tomllib
from pathlib import Path
from urllib.parse import urlencode
from urllib import request
from urllib.error import HTTPError

from wordfreq import top_n_list


LANGUAGE = "es"
LANGUAGE_DIR = Path("languages") / LANGUAGE
WORK_DIR = Path("work")
STATE_PATH = WORK_DIR / "daily_spanish_frequency_state.json"
DEFAULT_API_BASE = "https://app.mochi.cards/api"
DEFAULT_PARENT_DECK_ID = "khnMj1gA"
DEFAULT_TEMPLATE_ID = "tq51slCp"
DEFAULT_DAILY_LIMIT = 5
DEFAULT_CAP_RANK = 500
ROLLING_DECK_SIZE = 20
INITIAL_COMPLETED_RANK = 40
FIELDNAMES = ["rank", "word", "sentence", "tags"]


def mochi_api_key() -> str | None:
    env_key = os.environ.get("MOCHI_API_KEY")
    if env_key:
        return env_key
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
        with request.urlopen(req) as response:
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
    start = INITIAL_COMPLETED_RANK + (zero_based // ROLLING_DECK_SIZE) * ROLLING_DECK_SIZE + 1
    end = start + ROLLING_DECK_SIZE - 1
    return start, end


def batch_filename(start_rank: int, end_rank: int) -> str:
    return f"frequency_{start_rank:03d}_{end_rank:03d}.csv"


def deck_name(start_rank: int, end_rank: int) -> str:
    return f"Frequency {start_rank:03d}-{end_rank:03d}"


def csv_path_for_rank(rank: int) -> Path:
    start, end = rolling_range(rank)
    return LANGUAGE_DIR / batch_filename(start, end)


def tags_for_rank(rank: int) -> str:
    start, end = rolling_range(rank)
    return f"frequency;generated;rank-{start:03d}-{end:03d}"


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(";") if tag.strip()]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: int(row["rank"])))


def existing_source_ranks() -> set[int]:
    ranks: set[int] = set()
    for path in LANGUAGE_DIR.glob("frequency_*.csv"):
        for row in read_csv_rows(path):
            if row.get("rank"):
                ranks.add(int(row["rank"]))
    return ranks


def next_ranks(limit: int, cap_rank: int) -> list[int]:
    ranks = existing_source_ranks()
    start = max(ranks or {INITIAL_COMPLETED_RANK}) + 1
    if start > cap_rank:
        return []
    return list(range(start, min(start + limit - 1, cap_rank) + 1))


def frequency_words(cap_rank: int) -> dict[int, str]:
    return {rank: word for rank, word in enumerate(top_n_list(LANGUAGE, cap_rank), start=1)}


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
    markers = ["{{" + word + "}}", "{{" + word.capitalize() + "}}"]
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


def find_deck_by_name(api_base: str, api_key: str, name: str, parent_id: str) -> str | None:
    try:
        response = request_json(api_base, "decks/", api_key)
    except RuntimeError:
        return None
    for deck in flatten_items(response):
        if deck.get("name") == name and deck.get("parent-id") == parent_id:
            deck_id = deck.get("id")
            if isinstance(deck_id, str):
                return deck_id
    return None


def ensure_deck(
    api_base: str,
    api_key: str,
    state: dict,
    start_rank: int,
    end_rank: int,
    parent_deck_id: str,
) -> str:
    name = deck_name(start_rank, end_rank)
    state_key = f"{start_rank:03d}-{end_rank:03d}"
    known_id = state["decks"].get(state_key)
    if known_id:
        return known_id
    found_id = find_deck_by_name(api_base, api_key, name, parent_deck_id)
    if found_id:
        state["decks"][state_key] = found_id
        write_state(state)
        return found_id
    created = post_json(api_base, "decks/", api_key, {"name": name, "parent-id": parent_deck_id})
    deck_id = created.get("id")
    if not deck_id:
        raise RuntimeError(f"Create deck response did not include an id: {created}")
    state["decks"][state_key] = deck_id
    write_state(state)
    return deck_id


def card_sentence(card: dict) -> str | None:
    fields = card.get("fields")
    if isinstance(fields, dict):
        name = fields.get("name")
        if isinstance(name, dict) and isinstance(name.get("value"), str):
            return name["value"]
    return None


def existing_deck_sentences(api_base: str, api_key: str, deck_id: str) -> set[str]:
    sentences: set[str] = set()
    bookmark = None
    while True:
        query = {"deck-id": deck_id, "limit": "100"}
        if bookmark:
            query["bookmark"] = bookmark
        path = f"cards/?{urlencode(query)}"
        response = request_json(api_base, path, api_key)
        for card in flatten_items(response):
            sentence = card_sentence(card)
            if sentence:
                sentences.add(sentence)
        bookmark = response.get("bookmark") if isinstance(response, dict) else None
        if not bookmark:
            return sentences


def append_source_rows(rows: list[dict[str, str]]) -> None:
    grouped: dict[Path, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(csv_path_for_rank(int(row["rank"])), []).append(row)
    for path, new_rows in grouped.items():
        existing = read_csv_rows(path)
        by_rank = {int(row["rank"]): row for row in existing}
        for row in new_rows:
            rank = int(row["rank"])
            if rank in by_rank:
                raise ValueError(f"Rank {rank} already exists in {path}")
            by_rank[rank] = row
        write_csv_rows(path, list(by_rank.values()))


def apply_rows(
    rows: list[dict[str, str]],
    api_base: str,
    api_key: str,
    parent_deck_id: str,
    template_id: str,
) -> None:
    state = load_state()
    grouped: dict[tuple[int, int], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(rolling_range(int(row["rank"])), []).append(row)
    for (start_rank, end_rank), group in grouped.items():
        deck_id = ensure_deck(api_base, api_key, state, start_rank, end_rank, parent_deck_id)
        deck_sentences = existing_deck_sentences(api_base, api_key, deck_id)
        created_count = 0
        for row in group:
            if row["sentence"] in deck_sentences:
                print(f"Skipped existing card for rank {row['rank']}: {row['sentence']}")
                continue
            created = post_json(api_base, "cards/", api_key, build_payload(row, deck_id, template_id))
            created_count += 1
            print(f"Created card {created.get('id', '<missing id>')} for rank {row['rank']}: {row['sentence']}")
        print(f"Deck {deck_name(start_rank, end_rank)} ({deck_id}): created {created_count} card(s).")
    append_source_rows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare or apply the next daily Spanish wordfreq flashcard slice."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_DAILY_LIMIT)
    parser.add_argument("--cap-rank", type=int, default=DEFAULT_CAP_RANK)
    parser.add_argument("--sentences-json", type=Path)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--parent-deck-id", default=DEFAULT_PARENT_DECK_ID)
    parser.add_argument("--template-id", default=DEFAULT_TEMPLATE_ID)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    ranks = next_ranks(args.limit, args.cap_rank)
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

    api_key = mochi_api_key()
    if not api_key:
        raise SystemExit(
            "Set MOCHI_API_KEY before using --apply, either in the process environment "
            "or in ~/.codex/config.toml under [mcp_servers.mochi.env]."
        )
    apply_rows(rows, args.api_base, api_key, args.parent_deck_id, args.template_id)


if __name__ == "__main__":
    main()
