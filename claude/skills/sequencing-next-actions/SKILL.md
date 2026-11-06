---
name: sequencing-next-actions
description: >-
  A sequenced action table from the live board and repo, not memory,
  separating waits on people and stating the ordering claim. Use on "what
  next", "what should I work on", "plan this".
metadata:
  tags:
    - planning
    - project-management
    - github
    - prioritisation
---

# Sequencing Next Actions

One deliverable: a **table the owner can act on or argue with**, ordered by what to do first.

| column | what goes in it |
|---|---|
| **Action** | The task. One line, a verb |
| **What it is** | The concrete change — files, migration, integration. Not a restatement of the title |
| **Cx** | Effort: `XS` minutes · `S` hours · `M` a day · `L` multi-day |
| **Value** | Impact on the product or its user. **Not** tidiness, not how satisfying it is |

This skill answers *"what do I do next, and
why that first"* when the destination is known and the work is enumerable.

## The one non-negotiable: every row traces to evidence

A plausible-sounding task list is worse than none — it launders invention as a backlog, and the
owner cannot tell which rows came from the board and which came from the model. **Every row
points at an issue number, a defect measured this session, or a decision recorded in an ADR or
memory.** A row you cannot trace does not go in the table; if it matters, file it first, then
cite it.

The same applies to the numbers you reason from. Parse structured output as structured data —
a regex over a log that is ordered newest-first will happily return the field above the one you
asked for, and a cost or count read that way is fabrication with a plausible shape.

Gather before ranking:

- **The board** — `gh issue list --state open --limit 50`, with labels. This is the spine of the table.
- **In flight** — `gh pr list --state open`; a PR mid-review is not a task to start.
- **Shipped vs deployed** — `git log <last-tag>..main`, `gh release list`. Unreleased work changes what "done" means.
- **The resume breadcrumb** — the cwd-keyed `project` / `reference` memory: decisions made, what is waiting on whom.
- **What is genuinely blocked** — an approval, a credential, a third party. These are *waits*, not tasks.

## Rules that make the table worth reading

**Complexity and value are independent axes.** If they correlate across every row, one of them
is being guessed. Cheap-and-valuable is the most important cell in the table and the one a vibes
ranking never finds.

**Value orders the table; complexity only informs it.** Cheap work replenishes itself — every
merge creates a "cut a release" row, every deploy a "verify last night's run" row, every prompt
change a "drop the superseded arm" row. Sort by cheapness and positions 1-3 refill faster than
they are consumed, so position 4 is never reached and the expensive item is deferred forever.
**The tell is the same issue number sliding down successive tables.** Read the previous table
before writing a new one; no `XS` above position 4 without saying why out loud.

**One item is one row.** Splitting a large item's cheap first step into its own row above it is
how the prologue gets done and the item never starts. A refit, a spike, a schema decision that
belongs to a feature travels inside that feature's row.

**A recurring operational chore is not a task.** Cutting a release, verifying a scheduled run,
dropping a superseded arm — these regenerate on their own. They earn a row only when something
named is waiting on them, and they never earn the top.

**Spread the value column.** If most rows read High, the column is decoration and the owner
learns nothing. Hygiene with no user-visible consequence is Low even when it is satisfying;
a wrong number on a screen today outranks a refactor that prevents a wrong number later.

**Justify complexity when it is not obvious.** A migration, a new external integration, a change
to a high-blast-radius file, or a first-of-its-kind network path each deserve the two words that
say why. "M (migration + `relevance.py`)" tells the owner something; "M" alone does not.

**State the ordering claim.** Sequence encodes a belief — usually that one item de-risks or
invalidates another. Say it in a sentence under the table: *"4 before 6 is the whole bet: if
step 4 shows reps ask entity-scoped questions, step 6 is work we never needed."* An unstated
ordering cannot be argued with, and being argued with is the point.

**Mark work that may prove unnecessary.** The most valuable output of sequencing is discovering
that a later expensive item is contingent on an earlier cheap one. Flag it in the Value cell
rather than burying it.

**Separate waits into their own table.** "Blocked on Gaby's approval" is not a task; mixing it
in inflates the plan and hides that the critical path runs through a person, not through code.

**Say what you would not do.** A row deliberately deferred, with its reason, is worth more than
its absence — it shows the owner the option was considered and closed.

## Shape

Three tables, in this order:

1. **Sequenced** — what to pick up next, in order, with the ordering claim beneath it.
2. **Blocked on a human** — the wait and who owns it. Two columns is enough.
3. **Backlog, ranked** — everything else, ordered by value, not by issue number.

Keep the sequenced table short — roughly the next five or six moves. A twenty-row sequence is a
backlog wearing a plan's clothing, and nobody believes position 17.

End with a single question: offer to start at row 1. Do not begin work from this skill — it
produces the plan, the owner picks the entry point.

## Anti-patterns

- **Invented rows.** A task that sounds right but traces to nothing. The most damaging failure here, because it is invisible to anyone who does not know the board.
- **Uniform value.** Every row High. Nothing has been prioritised, only listed.
- **Hidden ordering.** A sequence with no stated rationale, which the owner must reverse-engineer or take on trust.
- **Waits as work.** Padding the plan with items nobody can start.
- **Hygiene inflation.** Ranking a satisfying cleanup above a defect a user hits today.
- **The self-replenishing top.** Three cheap rows leading every table while the same expensive issue sits at the bottom of each. The owner cannot start the work that matters because the plan never reaches it.
- **Estimating from memory.** Complexity assigned without opening the file or checking whether the migration/integration exists. Look before you rate.
- **Starting anyway.** Producing the table and then beginning row 1 unasked.
