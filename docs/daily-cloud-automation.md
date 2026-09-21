# Daily cloud frequency automation

Replaces the local Codex daily progress → populate run with a Cursor Automation
that runs in the cloud against `github.com/dnywh/mochiko` on `main`.

This document is the durable prompt and setup checklist. Creating the automation
in the Cursor product still requires an owner click (there is no create API in
this agent session). Behaviour rules remain in `docs/flashcard-workflow.md`.

## What the run does

1. Ensures Python deps (`wordfreq` under `work/python-packages`).
2. Confirms `MOCHI_API_KEY` is present.
3. Runs (cloud has git network access, so do **not** pass `--skip-push`):

   ```sh
   PYTHONPATH=work/python-packages python3 scripts/daily_frequency.py --apply --publish
   ```

   Local Codex sometimes used `--skip-fetch --skip-push` when git network was
   blocked. Cursor cloud agents should fetch and push themselves.

4. The script gates on Mochi review activity in the prior 24 hours (Melbourne
   time), then may create up to one Spanish word and three German words (three
   cloze cards each), append matching rows to `languages/*/frequency.csv`, and
   commit plus push only those CSV changes to `main`.
5. Skipped days (no recent study, or nothing to publish) make no Mochi writes
   and no git commit.

## Recommended schedule

- Cron (Melbourne): `0 21 * * *` with timezone `Australia/Melbourne`
- Meaning: 21:00 Melbourne every day, after a typical study window so the
  24-hour review gate can succeed.

UTC equivalent varies with DST; prefer setting the timezone in the UI or
`CRON_TZ=Australia/Melbourne 0 21 * * *` if the cron field accepts it.

## Secrets and environment

| Item | Where | Notes |
| --- | --- | --- |
| `MOCHI_API_KEY` | Cloud Agents → Secrets as a **Runtime Secret** | Required for any write. Scope to the mochiko environment. |
| Cloud environment | Personal environment for `github.com/dnywh/mochiko` | Do **not** use “No environment” / skip-install; secrets may not inject. |
| Environment public id (this project) | `e41878a8-b562-11f1-bb68-864e54d14197` | [Environment dashboard](https://cursor.com/dashboard/cloud-agents/environments/e/e41878a8-b562-11f1-bb68-864e54d14197) |
| GitHub access | Cursor GitHub App, read-write on `dnywh/mochiko` | Needed to push frequency CSVs to `main`. |
| Network | Allow `app.mochi.cards` if egress is restricted | Current personal env egress is unrestricted. |

Do not commit `.env` or paste the API key into the automation prompt.

## Create the automation (Danny)

1. Open [cursor.com/automations/new](https://cursor.com/automations/new).
2. Name: `Mochiko daily frequency`.
3. Trigger: Scheduled → cron `0 21 * * *`, timezone `Australia/Melbourne`.
4. Repository: **single repo** `github.com/dnywh/mochiko`, branch `main`
   (scheduled triggers default to no repo; without this, the agent cannot push).
5. Environment: the mochiko cloud environment above (not skip-install).
6. Tools: disable or withhold **Create pull request** (`open_git_pr`). This
   workflow commits directly to `main`.
7. Paste the prompt in the next section.
8. Save and set **Active**.
9. Optional smoke test: Run now, then confirm the agent either skipped cleanly
   or published only frequency CSVs. Do not expect a PR.

After create, note the automation URL/id (UUID in the dashboard URL) and keep it
with the project notes.

Optional IaC later: the community Terraform provider
`cursor_platform_workflow` can manage the same automation if a `CURSOR_TOKEN`
is available. This session had no token, so creation is UI-only.

## Automation prompt (paste verbatim)

```text
You are the daily Mochiko frequency automation for github.com/dnywh/mochiko.

Goal
- Run the governed Spanish + German frequency schedule once.
- Create Mochi cards and git commits only when scripts/daily_frequency.py decides conditions are met.
- Never open a pull request.

Hard rules
- Work only on branch main. If you are not on main, checkout main and pull origin/main before continuing.
- Read docs/flashcard-workflow.md (Scheduled frequency workflow) and docs/daily-cloud-automation.md first.
- Do not create wild cards, other decks, or unrelated repo changes.
- Stage and commit only changed languages/es/frequency.csv and/or languages/de/frequency.csv. Never stage work/, .env, credentials, sentence banks, or unrelated files.
- If cards were created but git push fails, report the failure and do not try to undo Mochi writes.

Steps
1. From the repo root, ensure wordfreq is available:
   mkdir -p work/python-packages
   pip3 install --target work/python-packages wordfreq
2. Confirm MOCHI_API_KEY is set in the environment (print only whether it is set, never the value). If missing, stop and report.
3. Run:
   PYTHONPATH=work/python-packages python3 scripts/daily_frequency.py --apply --publish
4. Treat a clean skip/block from the script (no recent review activity, nothing to publish, banks complete) as success: summarise in one or two lines and exit without git changes.
5. On success with publishes, the script itself commits and pushes main when --publish is set. If the script created cards but did not push, commit only the changed frequency CSV paths with message like "daily frequency cards: YYYY-MM-DD" and push origin main.
6. End with a short summary: skipped or which language ranks were created, and the commit SHA if any.
```

## Verify without creating cards

Offline bank check (no Mochi, no git writes):

```sh
PYTHONPATH=work/python-packages python3 scripts/daily_frequency.py --validate-banks
```

Governed live preview without writes (needs `MOCHI_API_KEY` and clean `main`):

```sh
PYTHONPATH=work/python-packages python3 scripts/daily_frequency.py
```

## Residual risks

- Automation create/list APIs are not available to this agent; only Danny can
  activate the schedule in the UI (or apply Terraform with a personal token).
- Cloud agents may prefer feature branches / PRs; the prompt and disabled PR
  tool must stay strict so publishes land on `main`.
- If `main` gains branch protection that blocks the Cursor identity, publishes
  will create cards but fail to push CSVs (recoverable next run for cards;
  source drift needs a manual CSV commit).
- Each run bills cloud-agent usage.
- Local Codex schedules should be disabled after the cloud automation is active
  to avoid double populate on the same day.
