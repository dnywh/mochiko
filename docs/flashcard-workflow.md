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

### Scheduled Spanish frequency workflow

The daily Spanish frequency automation is an explicit exception to the usual manual preview-before-import rule. It uses `wordfreq.top_n_list("es", N)` as the source of truth for rank order after excluding digits and other non-alphabetic tokens, continues after the existing frequency ranks 1-40, and currently writes up to three new cards per run until the approved cap rank is reached.

The scheduled run must:

- use general Latin American Spanish
- generate ranks in strict order
- exclude digits and other non-alphabetic `wordfreq` tokens before assigning ranks
- only continue if Mochi shows review activity within the prior 24 hours
- treat newly synced review records since the previous activity inspection as
  recent activity when Mochi's day-level dates are wrong after timezone travel
- count cards already created today across Mochi and only add the remaining portion of the three-card daily cap
- keep all Spanish frequency cards in the long-lived `Frequency` deck
- append successful rows to `languages/es/frequency.csv`
- validate one cloze pair per sentence before writing
- use deck `K7f2W8MO` and template `tq51slCp`
- require `MOCHI_API_KEY` before any write
- stop when rank 500 is complete unless the cap is intentionally raised

Use `scripts/daily_spanish_frequency.py` for this workflow. Running it without sentence input prints the next approved ranks after applying the recent-study and same-day creation gates. Running it with `--sentences-json` validates the proposed slice, which may now be smaller than three rows. Running it with `--apply` rechecks the gates, writes to the existing frequency deck, and appends the source rows after a successful write.

### Scheduled German frequency workflow

The German automation uses the same review-activity and validation gates as Spanish, but it keeps one long-lived `Frequency` deck. It adds up to three cards a day through `scripts/daily_german_frequency.py`, applies its same-day cap only to that German deck, and stops at rank 500 unless the cap is intentionally raised.

The scheduled run must:

- use standard German and informal `du` by default
- generate strict `wordfreq.top_n_list("de", N)` rank order after filtering non-alphabetic tokens
- continue only when Mochi shows review activity within the prior 24 hours
- add no more than three German frequency cards on a local calendar day
- validate exactly one cloze pair per sentence
- use deck `r2i5qXk7` and template `xo7aEe7Q`
- require `MOCHI_API_KEY` before any write
- append successful rows to `languages/de/frequency.csv`
- stop when rank 500 is complete unless the cap is intentionally raised

### Scheduled source version control

After a governed run successfully creates cards and updates either frequency
source, the automation commits only the changed Spanish and German frequency
CSVs directly to `main`, then pushes `main` to `origin`. It does not create a PR.
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
