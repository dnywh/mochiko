import argparse
import base64
import csv
import json
import os
from pathlib import Path
from urllib import request
from urllib.error import HTTPError


DEFAULT_TEMPLATE_ID = "tq51slCp"
PLACEHOLDER_DECK_ID = "REPLACE_WITH_MOCHI_DECK_ID"
DEFAULT_API_BASE = "https://app.mochi.cards/api"


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(";") if tag.strip()]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = {"rank", "word", "sentence", "tags"}
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    return rows


def validate_sentence(word: str, sentence: str) -> None:
    markers = ["{{" + word + "}}", "{{" + word.capitalize() + "}}"]
    total = sum(sentence.count(marker) for marker in markers)
    if total != 1:
        raise ValueError(f"{word!r} must appear as exactly one cloze in {sentence!r}")
    if sentence.count("{{") != 1 or sentence.count("}}") != 1:
        raise ValueError(f"{word!r} must have exactly one cloze pair in {sentence!r}")


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


def auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def post_json(api_base: str, path: str, api_key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{api_base.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        method="POST",
        headers={
            "Authorization": auth_header(api_key),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mochi API error {error.code}: {detail}") from error


def create_deck(api_base: str, api_key: str, name: str, parent_id: str | None) -> str:
    payload = {"name": name}
    if parent_id:
        payload["parent-id"] = parent_id
    created = post_json(api_base, "decks/", api_key, payload)
    deck_id = created.get("id")
    if not deck_id:
        raise RuntimeError(f"Create deck response did not include an id: {created}")
    return deck_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare Mochi create_card payloads from a Mochiko CSV batch."
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--deck-id", default=PLACEHOLDER_DECK_ID)
    parser.add_argument(
        "--create-deck-name",
        help="Create a Mochi deck with this name before importing cards.",
    )
    parser.add_argument(
        "--parent-deck-id",
        help="Optional parent deck ID when creating a deck.",
    )
    parser.add_argument("--template-id", default=DEFAULT_TEMPLATE_ID)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--jsonl-output",
        type=Path,
        help="Write create_card payloads to this JSONL file.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Reserved for a future direct Mochi API/MCP backend. Currently refused.",
    )
    args = parser.parse_args()

    rows = load_rows(args.csv_path)
    deck_id = args.deck_id
    payloads = [build_payload(row, deck_id, args.template_id) for row in rows]

    for row, payload in zip(rows, payloads):
        print(
            f"{int(row['rank']):03d}. {row['word']}: "
            f"{payload['fields']['name']['value']} -> {payload['manual-tags']}"
        )

    if args.jsonl_output:
        args.jsonl_output.parent.mkdir(parents=True, exist_ok=True)
        with args.jsonl_output.open("w", encoding="utf-8") as f:
            for payload in payloads:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print(f"\nWrote {args.jsonl_output}")

    if not args.apply:
        print(f"\nPrepared {len(payloads)} create_card payloads. No Mochi writes performed.")
        return

    api_key = os.environ.get("MOCHI_API_KEY")
    if not api_key:
        raise SystemExit("Set MOCHI_API_KEY before using --apply.")

    if args.create_deck_name:
        deck_id = create_deck(args.api_base, api_key, args.create_deck_name, args.parent_deck_id)
        payloads = [build_payload(row, deck_id, args.template_id) for row in rows]
        print(f"\nCreated deck {args.create_deck_name!r}: {deck_id}")
    elif deck_id == PLACEHOLDER_DECK_ID:
        raise SystemExit("Pass --deck-id or --create-deck-name before using --apply.")

    created_ids = []
    for payload in payloads:
        created = post_json(args.api_base, "cards/", api_key, payload)
        created_ids.append(created.get("id", "<missing id>"))
        print(f"Created card {created_ids[-1]}: {payload['fields']['name']['value']}")

    print(f"\nCreated {len(created_ids)} cards in deck {deck_id}.")


if __name__ == "__main__":
    main()
