# Mochiko

Mochiko is a playbook and toolbench for generating language-learning flashcards for [Mochi](https://mochi.cards/).

It keeps durable instructions, templates, scripts, and formal source artefacts in this repo. Mochi remains the source of truth for cards after import, especially for messy "from the wild" captures that are reviewed in chat and written directly with the Mochi MCP/API.

Spanish is the current pilot language. German is a planned future language, so reusable copy and tooling should stay language-general unless it is explicitly documenting Spanish.

## Current Mochi State

- Parent Spanish deck: `Spanish` (`khnMj1gA`)
- Wild Spanish deck: `Wild` (`bxo7vr1h`)
- Spanish frequency deck: `Frequency 001-020` (`MNmR28ru`)
- Spanish frequency deck: `Frequency 021-040` (`juLri2Ke`)
- Spanish numbers deck: `Numbers 010-032` (`cGTBD2MJ`)
- Recommended Spanish template: `Mochiko Language with Audio` (`tq51slCp`)
- Original Spanish template: `Language with Audio` (`NzSvxUDF`)
- Superseded v2 template: `Language with Audio v2 Inline` (`KHhX0rbi`)
- Avoid first attempted v2 template: `Language with Audio v2` (`rdCJTaM9`)

## Workflows

See [docs/flashcard-workflow.md](docs/flashcard-workflow.md) for the canonical workflow.

- Formal decks such as frequency lists, number ranges, and structured drills should be committed under `languages/<language-code>/` and imported through reusable tooling.
- Wild captures should usually be normalised, reviewed in chat, and imported directly to Mochi. Do not add one-off wild CSVs unless the user asks to preserve source files.
- Every generated card should use exactly one cloze pair, for example:

```text
Soy {{de}} Perú.
```

## Repo Layout

- `languages/es/frequency_001_020.csv` - Spanish frequency source for ranks 1-20.
- `languages/es/frequency_021_040.csv` - Spanish frequency source for ranks 21-40.
- `languages/es/numbers_010_032.csv` - Spanish number source for 10-32.
- `scripts/generate_spanish_frequency_batches.py` - Spanish frequency batch generator.
- `scripts/import_mochi_batch.py` - reusable CSV-to-Mochi preview/import helper.
- `templates/mochiko_language_with_audio.md` - source for the recommended Mochiko template.
- `docs/flashcard-workflow.md` - detailed workflow and guardrails.
- `skills/mochiko-flashcards/` - repo-shared Codex skill for portable agent guidance.

Future German formal sources should live under `languages/de/` after German deck IDs, template decisions, language defaults, and source material are chosen.

## Setup

Install dependencies into the ignored local work directory:

```sh
python3 -m pip install --target work/python-packages wordfreq
```

Regenerate the current Spanish pilot preview:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_pilot.py
```

Generate a specific Spanish frequency batch:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_batches.py --start-rank 21 --end-rank 40
```

## Importing Formal CSV Batches

Preview Mochi `create_card` payloads without writing:

```sh
python3 scripts/import_mochi_batch.py languages/es/frequency_021_040.csv --jsonl-output outputs/mochi_create_card_frequency_021_040.jsonl
```

Import with the official Mochi API only after review:

```sh
export MOCHI_API_KEY=...
python3 scripts/import_mochi_batch.py languages/es/frequency_021_040.csv \
  --create-deck-name "Frequency 021-040" \
  --parent-deck-id khnMj1gA \
  --template-id tq51slCp \
  --apply
```

The importer uses Mochi's `POST /cards` API and Basic auth with the API key as the username. The JSONL output is only a review or handoff artefact; Mochi cannot import it directly.

## Source Material

The current Spanish frequency batches use `wordfreq` to rank common Spanish terms, with manually authored beginner sentences around those terms.

Useful source material for expanding the project, especially German:

- [Fluent Forever Base Vocabulary List](https://method.fluent-forever.com/base-vocabulary-list/)
- [General Service List](https://en.wikipedia.org/wiki/General_Service_List)
- [`625-words-fluent-forever-output.csv`](https://github.com/kelvinn/the-625-list/blob/master/625-words-fluent-forever-output.csv)

## Template And AI-Credit Notes

`templates/mochiko_language_with_audio.md` matches the recommended live Mochi template `Mochiko Language with Audio` (`tq51slCp`). It uses inline speech blocks for both slow and fast audio because the exposed Mochi `create_template` tool did not preserve the original template's speech-field `source` setting when creating `rdCJTaM9`.

Mochi `<ai>...</ai>` component contents must stay on a single line. Multi-line `<ai>` contents can break formatting or rendering. Keep line breaks outside the `<ai>` tag only.

Changing a template AI prompt can cause cached AI components to miss and regenerate when cards render. Treat this as credit-spending until verified otherwise. Safer options:

- Create or use a separate v2 template and test it with one card.
- Use the v2 template only for future generated decks.
- Avoid bulk re-rendering or reviewing old cards immediately after prompt changes.
- Keep old template IDs and generated CSVs so cards can be traced back to their source prompt.
