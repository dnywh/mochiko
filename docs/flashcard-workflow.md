# Mochiko flashcard workflow

Mochiko supports two related workflows:

- Formal decks: reproducible sources committed to this repo.
- Wild captures: lived phrases normalised in chat and written directly to Mochi.

Use this document as the working playbook. Keep `README.md` high level and keep `AGENTS.md` focused on operating rules for future agents.

## Universal card rules

- Write one target-language sentence per card.
- Use exactly one cloze pair: `{{target}}`.
- Avoid initial-position clozes when practical.
- Prefer short, natural beginner sentences.
- Make the hidden term useful on its own: a word, phrase, number, contraction, or idiom the learner should recognise.
- For function words, choose simple contexts that make the target learnable.
- Preview cards before writing to Mochi.

## Language defaults

### Spanish (`es`)

- Use general Latin American Spanish unless the user asks for a regional variant.
- Use `tq51slCp` (`Mochiko Language with Audio`) for current Spanish imports unless the user chooses another template.
- Current Spanish parent deck: `Spanish` (`khnMj1gA`).
- Current Spanish frequency deck: `Frequency` (`K7f2W8MO`).
- Current Spanish numbers deck: `Numbers` (`Njhecliy`).
- Current Spanish wild deck: `Wild` (`bxo7vr1h`).

### German (`de`)

- Use standard German, with informal `du` by default unless the sentence naturally requires another register.
- Use `xo7aEe7Q` (`Mochiko German with Seraphina HD`) for current German imports.
- The German audio template source selects `de-DE-Seraphina:DragonHDLatestNeural` with Mochi's `voice` attribute. Replacing a live template can regenerate audio, so test a sample before changing existing cards.
- Current German parent deck: `German` (`UjfR5r6p`).
- Current German frequency deck: `Frequency` (`r2i5qXk7`).
- Use `wordfreq.top_n_list("de", N)` as the frequency source after excluding digits and other non-alphabetic tokens.
- Use `frequency;generated;german` tags for scheduled frequency cards.
- Keep German formal sources under `languages/de/`.

## Formal deck workflow

Use this for frequency lists, number ranges, verb drills, themed lists, and other repeatable exercises.

1. Put source rows under `languages/<language-code>/`.
2. Scheduled frequency sources include a `variant` column so new words can
   have three independently reviewed cards:

   ```csv
   rank,variant,word,sentence,tags
   ```

3. Ensure the `word` value appears exactly once as the clozed target in `sentence`, except for normal capitalisation.
4. Use semicolon-delimited tags in the CSV, for example:

   ```text
   frequency;generated;rank-001-020
   numbers;generated;range-010-032
   ```

5. Preview with `scripts/import_mochi_batch.py`.
6. Import only after review and only when the user explicitly asks for a write.

### Scheduled frequency workflow

The combined daily automation is an explicit exception to the usual manual
preview-before-import rule. It uses filtered `wordfreq.top_n_list()` results as
the source of truth and reads prepared sentences from each language's committed
`frequency_sentence_bank.csv`.

The scheduled run must:

- process Spanish before German in strict frequency-rank order
- continue only when Mochi shows review activity within the prior 24 hours
- treat newly synced review records as recent when Mochi's day-level dates are unreliable
- fetch Mochi cards once and reuse that snapshot for gates and duplicate checks
- add one Spanish word and up to three German words per day
- create exactly three separate sentence cards for each new word
- vary each trio across useful grammatical, semantic, or conversational contexts
- validate complete variants 1, 2, and 3 with exactly one cloze pair each
- tag every card with its exact rank and variant for safe interrupted-run recovery
- keep Spanish in `K7f2W8MO` and German in `r2i5qXk7`
- append successful rows to the corresponding `frequency.csv`
- require `MOCHI_API_KEY` before any write and stop at rank 500

Existing one-sentence frequency cards are not backfilled. New ranks use three
separate cards so each context becomes an independent retrieval event. A
partial write is recoverable because the next run skips matching sentences and
completes the tagged trio.

Use `scripts/daily_frequency.py`. `--validate-banks` checks prepared rows without
Git or Mochi access. A run without `--apply` performs a governed live preview.
`--apply --publish` performs the single-snapshot write and guarded publication.

### Scheduled source version control

After a governed run successfully creates cards and updates either frequency
source, the automation commits only the changed Spanish and German frequency
CSVs directly to `main`, then pushes `main` to `origin`. Sentence banks are
replenished separately and are not changed by the scheduled run. It does not create a PR.
Skipped runs create no commit. Scratch files under `work/`, credentials, and
unrelated worktree changes must never be staged. A commit or push failure is
reported without undoing cards that were already created in Mochi.

Preview example:

```sh
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv --deck-id Njhecliy
```

API import example:

```sh
export MOCHI_API_KEY=...
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv \
  --deck-id Njhecliy \
  --template-id tq51slCp \
  --apply
```

## Wild capture workflow

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

## Template notes

`templates/mochiko_language_with_audio.md` is the source for the recommended Spanish template.

Mochi `<ai>...</ai>` contents must stay on one line. Changing prompt text can cause cached AI/audio components to regenerate and may spend credits, so test template changes on one card before broader use.

Hidden-term explanations should bold the hidden term once at the start and avoid repeating it after the colon.

## Repo-shared agent skill

The portable agent skill lives at `skills/mochiko-flashcards/`. See `README.md` for Codex installation instructions.

The skill entrypoint should stay concise and include only the operating rules needed to find the right context. Its bundled `references/portable-workflow.md` should be a compact portable subset of this document, not a full duplicate.

For agents that do not support Codex-style skills, use `skills/mochiko-flashcards/SKILL.md` and `skills/mochiko-flashcards/references/portable-workflow.md` as project instructions.
