---
name: settling-agreements
description: >-
  Settle a project's agreements: infer them from the repo, import an
  agreements.md preset, ask only the gaps. Use when adopting the kit in a new
  or brownfield project.
allowed-tools: Read Grep Glob AskUserQuestion Bash(git log *) Bash(git show *) Bash(git tag --sort=*) Bash(gh pr list *) Bash(gh pr view *) Bash(gh release list *) Bash(gh run list *) Bash(gh api repos/*/environments) Bash(gitleaks detect *)
metadata:
  requires-tools: Write Edit Bash WebFetch
  tags:
    - adoption
    - agreements
    - clarification
---

# Settling agreements

`CONSTITUTION.md` is the guideline a developer skims. This skill applies it to one project. It works out what the
project already does, starts from any agreements the developer brings, asks only what it cannot settle on its own,
and writes the result to `docs/agreements.md` for the developer, or the team, to approve.

Use it when a developer adopts the kit, whether the project is new, ongoing or brownfield. Use it again when the
team wants to revisit its agreements.

## What the session settles

- **The declarations.** Tenancy mode (`claude/rules/glossary.md`) and stage (`CONSTITUTION.md` §4), each from facts.
- **The ten decisions** under "Decisions every team settles" in `CONSTITUTION.md` §5. Each one gets the project's own
  answer. None is skipped.
- **The working agreements** in §5. The project adopts each as written, or adjusts or declines it with a reason.
  Three things are locked and are only explained, never offered for adjustment: the agreements that apply the safety
  floor (checks gate the merge, and agents never bypass a check), the definition of a one-way decision, and the duty
  to settle all ten decisions.

The safety floor (§2) is never part of the session. A current practice that breaks it is recorded as a gap, with an
owner and a date.

Read §2, §4 and §5 from the installed `CONSTITUTION.md` at the start. Never restate them from memory.

Keep the draft in a file outside the repository, such as the session's scratch directory, and update it after every
answer. Nothing is written into the project until step 6.

Only the reading is pre-approved. Writing files, running copier or `just`, and opening the PR each prompt for
permission, and that prompt is the developer's agreement to the step.

## 1. Work out the situation

| Situation | Signals |
|---|---|
| new | no commits yet, or only a scaffold |
| ongoing | history, CI and docs exist, and the team wants to keep most of what it does |
| brownfield | an inherited or long-lived codebase whose practice nobody wrote down |

Read the repository before asking: `git log`, the CI workflows, the README and any existing `CLAUDE.md`, ADRs or
runbooks. Ask only when the signals disagree. The situation decides how much evidence step 2 can collect.

Settle tenancy and stage the same way. Stage follows the §4 table: real data, promised availability and the rate of
change. Tenancy has no default. Ask when the code does not show it.

Settle whether the stack is decided. It is decided when an ADR accepts it, or when the code already runs on it:

- **New project.** The developer names the stack, or asks for options, which come from `docs/ai-sdlc/radar.md` and
  `docs/ai-sdlc/decision-points.md`. Either way it becomes a stack ADR for the decider to accept. Until then, the
  stack is undecided.
- **Ongoing or brownfield project.** Read the stack from the repository: lockfiles, CI workflows, Dockerfiles. It is
  decided. Record it in an ADR that describes the existing stack, and fill the template's slots from the commands the
  project already runs.
- **A proposed addition** to an existing stack, such as a new language or datastore, is its own proposed ADR, drafted
  from what the repository already uses. Once accepted, it adds to the slots. It never makes the stack undecided.

`template/README.md` § How CI grows draws the same tree.

## 2. Gather the starting answers

Collect them in layers. A later layer overrides an earlier one, and every row remembers which layer it came from.

1. **The kit's defaults.** The proposed defaults in `docs/ai-sdlc/decision-points.md` and the template's
   `docs/agreements.md`.
2. **A preset**, if the developer names one. A preset is any `agreements.md`, given by path or URL: another
   project's, or one kept in a team kit or a person's kit (`CONSTITUTION.md` §6). Take its choices and its adjusted
   working agreements. Leave its dates and deciders behind, because they belong to the other project.
3. **What the repository shows**, for an ongoing or brownfield project. [evidence.md](evidence.md) lists what to read
   for each decision, and the floor checks to run. Record the evidence with the row, for example "38 of the last 40
   PRs were squash-merged".

## 3. Draft every row

Fill every row you can before asking anything. For each, keep the answer, its layer and its evidence. Mark a row
**weak** when:

- the evidence is thin or mixed, for example 22 squash merges and 18 merge commits;
- two layers disagree, for example the preset says trunk-based and the history shows story branches;
- no layer says anything;
- the current practice breaks the safety floor. That row becomes a gap, not an agreement.

A new project has no evidence, so its rows come from the defaults and the preset.

## 4. Ask only the weak rows

Follow `claude/rules/interaction/clarify-protocol.md`. Ask one question at a time with `AskUserQuestion`. Each
question names the evidence and puts the recommended answer first. Update the draft before asking the next question.
After five questions, stop, summarise what is settled, and ask whether to continue.

For the working agreements, ask one question whose text lists every agreement in §5, each in a few words. Mark the
three locked items and say in one line why they cannot change. Put the list in the question itself, not in a message
before it: the developer may see only the question. Below the list, propose a setup from the evidence: the agreements
to adopt as written, and each one to adjust, with the proposed change and its evidence. The recommended option adopts
that setup. The others adopt every agreement as written, or change the setup. For each agreement the developer
changes, ask first what changes, then, as a separate question, why.

On a team, the developer's answers to weak rows are proposals. The team settles them in step 7.

## 5. Review the whole draft

Show the developer the complete draft once: every decision with its choice and its source, every adjusted working
agreement, every gap, and the tenancy and stage. They correct anything, and nothing is written until they confirm.

## 6. Write it into the project

The template, when the developer wants it, goes first: it renders `.claude/CLAUDE.md` and `docs/agreements.md`, and
the settled answers are written into the rendered files. Writing them first and rendering afterwards loses them,
because copier overwrites both files.

**Offer the template.** Map the settled answers to copier answers and show the mapping:

| Settled | Copier answer |
|---|---|
| the project's name | `project_name`, from the repository name unless the developer gives another |
| tenancy and stage | `tenancy_mode`, `stage` |
| CI on GitHub Actions | `ci_target=github-actions`, which `release_workflow` and `team_delivery` require |
| the stack is decided (step 1) | `stack_decided=true` |
| a deployment workflow through the pipeline, once there is a deploy target or the project leaves `explore` | `release_workflow=true`, which requires `stack_decided` |
| more than one person, or a client to coordinate with | `team_delivery=true` |
| the decider for one-way decisions, on a team | `decision_owners` |
| the response expectation for reviews, on a team | `review_wait_hours` |

In `explore` with the stack undecided, render `stack_decided=false` and `release_workflow=false`. Record the
deployment, rollback and hotfix rows as "settled when there is a deploy target or the project leaves `explore`": §5
asks for them before the first change reaches production, and explore code never reaches production. Past `explore`,
render `stack_decided=true` even before the stack ADR is accepted: §4 asks for lint and tests there, so CI stays red
until the slots are filled, and the stack ADR is the first thing to settle.

Run it only if the developer agrees:

- **A new project:** `copier copy` from the kit's git URL with these answers, as `template/README.md` gives it.
- **An ongoing or brownfield project:** render into a temporary directory, then merge file by file. Never run
  `copier copy --overwrite` on a project with its own README, justfile or workflows, because it replaces them with
  stubs.
- In both cases, run `just install-project` after the copy, never before. `copier copy` refuses to write over the
  `.claude/CLAUDE.md` symlink that the install creates.

**Write the agreements.** Fill `docs/agreements.md`, or create it with the template's structure when the developer
declined the template:

- **The decisions table.** One row per decision: the choice, with `— evidence: ...` or `— from preset ...` where it
  applies, then the status, the date and the decider.
- **`## Adjusted working agreements`.** One row per adjusted or declined agreement: what changed, why, the date and
  who decided. Leave the table empty when nothing was adjusted.
- **`## Gaps against the safety floor`.** One row per practice that breaks the floor: the rule it breaks, the owner
  and the date it will be fixed.

Write the tenancy and stage declarations into the project's `.claude/CLAUDE.md`, in the form the template renders.
If that file is a symlink into the kit, which `just install-project` creates when the template was declined, write
them into the project's root `CLAUDE.md` instead. Never edit a symlinked file: it is the kit's, shared by every
project.

## 7. Make it an agreement

- **One person:** set each status to `agreed`, with today's date and the developer as decider. The agreements hold
  once the file is written.
- **A team:** the team reads the draft first and meets only on the rows someone contests. Nothing is agreed until
  the decider merges. Do not message teammates: the developer tells them, and schedules any meeting.
  1. **Pre-read.** Open a PR with the files, with each status set to `agreed when #<PR> merges`, the named decider,
     and the date left empty, because the merge sets it. The PR body is the agenda: every weak row and every proposed
     adjustment, each with its evidence and the developer's proposal. Open one review thread on each agenda item. A
     row settled by evidence gets no thread, though anyone may comment on it. The PR states the pre-read window:
     three working days, unless the team's own row on changing agreements says otherwise.
  2. **Meeting on contested rows.** When the window closes, an agenda item nobody objected to is settled, because
     silence within the window is consent (§5). The items with an objection go to one timeboxed meeting, of 30 to 45
     minutes. The named decider decides each one after hearing the team. During the meeting, write each outcome into
     the files and resolve its thread with the outcome and the reason. If nothing is contested, there is no meeting.
  3. **Minutes and merge.** Add the minutes to the PR: who attended, and each contested item's outcome and reason.
     A teammate who missed the meeting has one working day after the minutes to object on the PR. Then the decider
     merges.

## 8. Offer to save a preset

Offer to save the settled choices and adjustments as a preset the next project can import, in the developer's or
the team's kit. A preset is the same `agreements.md` with its dates and deciders cleared.

## Done when

- The developer confirmed the whole draft in step 5.
- The project's `CLAUDE.md` declares tenancy and stage.
- Every one of the ten decisions has a choice and a status, and none is skipped.
- Every adjusted working agreement has a reason, a date and a decider, and none of the three locked items is adjusted.
- Every breach of the safety floor is a gap with an owner and a date.
- For a team, the PR is open with its agenda, a thread on each agenda item, and its window stated.

## Anti-patterns

- **Asking what the repository already answers.** Read first. A question about branching in a repository with 400
  merged PRs wastes the developer's time.
- **Recording intent as practice.** In a brownfield project, the evidence shows what the team does. When the
  developer says the team does something else, ask which one becomes the agreement, and keep the evidence in the row
  either way.
- **Carrying a preset's deciders over.** The new project's people decide its agreements.
- **Turning a floor breach into an agreement.** "We deploy from laptops" is a gap with an owner, never a choice.
- **Treating a team's agreement as done when the file is written.** A team agrees through the PR, not through the
  session.
