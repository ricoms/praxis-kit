---
name: running-a-work-session
description: >-
  The project session loop: sweep what changed, sequence the next moves, do
  one row end to end, close it out, repeat. Use on "start the day", "do row
  N", "merged", or a session of back-to-back tasks.
metadata:
  tags:
    - session-management
    - planning
    - workflow
---

# Running a Work Session

A session is a loop, not a task list. Each pass ends with the board, the repo and the owner's
picture of both in agreement, so the next pass starts from facts instead of memory.

```
resume ─▶ sweep ─▶ sequence ─▶ owner picks a row ─▶ do the row ─▶ owner merges ─▶ close out ─┐
                  ▲                                                                                │
                  └────────────────────── re-sequence when state changed ◀─────────────────────────┘
                                                        hand off at the end
```

## The steps

**0 · Resume.** Start from what the last session left: the branch and working tree, the issues it left open, and
the note it recorded for the next session (the project's notes, an issue comment, or an agent memory). At the end,
**hand off** the same way: unfinished work becomes issues, the working tree is clean or its state is written down,
and the note says where things stand.

**1 · Sweep** with the project's sweep skill, if it has one, or by hand: every
channel, threads included, filtered on `updatedAt`. Start from the floor the last sweep saved, and
save the new one in the hand-off note before reporting. Report, then stop.

**2 · Sequence** with `sequencing-next-actions`, scoped to the owner's assigned issues unless they
say otherwise. Read the previous table first: a row that keeps sliding down is the thing to say.

**3 · The owner picks a row.** Do not start row 1 because it is row 1.

**4 · Do the row, the whole row.** "Do row N" includes the branch, the checks and the PR. It stops
at the merge, which is the owner's.

- Fetch first and branch from a fresh `origin/main` in a worktree, one per row. The owner merges
  between turns, so the local checkout is never the base.
- A review row follows `reviewing-delivered-work`: read the standard first, reproduce the author's
  claims, ask only what the author can fix. No asks → approve in one line.
- Anything addressed to someone else — a review, a comment, a chat message — is drafted and
  shown. It is posted on the owner's word, as written.
- A check that the row adds is proved by making it fail on the real tree. Do that on a scratch
  copy or a commit, never by reverting the working tree: `git checkout -- <file>` discards the
  row's own uncommitted edits along with the test.

**5 · Close out, as soon as the owner says "merged".**

- Remove the worktree and delete the local branch.
- The issue closed: board Status Done and Remaining Work 0, then ask for the Actual. Never guess it.
- Work the row uncovered goes into an existing issue or a new one, the owner choosing which. A
  follow-up left only in chat is lost.

**6 · Re-sequence only when state changed.** A merge, a sweep finding or a new decision changes
the table; finishing a row does not by itself. Otherwise take the next row.

## Where the owner decides

Which row · whether a draft is sent · the merge · the Actual · any decision the owner holds as a
named decider. Everything else in the loop is the agent's to do without asking.

## Anti-patterns

- **Starting work from the sweep.** The sweep reports; the table decides.
- **Stopping at the diff.** A row without its PR is not done, and neither is a merge without its
  close-out.
- **Asking for permission between steps the owner already chose.** "Do row 3" covers the branch,
  the commit and the PR.
- **Posting the long version.** A review, comment or message carries the action, not the analysis.
  The analysis goes to the owner in the session.
- **Chat-only follow-ups.** If it matters after the session ends, it belongs on an issue.

## See also

`sequencing-next-actions` · `reviewing-delivered-work` · `managing-github-issues` ·
`docs/ai-driven-lifecycle.md`
