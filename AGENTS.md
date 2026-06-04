# AGENTS.md

## Project Role

Mochiko is a playbook and toolbench for generating language-learning flashcards for Mochi. Keep implementation and documentation focused on that purpose.

## Source Of Truth

- Read `docs/flashcard-workflow.md` before changing card-generation behaviour, deck workflow, tags, templates, or import rules.
- Use `README.md` for project state, setup, and installation details.
- Keep this file as repo-local operating guidance; do not duplicate the full workflow here.

## Operating Rules

- Do not create Mochi cards or decks unless the user explicitly asks.
- Do not make a PR unless the user explicitly asks.
- Preserve the formal-vs-wild split: formal reusable decks use committed sources under `languages/`; wild captures are normally reviewed in chat and imported directly to Mochi.
- Keep scratch files, installed packages, and ad hoc experiments under `work/`.
- Use Australian English in PR descriptions, comments, and handoff text where applicable.
- If a tool or source is inaccessible, say so explicitly.
