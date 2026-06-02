# AGENTS.md

## Project Overview

Mochiko preserves source assets and scripts for generating language-learning decks in Mochi. It currently contains a Spanish pilot, but copy, structure, and implementation should stay language-general because German will likely be added next.

The goal is not to bulk-generate cards blindly. Generate small previews, inspect them, then import a small pilot into Mochi.

## Current Mochi State

- Parent Spanish deck: `Spanish` (`khnMj1gA`)
- Pilot deck already created: `Frequency 001-020` (`MNmR28ru`)
- Original template: `Language with Audio` (`NzSvxUDF`)
- Recommended new template for future Spanish imports: `Mochiko Language with Audio` (`tq51slCp`)
- Superseded v2 template: `Language with Audio v2 Inline` (`KHhX0rbi`)
- A first attempted v2 template also exists: `Language with Audio v2` (`rdCJTaM9`), but avoid it because the MCP-created `Audio` field did not preserve the original speech source linkage.

Do not create more Mochi cards or decks unless the user explicitly asks.

## Setup Commands

Install dependencies into the ignored local work directory:

```sh
python3 -m pip install --target work/python-packages wordfreq
```

Regenerate the current Spanish preview:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_pilot.py
```

Generate the next Spanish frequency batch:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_batches.py --start-rank 21 --end-rank 40
```

## Code And Data Conventions

- Keep language assets under `languages/<language-code>/`.
- Keep reusable import/generation scripts under `scripts/`.
- Keep Mochi template prompt source under `templates/`.
- Keep generated previews committed when they are useful review artefacts.
- Keep scratch files, installed packages, and ad hoc experiments under `work/`.
- Use clear frequency-batch names such as `frequency_001_020.csv` and Mochi deck names such as `Frequency 001-020`.

## Card Generation Rules

- Each generated card sentence must contain exactly one cloze pair: `{{target}}`.
- Avoid initial-position clozes when possible because Mochi renders hidden terms as line breaks in AI prompts and that can confuse term identification.
- Prefer short, natural beginner sentences over isolated words.
- For function words, use simple contexts that make the target learnable.
- Preview generated rows before importing to Mochi.
- More Spanish frequency cards are a natural next step after one successful test card on `tq51slCp`.
- `languages/es/frequency_021_040.csv` has already been generated and inspected locally. Do not import it until the user asks.

## Template Rules

- Mochi `<ai>...</ai>` contents must be single-line. Do not put literal newlines inside an `<ai>` tag.
- Keep template source aligned with `templates/mochiko_language_with_audio.md`.
- The current working v2 prompt was edited in Mochi and confirmed by the user on one test client card.
- Hidden-term explanations should bold the hidden term once at the start and should not repeat the same term after the colon.

## Mochi Import Rules

Use `create_card` with:

- `content`: empty string
- `template-id`: `tq51slCp` for future Spanish frequency decks unless the user chooses another template
- `fields.name.value`: the cloze sentence
- `manual-tags`: tag names without `#`

Example tags:

```json
["frequency", "generated", "rank-001-020"]
```

`update_card` with `manual-tags` overwrites the full manual tag list, so include every tag that should remain.

Use `scripts/import_mochi_batch.py` for imports. It previews by default. Direct API writes require `--apply` and `MOCHI_API_KEY`.

## AI-Credit Caution

Changing Mochi `<ai>` prompt text can cause cache misses and spend AI credits when cards render. Prefer creating a separate v2 template, testing one card, then using it only for future decks. Avoid bulk re-rendering old cards immediately after prompt changes.

## User Preferences

- Keep explanations practical and concise.
- Do not make a PR unless explicitly asked.
- Use Australian English in PR descriptions, comments, and handoff text where applicable.
- If a tool or source is inaccessible, say so explicitly.
