# Mochiko Flashcard Workflow Reference

Bundled reference for installed skills. If a live Mochiko repo is available, prefer `docs/flashcard-workflow.md`.

## Essentials

- Do not create Mochi cards or decks unless the user explicitly asks.
- Use exactly one cloze pair per card: `{{target}}`.
- Prefer short, natural beginner sentences and avoid initial-position clozes when practical.
- Spanish defaults to general Latin American Spanish.
- German is planned but not configured; do not invent German deck/template defaults.

## Current Spanish Defaults

- Parent deck: `Spanish` (`khnMj1gA`)
- Wild deck: `Wild` (`bxo7vr1h`)
- Numbers deck: `Numbers 010-032` (`cGTBD2MJ`)
- Template: `Mochiko Language with Audio` (`tq51slCp`)

## Workflow Split

- Formal decks: frequency lists, numbers, drills, and repeatable sets. Keep source rows under `languages/<language-code>/` when the repo is available, using CSV columns `rank,word,sentence,tags`.
- Wild captures: messy lived phrases. Normalise in chat, preview when practical, and write directly to Mochi only when explicitly asked. Do not create wild CSVs unless requested.

## Mochi Payload Shape

```json
{
  "content": "",
  "deck-id": "bxo7vr1h",
  "template-id": "tq51slCp",
  "fields": {
    "name": {
      "id": "name",
      "value": "El vaso está {{sobre}} la mesa."
    }
  },
  "manual-tags": ["wild", "generated", "spanish"]
}
```

Mochi `<ai>...</ai>` prompt contents should stay on one line. Template prompt changes may spend AI/audio credits when cards render.
