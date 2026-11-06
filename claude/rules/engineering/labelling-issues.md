# Issue Labelling

Always-on. Applies whenever an issue is filed or triaged. Issue shape, epics, boards and lifecycle: `managing-github-issues`.

`bug` = **the system behaved incorrectly against intent** — wrong output, a crash, a silent failure. Apply it at filing, not in a later sweep.

**NOT `bug`**: missing features, planned work, debt, hardening, investigations, another system's outage, or the remediation task that follows an incident — label the incident, not its cleanup, or one incident is counted twice.

**A pending decision does not reclassify wrong behaviour.** An issue can carry `bug` and `question` at once: the output is wrong today whichever answer eventually wins. This is the most-missed case, and the one that silently empties a defect count.

**Why it is load-bearing**: the label is what answers *"is anything known to be wrong right now?"* for people who don't read the code — clients, auditors, leads. Under-labelling makes a system look defect-free; labelling every annoyance makes the count mean nothing. Both are failures.

## Axes

Every issue gets a **kind** — `bug` | `enhancement` | `question`. An issue with no kind cannot be counted or filtered.

**Track** and **size** are per-project: declare the set in the project's `CLAUDE.md`, and mark any track belonging to a finished phase as historical so nobody reaches for it on new work. Adding a label is like adding a dependency — it needs a question it answers; delete defaults that go unused.

## Adopting this in an existing repo

Audit first, propose corrections, never bulk-relabel unasked: `managing-github-issues` § *Adopting the labelling rule*.
