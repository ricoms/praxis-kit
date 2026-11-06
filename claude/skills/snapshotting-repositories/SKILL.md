---
name: snapshotting-repositories
description: >-
  Dated repo snapshot: PR flow, review, CI, DORA estimates, hygiene. Use to
  measure a repo over a window or compare snapshots.
allowed-tools: Bash, Read, Write
metadata:
  tags:
    - delivery
    - research
---

# Snapshotting repositories

Takes a dated, repeatable reading of one GitHub repository for a time window. `hugin snapshot` collects the data and
computes every number; the agent only interprets them. Read-only against GitHub. With `--board`, it adds the project
board's reading, computed by the same code as `hugin velocity`.

## Inputs

- **Repo** as `OWNER/NAME`, readable by the signed-in `gh` account. Check `gh auth status` names the account that can
  see it: a personal account returns empty lists that look like a quiet week.
- **Window** as two UTC timestamps. Start where the previous snapshot stopped, to the minute, so windows never overlap.
- **Roles file**, JSON mapping each login to a role (`{"login": "Dev A"}`). Keep it outside any tracked repo. Reuse the
  previous snapshot's file so each role means the same person across snapshots.

## Run it

```sh
uv run --no-dev --project <kit> hugin snapshot collect --repo OWNER/NAME \
  --since 2025-03-03T09:00:00Z --until 2025-03-10T09:00:00Z --roles ~/private/roles.json --out <snapshot dir>
uv run --no-dev --project <kit> hugin snapshot report <snapshot dir> --json
```

`<kit>` is the praxis-kit checkout this skill is linked from: the resolved path of this skill's directory, three levels
up. `uv` provides Python 3.13 there. Relative paths such as `--out` stay relative to the current directory.

Add `--board OWNER/NUMBER --capacity DAYS --target "<milestone>"` for the board reading. The field-name flags are
`hugin velocity`'s (`--help`). Only the repository's own issues on the board are read.

Add `--checkout DIR`, a local clone of the repository, to read every commit message on the default branch, the merge
that brought in each revert commit, and the checks (workflows, rules, tests) that cite an ADR. Without it, commit
messages come only from deployment compares.

`collect` writes `window.json`, `nodes.jsonl`, `edges.jsonl` and `metrics.json`, and prints a Markdown reading. Raw
API responses hold logins and titles, so they go to `--raw` (default `~/.cache/repo-snapshots/`) and stay local.
`--reuse-raw` rebuilds from them without fetching. A large repo takes minutes: CI runs are fetched one day at a time.

If stderr lists unmapped logins, add them to the roles file and run again with `--reuse-raw`. Bots are detected by
GitHub's actor type and need no entry.

## Read it

- **Coverage warnings** come first. A capped day, a truncated compare or an unmapped login limits the figures it
  touches; say which, in the write-up.
- **Counts of open things** (issues, PRs, branches, ruleset state) are as of collection time, not `--until`. Collect
  close to `--until`.
- **Review** has two shares: no outside review of any kind, and no outside approval. Self-reviews and bot reviews never
  count. Report both, and split by merge target, since slices merged into a feature branch are reviewed later as a
  whole.
- **DORA figures are estimates** from GitHub deployment records, per environment. They describe production only once
  production deploys exist. A deploy record that says success after a failed check makes all four wrong; spot-check
  the failed and the first successful deploy in the window against their run logs.
- **The board reading is as of the day the board was fetched** (`as_of`). The board keeps no field history, so a
  margin or a ratio can only be read on the day; the snapshot's `metrics.json` is that record. Never rebuild a past reading from today's board.
- **Carry-over** comes from milestone events, which do have history. An item carries over when it leaves a sprint
  while open, for a later sprint, after the sprint began (the previous sprint's due date). The first sprint began one
  sprint length before its due date, the length being the gap between the first two due dates; with only one sprint,
  carry-over is unknown. Moves before that are re-planning; moves to no sprint or to an earlier one are counted apart,
  and moves of closed items are not counted.
  Renamed milestones are matched from the events; any title left unmatched makes the figure a lower bound, and the
  reading says so.
- **Lineage** answers three path questions: which reverts followed a failed deploy, how story branches' slices were
  reviewed and shipped, and which ADRs have a decide issue, citing PRs and a check. Revert chains and decision
  lineage rest on links read from text (`source: text`), which miss what nobody wrote down. A revert counts only the
  failed deploys that carried the reverted change. Without `--checkout`, a revert merged through a merge-commit PR can
  appear as two chains, and the reading warns. A failed deploy with no revert was fixed forward or not at all; read
  its run log before saying which.
- Compare with the previous snapshot only on figures computed the same way. [signals.md](signals.md) lists each
  signal's source, formula and known trap.

## Write it up

Write the snapshot up as prose plus the figures, with roles instead of names and no issue numbers, commit references or
client details. The write-up and `metrics.json` live outside praxis-kit, in a personal kit or the engagement's own
notes: `metrics.json` can hold label, branch or milestone names that identify the client.
