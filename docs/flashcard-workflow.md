# Mochiko Flashcard Workflow

Mochiko supports two related workflows:

- Formal decks: reproducible sources committed to this repo.
- Wild captures: lived phrases normalised in chat and written directly to Mochi.

Use this document as the working playbook. Keep `README.md` high level and keep `AGENTS.md` focused on operating rules for future agents.

## Universal Card Rules

- Write one target-language sentence per card.
- Use exactly one cloze pair: `{{target}}`.
- Avoid initial-position clozes when practical.
- Prefer short, natural beginner sentences.
- Make the hidden term useful on its own: a word, phrase, number, contraction, or idiom the learner should recognise.
- For function words, choose simple contexts that make the target learnable.
- Preview cards before writing to Mochi.

## Language Defaults

### Spanish (`es`)

- Use general Latin American Spanish unless the user asks for a regional variant.
- Use `tq51slCp` (`Mochiko Language with Audio`) for current Spanish imports unless the user chooses another template.
- Current Spanish parent deck: `Spanish` (`khnMj1gA`).
- Current Spanish wild deck: `Wild` (`bxo7vr1h`).

### German (`de`)

German is planned but not configured yet.

Before importing German cards, decide and document:

- parent deck ID
- template choice
- voice/audio template behaviour
- register defaults, such as formal/informal address
- source material for formal decks
- tag conventions

Keep German files under `languages/de/` once they exist.

## Formal Deck Workflow

Use this for frequency lists, number ranges, verb drills, themed lists, and other repeatable exercises.

1. Put source rows under `languages/<language-code>/`.
2. Use the existing CSV schema unless a future change intentionally broadens it:

   ```csv
   rank,word,sentence,tags
   ```

3. Ensure the `word` value appears exactly once as the clozed target in `sentence`, except for normal capitalisation.
4. Use semicolon-delimited tags in the CSV, for example:

   ```text
   frequency;generated;rank-001-020
   numbers;generated;range-010-032
   ```

5. Preview with `scripts/import_mochi_batch.py`.
6. Import only after review and only when the user explicitly asks for a write.

Preview example:

```sh
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv --deck-id cGTBD2MJ
```

API import example:

```sh
export MOCHI_API_KEY=...
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv \
  --deck-id cGTBD2MJ \
  --template-id tq51slCp \
  --apply
```

## Wild Capture Workflow

Use this for messy lists captured from signs, restaurants, transport, conversations, or daily life.

1. Preserve the user's intent and context.
2. Check the target wild deck before proposing new cards. Compare proposed cloze targets, unclozed sentence text, and obvious concept equivalents against current cards in the deck or wild-tagged set.
3. If a duplicate or near-duplicate exists, skip the new card and tell the user which existing card covers it, for example: `You already have {{sobre}}: El vaso está {{sobre}} la mesa.`
4. Normalise non-duplicate captures into useful beginner-friendly target-language sentences.
5. Keep regional terms when they are likely what the user is hearing, but otherwise prefer the language default.
6. Present an in-chat preview when practical.
7. Write directly to the requested Mochi deck with MCP/API tools only when the user explicitly asks.
8. Do not create repo CSVs for wild batches unless the user asks to preserve source files.

Direct MCP `create_card` payload shape:

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

## Template Notes

`templates/mochiko_language_with_audio.md` is the source for the recommended Spanish template.

Mochi `<ai>...</ai>` contents must stay on one line. Changing prompt text can cause cached AI/audio components to regenerate and may spend credits, so test template changes on one card before broader use.

Hidden-term explanations should bold the hidden term once at the start and avoid repeating it after the colon.

## Repo-Shared Agent Skill

The portable agent skill lives at `skills/mochiko-flashcards/`. See `README.md` for Codex installation instructions.

The skill entrypoint should stay concise and include only the operating rules needed to find the right context. Its bundled `references/portable-workflow.md` should be a compact portable subset of this document, not a full duplicate.

For agents that do not support Codex-style skills, use `skills/mochiko-flashcards/SKILL.md` and `skills/mochiko-flashcards/references/portable-workflow.md` as project instructions.
