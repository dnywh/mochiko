---
name: mochiko-flashcards
description: Use when generating, previewing, or importing Mochi language-learning flashcards with the Mochiko repo conventions, including formal CSV deck sources, wild capture batches, cloze cards, template/tag defaults, and multi-language planning for Spanish or future German.
metadata:
  short-description: Generate Mochi flashcards with Mochiko
---

# Mochiko Flashcards

Use this skill when the user asks to create, review, preview, or import language-learning flashcards through Mochiko.

## Start Here

Before writing cards or changing workflow behaviour, read:

- `README.md`
- `AGENTS.md`
- `docs/flashcard-workflow.md`

Use those files as the source of truth. Keep this skill concise and update the repo docs first when rules change.

## Core Rules

- Do not create Mochi cards or decks unless the user explicitly asks.
- Do not make a PR unless the user explicitly asks.
- Use exactly one cloze pair per card: `{{target}}`.
- Prefer short, natural beginner sentences.
- Avoid initial-position clozes when practical.
- For Spanish, use general Latin American Spanish unless the user asks for a regional variant.
- Treat German as planned but not configured until deck IDs, template, language defaults, and source material are documented.

## Choose The Workflow

- Formal decks: frequency lists, numbers, drills, and other reproducible sets. Keep source under `languages/<language-code>/` and use CSV preview/import tooling.
- Wild captures: messy lived phrases. Normalise in chat, review with the user when practical, then write directly to Mochi with MCP/API tools when explicitly requested. Do not create one-off wild CSVs unless asked.

## Mochi Writes

For current Spanish cards, use template `tq51slCp` unless the user chooses another template.

Direct `create_card` payloads should use:

- `content`: empty string
- `template-id`: current language template
- `fields.name.value`: cloze sentence
- `manual-tags`: tag names without `#`

If using repo CSV tooling, preview first with `scripts/import_mochi_batch.py` and use `--apply` only when explicitly asked.
