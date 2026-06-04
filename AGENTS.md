# AGENTS.md

## Project Overview

Mochiko is a playbook and toolbench for generating language-learning flashcards for Mochi. It preserves reusable instructions, source artefacts, templates, and scripts while Mochi remains the source of truth for imported cards.

The repo currently contains Spanish pilot material, but structure, copy, and tooling should stay language-general because German is planned next.

## Current Mochi State

- Parent Spanish deck: `Spanish` (`khnMj1gA`)
- Wild Spanish deck: `Wild` (`bxo7vr1h`)
- Spanish frequency deck: `Frequency 001-020` (`MNmR28ru`)
- Spanish frequency deck: `Frequency 021-040` (`juLri2Ke`)
- Spanish numbers deck: `Numbers 010-032` (`cGTBD2MJ`)
- Original Spanish template: `Language with Audio` (`NzSvxUDF`)
- Recommended Spanish template: `Mochiko Language with Audio` (`tq51slCp`)
- Superseded v2 template: `Language with Audio v2 Inline` (`KHhX0rbi`)
- Avoid first attempted v2 template: `Language with Audio v2` (`rdCJTaM9`)

Do not create Mochi cards or decks unless the user explicitly asks.

## Workflow Policy

- Read `README.md` and `docs/flashcard-workflow.md` before changing card-generation behaviour.
- Formal decks belong in committed source files under `languages/<language-code>/`.
- Frequency lists, number lists, and structured drills are formal decks.
- Wild captures are normally reviewed in chat and written directly to Mochi with MCP/API tools; do not create one-off wild CSVs unless the user asks.
- Keep generated previews committed only when they are useful review artefacts for formal/reproducible decks.
- Keep scratch files, installed packages, and ad hoc experiments under `work/`.

## Language Defaults

- Spanish (`es`): aim for general Latin American Spanish unless the user asks for a regional variant.
- German (`de`): planned but not configured; choose deck IDs, template, register, and source material before generating or importing German cards.
- Keep reusable docs language-general. Put language-specific rules in clearly labelled sections.

## Card Generation Rules

- Each generated card sentence must contain exactly one cloze pair: `{{target}}`.
- Avoid initial-position clozes when practical because Mochi renders hidden terms as line breaks in AI prompts.
- Prefer short, natural beginner sentences over isolated words.
- For function words, use simple contexts that make the target learnable.
- For formal CSV rows, `word` must match the exact clozed text, except for normal capitalisation.
- Preview generated rows before importing to Mochi.

## Template Rules

- Use `tq51slCp` for current Spanish imports unless the user chooses another template.
- Mochi `<ai>...</ai>` contents must be single-line. Do not put literal newlines inside an `<ai>` tag.
- Keep template source aligned with `templates/mochiko_language_with_audio.md`.
- Hidden-term explanations should bold the hidden term once at the start and should not repeat the same term after the colon.

## Mochi Import Rules

Use `create_card` with:

- `content`: empty string
- `template-id`: `tq51slCp` for current Spanish imports unless the user chooses another template
- `fields.name.value`: the cloze sentence
- `manual-tags`: tag names without `#`

Example tags:

```json
["frequency", "generated", "rank-001-020"]
```

For updates, Mochi's `update_card` `manual-tags` field overwrites the full manual tag list, so include every tag that should remain.

Use `scripts/import_mochi_batch.py` for formal CSV imports. It previews by default. Direct API writes require `--apply` and `MOCHI_API_KEY`.

## Setup Commands

Install dependencies into the ignored local work directory:

```sh
python3 -m pip install --target work/python-packages wordfreq
```

Regenerate the current Spanish preview:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_pilot.py
```

Regenerate the imported Spanish 21-40 frequency batch:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_batches.py --start-rank 21 --end-rank 40
```

Dry-run a formal CSV batch:

```sh
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv --deck-id cGTBD2MJ
```

## User Preferences

- Keep explanations practical and concise.
- Do not make a PR unless explicitly asked.
- Use Australian English in PR descriptions, comments, and handoff text where applicable.
- If a tool or source is inaccessible, say so explicitly.
