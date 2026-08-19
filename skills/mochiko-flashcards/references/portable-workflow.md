# Mochiko Flashcard Workflow Reference

Bundled reference for installed skills. If a live Mochiko repo is available, prefer `docs/flashcard-workflow.md`.

## Essentials

- Do not create Mochi cards or decks unless the user explicitly asks.
- Use exactly one cloze pair per card: `{{target}}`.
- Prefer short, natural beginner sentences and avoid initial-position clozes when practical.
- Spanish defaults to general Latin American Spanish.
- German defaults to standard German and informal `du` where appropriate.

## Current Spanish Defaults

- Parent deck: `Spanish` (`khnMj1gA`)
- Frequency deck: `Frequency` (`K7f2W8MO`)
- Wild deck: `Wild` (`bxo7vr1h`)
- Numbers deck: `Numbers` (`Njhecliy`)
- Template: `Mochiko Language with Audio` (`tq51slCp`)

## Current German Defaults

- Parent deck: `German` (`UjfR5r6p`)
- Frequency deck: `Frequency` (`r2i5qXk7`)
- Template: `Mochiko German with Seraphina HD` (`xo7aEe7Q`)
- Frequency source: filtered `wordfreq.top_n_list("de", N)` rank order
- Scheduled tags: `frequency;generated;german`

## Workflow Split

- Formal decks: frequency lists, numbers, drills, and repeatable sets. Keep source rows under `languages/<language-code>/` when the repo is available, using CSV columns `rank,word,sentence,tags`.
- Scheduled Spanish and German frequency sources use one strict-rank-order `frequency.csv` per language. Successful governed runs may commit and push only those changed source CSVs when the automation explicitly authorises it.
- Wild captures: messy lived phrases. Check the target wild deck or wild-tagged set for duplicate cloze targets, sentence text, and obvious concept equivalents before proposing new cards. Tell the user which existing card covers a duplicate, then skip it. Normalise non-duplicates in chat, preview when practical, and write directly to Mochi only when explicitly asked. Do not create wild CSVs unless requested.

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
