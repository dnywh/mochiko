# Mochiko

Small scripts and source artefacts for generating language-learning cards for Mochi.

Current status:

- Spanish pilot deck created in Mochi: `Frequency 001-020`
- Mochi deck ID: `MNmR28ru`
- Recommended Mochiko template ID: `tq51slCp` (`Mochiko Language with Audio`)
- Parent deck: `Spanish` (`khnMj1gA`)

Next steps:

- [x] Test one new Spanish card with `tq51slCp` and confirm translation, hidden-term explanation, and both speech blocks work.
- [x] Generate and inspect the next Spanish frequency batch before importing more cards.
- [x] Add a reusable Mochi importer script so future Spanish and German batches do not require one-off MCP calls.
- [ ] Create/import the next Spanish batch in Mochi after final review.
- [ ] Decide whether to update the original 20 Spanish pilot cards from `NzSvxUDF` to `tq51slCp`; this may spend AI/audio credits.

## Approach

Cards use a language-learning template with translation, a focused hidden-term explanation, and speech audio. Each generated row contains one target-language sentence with exactly one clozed term, for example:

```text
Soy {{de}} Perú.
```

The first pilot used `wordfreq` for Spanish frequency ordering, then hand-authored beginner-friendly sentence clozes for the top 20 words. The repo is intentionally structured so German and other languages can be added later under `languages/<code>/`.

## Files

- `languages/es/frequency_001_020.csv` - generated pilot preview.
- `languages/es/frequency_021_040.csv` - generated next-batch preview.
- `scripts/generate_spanish_frequency_batches.py` - reproducible Spanish batch generator.
- `scripts/import_mochi_batch.py` - reusable dry-run/import helper for Mochi CSV batches.
- `templates/mochiko_language_with_audio.md` - recommended Mochiko template prompt.

## Setup

Install Python dependencies into a local target:

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

## Mochi Import Notes

Use `create_card` with:

- `deck-id`: target frequency deck ID
- `template-id`: the current language template ID; use `tq51slCp` for new Spanish frequency decks unless testing says otherwise
- `content`: empty string
- `fields.name.value`: the cloze sentence
- `manual-tags`: tags without `#`, for example `["frequency", "generated", "rank-001-020"]`

Do not create more cards until the generated preview has been inspected.

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

The importer uses Mochi's `POST /cards` API and Basic auth with the API key as the username.

## Template And AI-Credit Notes

`templates/mochiko_language_with_audio.md` matches the recommended live Mochi template `Mochiko Language with Audio` (`tq51slCp`). It uses inline speech blocks for both slow and fast audio because the exposed Mochi `create_template` tool did not preserve the original template's speech-field `source` setting when creating `rdCJTaM9`.

Mochi `<ai>...</ai>` component contents must stay on a single line. Multi-line `<ai>` contents can break formatting/rendering. Keep line breaks outside the `<ai>` tag only.

Hidden-term explanations should bold the hidden term once at the start and avoid repeating it after the colon. Prefer `**por**: by/through/for; used for movement through a place, cause, duration, or means.` over `por: por; by/through/for; ...`.

Changing a template AI prompt can cause cached AI components to miss and regenerate when cards render. Treat this as credit-spending until verified otherwise. Safer options:

- Create or use a separate v2 template and test it with one card.
- Use the v2 template only for future generated decks.
- Avoid bulk re-rendering/reviewing old cards immediately after a prompt change.
- Keep old template IDs and generated CSVs so cards can be traced back to their source prompt.

Tags are supplied without the `#` prefix. For API imports, pass `manual-tags`, for example:

```json
["frequency", "generated", "rank-001-020"]
```

For updates, Mochi's `update_card` `manual-tags` field overwrites the current manual tag list, so include every tag you want to keep.
