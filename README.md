# Mochiko

Mochiko is a playbook and toolbench for generating language-learning flashcards for [Mochi](https://mochi.cards/).

It keeps durable instructions, templates, scripts, and formal source artefacts in this repo. Mochi remains the source of truth for cards after import, especially for messy "from the wild" captures that are reviewed in chat and written directly with the Mochi MCP/API.

Spanish and German are the current languages. Keep reusable copy and tooling language-general unless it is documenting a language-specific workflow.

## Current Mochi state

- Parent Spanish deck: `Spanish` (`khnMj1gA`)
- Wild Spanish deck: `Wild` (`bxo7vr1h`)
- Spanish frequency deck: `Frequency` (`K7f2W8MO`)
- Spanish numbers deck: `Numbers` (`Njhecliy`)
- Recommended Spanish template: `Mochiko Language with Audio` (`tq51slCp`)
- Parent German deck: `German` (`UjfR5r6p`)
- German frequency deck: `Frequency` (`r2i5qXk7`)
- Recommended German template: `Mochiko German with Seraphina HD` (`xo7aEe7Q`)
- Original Spanish template: `Language with Audio` (`NzSvxUDF`)
- Superseded v2 template: `Language with Audio v2 Inline` (`KHhX0rbi`)
- Avoid first attempted v2 template: `Language with Audio v2` (`rdCJTaM9`)

## Workflows

See [docs/flashcard-workflow.md](docs/flashcard-workflow.md) for the canonical workflow.

At a high level, formal/reusable decks live in this repo under `languages/<language-code>/`, while wild captures are usually reviewed in chat and imported directly to Mochi.

## Repo layout

- `languages/es/frequency.csv` - Spanish frequency source in strict rank order.
- `languages/de/frequency.csv` - German frequency source in strict rank order.
- `languages/es/numbers_010_032.csv` - Spanish number source for 10-32.
- `languages/es/numbers_033_050.csv` - Spanish number source for 33-50.
- `scripts/generate_spanish_frequency_batches.py` - Spanish frequency batch generator.
- `scripts/daily_spanish_frequency.py` - daily Spanish frequency automation runner.
- `scripts/daily_german_frequency.py` - daily German frequency automation runner.
- `scripts/import_mochi_batch.py` - reusable CSV-to-Mochi preview/import helper.
- `templates/mochiko_language_with_audio.md` - source for the recommended Mochiko template.
- `templates/mochiko_german_with_audio.md` - source for the German audio template.
- `docs/flashcard-workflow.md` - detailed workflow and guardrails.
- `skills/mochiko-flashcards/` - repo-shared agent skill for portable guidance in Codex and similar AI coding tools.

Spanish and German frequency cards each use one long-lived `Frequency` deck and
one corresponding source CSV.

## Setup

Install dependencies into the ignored local work directory:

```sh
python3 -m pip install --target work/python-packages wordfreq
```

Configure the Mochi API key in a repo-local `.env` file:

```sh
cp .env.example .env
```

Replace the placeholder in `.env` with your key. The `.env` file is ignored by
Git and must not be committed; `.env.example` contains only the safe placeholder.
The daily frequency runners check an exported `MOCHI_API_KEY` first,
then the repo-local `.env`, and finally the Mochi MCP environment in
`~/.codex/config.toml`.

Regenerate the current Spanish pilot preview:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_pilot.py
```

Generate a specific Spanish frequency batch:

```sh
PYTHONPATH=work/python-packages python3 scripts/generate_spanish_frequency_batches.py --start-rank 21 --end-rank 40
```

Show the next scheduled Spanish frequency ranks:

```sh
PYTHONPATH=work/python-packages python3 scripts/daily_spanish_frequency.py
```

The Spanish daily runner preserves `wordfreq.top_n_list("es", N)` order after excluding digits and other non-alphabetic tokens, starts after the existing frequency ranks 1-40, writes to one long-lived frequency deck, and stops at rank 500 unless the cap is intentionally changed. The scheduled task checks for Mochi review activity in the prior 24 hours and currently caps same-day creation at three cards.

The German daily runner follows `wordfreq.top_n_list("de", N)` in the same way, starts at rank 1, uses one long-lived frequency deck, checks for recent study, and applies a separate three-card daily cap:

```sh
PYTHONPATH=work/python-packages python3 scripts/daily_german_frequency.py --require-recent-study-hours 24 --daily-created-cap 3
```

## Installing the agent skill

The repo-shared skill lives at `skills/mochiko-flashcards/`. In Codex, install it by symlinking the repo copy into your skills directory, then restart Codex:

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -sfn "$PWD/skills/mochiko-flashcards" \
  "${CODEX_HOME:-$HOME/.codex}/skills/mochiko-flashcards"
```

Using a symlink keeps the installed skill aligned with repo updates. On another machine, clone this repo, run the same commands from the repo root, then restart Codex.

The skill includes `skills/mochiko-flashcards/references/portable-workflow.md` so the installed copy remains useful even when the full repo docs are not beside it. When an agent is working inside this repo, it should prefer the live repo docs if they differ from the bundled reference.

For other agent tools, use `skills/mochiko-flashcards/SKILL.md` as the portable operating guide. If the tool does not support Codex-style skills directly, add that file and `skills/mochiko-flashcards/references/portable-workflow.md` to the agent's project instructions or context.

## Importing formal CSV batches

Preview a formal CSV batch without writing:

```sh
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv \
  --deck-id Njhecliy \
  --jsonl-output outputs/mochi_create_card_numbers_010_032.jsonl
```

Import with the official Mochi API only after review and an explicit write request:

```sh
export MOCHI_API_KEY=...
python3 scripts/import_mochi_batch.py languages/es/numbers_010_032.csv \
  --deck-id Njhecliy \
  --template-id tq51slCp \
  --apply
```

The importer uses Mochi's `POST /cards` API and Basic auth with the API key as the username. The JSONL output is only a review or handoff artefact; Mochi cannot import it directly.

## Source material

The Spanish frequency source uses `wordfreq` to rank common Spanish terms, with manually authored beginner sentences around those terms.

Useful source material for expanding the project, especially German:

- [Fluent Forever Base Vocabulary List](https://method.fluent-forever.com/base-vocabulary-list/)
- [General Service List](https://en.wikipedia.org/wiki/General_Service_List)
- [`625-words-fluent-forever-output.csv`](https://github.com/kelvinn/the-625-list/blob/master/625-words-fluent-forever-output.csv)

## Template notes

`templates/mochiko_language_with_audio.md` matches the recommended live Mochi template `Mochiko Language with Audio` (`tq51slCp`). See [docs/flashcard-workflow.md](docs/flashcard-workflow.md) for template and AI-credit guardrails.
