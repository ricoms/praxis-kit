# Constitution

**Status:** draft, drawn from one engagement. A team adopts it for its own project by settling its agreements (see
the [README](README.md#start-here)). Changes to this file follow section 7: a pull request that stays open for an
objection window before it merges.

This is the agreement a team signs up to when it builds software with this kit. The team means the people on it
and the agents that work for them. It is written for people first; agents follow it because the person they act
for does.

It holds for every kind of project: new or inherited, a spike or a production service, a young MVP or a ten-year-old
system. It names no language, framework or cloud. Stack choices are defaults, listed with their alternatives in
[decision points](docs/ai-sdlc/decision-points.md) and the [radar](docs/ai-sdlc/radar.md), and any project may
replace them.

## 1. What we are after

We want **velocity, not speed**. Velocity is finished work that stays finished, week after week. Speed is output
that borrows from next week.

We read velocity from five signals, taken from the board, git and the deployment record:

- **Change lead time.** How long a change takes from start to running in production, and how much of that time it
  sat waiting on a decision, an answer or a review.
- **Change fail rate.** How often a deployed change breaks something and has to be fixed, rolled back or reverted.
- **Rework rate.** How often finished work is reopened, or a deployment is needed only to fix an earlier one.
- **Recovery time.** How long it takes to put right a deployment that failed.
- **Change effort.** Whether the next comparable change is as easy as the last one. Rising complexity is the
  warning sign.

How often a team deploys is reported next to these, but it is not a goal: on its own it measures speed. The signals
compare a team with its own past, never with another team, and none of them is a target. A week that ships more
while any of them gets worse was fast, not good.

Today the `reading-delivery-velocity` skill, in the `team-delivery` profile, measures waiting and actual effort from
the board. The other signals have no measure in the kit yet.

We want the work to be **calm**. Calm means no heroics: nobody rescues a deadline at night, and nobody is
interrupted for something that can wait for its channel. Only an incident or a breach of the safety floor
(section 2) justifies an interruption. Everything else is asked once, in the right place, with a deadline.

## 2. The safety floor

These five rules hold at every stage, in every codebase, with no ratchet. Rule 5 names the floor's only two
exceptions. Each rule protects people, data or money, and none of them is a matter of taste.

1. **Secrets are never committed.** Not to a branch, not to history, not in a test fixture. A secret that leaks is
   revoked first and investigated after.
2. **Every dependency is locked and bounded.** A committed lockfile pins every version, manifests have upper
   bounds, and no version changes except in a commit that names it.
3. **Nothing merges while checks are red.** A red check is fixed or explained in the same day. Nobody weakens a
   check to make it pass.
4. **Every access to data is scoped by the project's declared tenancy mode.** A project declares `multi-tenant`,
   `single-tenant` or `single-user` before any code assumes one ([glossary](claude/rules/glossary.md)).
5. **Nothing reaches production outside the pipeline.** No workstation applies changes to a shared environment,
   not even for a quick fix. There are two exceptions, and every other change goes through the pipeline.
   - **The pipeline's bootstrap.** It creates the pipeline's own identity, permissions and state store, which the
     pipeline cannot create for itself. A person named in a decision record runs it by hand, once per environment,
     after checking which identity the commands will run as. The run is recorded in that decision record, and it
     counts as done once the pipeline has deployed as the identity it created.
   - **Rotating or revoking a secret by hand.** This is key management, not a deployment. A rotation that the secret
     store or platform performs on its own, set up through the pipeline, is preferred and needs no exception. Where
     a secret cannot rotate on its own, a named secret custodian rotates it by hand. The custodian is elevated for
     the rotation only, with multi-factor authentication, the elevation expires on its own, and every privileged
     action is logged. A scheduled rotation runs only after its issue, stating the reason, the security impact and
     the way back, is approved by the named decider. The decider is someone other than the custodian
     wherever the project has a second eligible person. A compromised secret is revoked at once, its issue is opened
     within a day, and the decider approves it afterwards. Agents draft these steps; they never run them.

One practice sits directly under the floor and is active at every stage, because it has a single sanctioned
exception:

- **Upgrades are classified by reversibility and trust.** A release enters only after a cooldown, except to fix a
  known vulnerability. Two-way, low-trust-risk upgrades may be grouped. An upgrade goes alone, with its changelog
  read and a named owner, when it is one-way (section 5) or when it adds a dependency, changes publisher, or runs
  where secrets are present. A malicious release that ran with secrets is a one-way door: reverting the lockfile
  does not undo what it sent out.

## 3. Gates and ratchets

Every practice in this constitution applies in one of two ways, decided by whether the code already exists.

- **New code meets the practice as a gate.** A change that falls short does not merge.
- **Existing code meets it as a ratchet.** The project records today's shortfall once, as a baseline. The baseline
  may only shrink: a fixed exemption must be removed, and no new one may be added to pass a check.

This rule is what lets an inherited or legacy codebase adopt the constitution on its first day. Nobody has to
rewrite the past before shipping, and nobody may add to it. A complexity limit shows the pattern. On the day it is
switched on, every function already over the limit is recorded as an exemption. From then on the build fails on a
new function over the limit, and on an exemption that no longer applies.

Nobody raises a threshold to make a check pass. Loosening a ratchet is an amendment to this constitution
(section 7), not a code change.

## 4. Stages

Each project declares one stage in its `CLAUDE.md`, next to its tenancy mode. The stage switches practices on or
off; the gate-and-ratchet rule decides how strictly an active practice applies.

A stage is defined by facts anyone can check, not by how the team feels about the project:

| Stage | True of the project | It leaves the stage when |
|---|---|---|
| `explore` | no real users and no real data | the first real user or real record arrives, or the code is thrown away |
| `build` | real users or real data, but nobody has been promised availability | availability is promised, by a contract, a service level or a launch |
| `run` | availability is promised, and the code changes actively | change is mostly fixes and upgrades |
| `sustain` | availability is promised, and change is mostly fixes and upgrades | it is retired or rebuilt |

Real data is the line that switches protection on; a promise of availability is the line that switches operations
on. An inherited system under heavy modernisation is therefore `run`, not `sustain`: the ratchet handles its past,
and its rate of change decides its stage.

A stage belongs to a repository. A spike inside a `run` repository lives on its own branch or in its own repository;
it does not lower the stage of the code around it. Changing stage is a decision with an owner. Moving out of
`explore` means one of two things: throw the code away, or keep it and record its baseline so the ratchet starts
from there. Explore code never reaches production on its own.

Which practices each stage switches on. "on" means the practice is active and the gate-and-ratchet rule applies;
"—" means it is off; any other value means it is active only in the form stated.

| Practice | explore | build | run | sustain |
|---|---|---|---|---|
| Upgrades classified by reversibility and trust, after a cooldown (section 2) | on | on | on | on |
| Tests at the right tier: scenarios for cross-module flows, component tests for modules, structural checks | one smoke check | on | on | on |
| Strictest typing and lint the language offers, including the complexity limit | — | on | on | on |
| Modules split by user-facing purpose, with flows between them kept explicit | — | on | on | new code |
| A specification before implementing a non-trivial feature | — | on | on | beyond fixes |
| A decision record for every one-way decision (section 5) | — | on | on | on |
| Threat model for features that touch authentication, personal data, money, a tenancy boundary, an LLM tool surface or an external integration | — | on | on | on |
| Security scan of code, secrets and infrastructure | — | per phase | weekly | weekly |
| Dependency audit for known vulnerabilities | — | weekly | weekly | weekly |
| Traces, metrics and structured logs | — | logs | on | on |
| Service levels, with alerts routed to the team | — | — | on | on |
| Smoke checks after every deploy, with automatic rollback | — | on | on | on |
| Backups, with a restore rehearsed before availability is promised, then yearly and after any storage change | — | on | on | on |
| Access granted on joining and removed on leaving, checked whenever someone leaves | — | on | on | on |
| Secrets rotated on schedule, each rotation logged | — | on | on | on |
| The board as the record of work, with actual effort and waiting time on close | — | on | on | on |

The safety floor (section 2) is not in this table because no stage can switch it off.

## 5. Agreements between us

These are the working agreements: how we treat each other's time, attention and work. Most have a check or a
template behind them; the ones that do not are kept because we agreed to keep them.

A project adopts the working agreements as written, or adjusts or declines one for itself. It records each
adjustment where it settles the decisions listed under "Decisions every team settles", with why, the date and who
decided.

Three things cannot be adjusted, because other parts of this constitution rely on them:

- the agreements that apply the safety floor (section 2): checks gate the merge, and agents never bypass a check;
- the definition of a one-way decision, which sections 2, 4 and 7 use;
- the duty to settle every decision under "Decisions every team settles". A project chooses its own answer to each
  one, but it does not skip any.

### Decisions

- **We decide by reversibility.** A reversible decision is made by whoever proposes it. They log it, and the team
  confirms it in a batch. A one-way decision stops the work until it is written down as a decision record and
  accepted by its named decider.
- **A decision is one-way** when reverting the change and redeploying the previous release would not restore an
  equivalent state. That happens when data was changed in a way the old release cannot read, when something outside
  the repository started depending on it, when it let data cross a trust or tenancy boundary, or when it moved data,
  money, messages or accounts in a way that cannot be called back.
- **The named decider decides and informs.** Co-deciders are consulted. Silence within the stated window is
  consent.
- **A decision lives where it can be found.** It goes in a decision record or an issue, and chat carries only the
  link. An agreement reached in a direct message moves to its issue the same day.

### Questions and requests

- **We ask one question at a time, with a recommendation and a deadline.** Each question says what happens if no
  answer arrives. A batch of questions waits longer than one question does.
- **Requests go through the tool that tracks them.** Review requests go through the code host, and work goes
  through the board. A chat ping is not a request.
- **Absence is announced in writing.** Missing a meeting means sending a written update. A meeting without notes is
  marked as having none.

### Shared work

- **Small changes, each reviewable in one sitting.** Each change is verified before it is called done.
- **The author owns the merge.** Checks gate the merge, and a review is requested where the change is one-way.
- **Shared history is never rewritten.** We do not force-push shared branches; a branch is updated by merging, not
  by rebasing.
- **We verify the path, not the piece.** A check counts only once it has been seen failing on the real target with
  the defect present. A claim about a deployed system cites a read-only command that shows it. A claim about tests
  cites a fresh run.
- **We say what we did not check.** A result that looks like success but was not earned, such as an empty list from
  a failed call, is a failure until shown otherwise.

### Agents

- **Each agent acts for one named person, who owns what it does.** The project's `CLAUDE.md` lists what agents may
  do without asking and what they never do.
- **Agents never** message another person, change an external account, claim authorship, or bypass a check.
  AI-assisted work carries an attribution line.
- **A correction narrows an agent's scope; it never widens it.** After being corrected, an agent answers and waits.
- **Repeated corrections become setup.** A correction is saved as memory first. It becomes a skill when it recurs,
  and an always-on rule only when every session needs it.

### Joining and leaving

- **A departure is announced at least two weeks ahead.** The person leaving hands over methods, not only open
  issues. Go-live work, alarms and access move before the last week.

### Decisions every team settles

Some choices have no right answer for every team, but every team needs an explicit one. Unspoken conventions are
where friction, blame and surprises come from. This constitution does not choose them; it requires the team to
settle each one and write the answer down, with the date and who decided:

- the branching and merge strategy;
- the deployment workflow and its environments;
- the rollback workflow: who can trigger it, and whether it has been rehearsed;
- the hotfix path: how an urgent fix skips the normal flow without skipping the pipeline;
- review norms;
- the definition of done;
- versioning and release notes;
- incident handling: who responds first and where alarms go;
- response expectations: how soon a review or a question is answered, and when nobody is expected to answer;
- how these agreements change.

A new project settles them before its first change reaches production. A project adopting this constitution first
writes down what it does today, then changes it deliberately. A current practice that breaks the safety floor is
recorded as a gap with an owner and a date, not accepted as the agreement.

The kit offers a default for each, with alternatives and the signs that call for one, in
[decision points](docs/ai-sdlc/decision-points.md). Adopting a default is a decision like any other and is
recorded the same way. A default nobody looked at is not an agreement.

## 6. Where everything else lives

This document is the root. Everything below it applies the constitution and must not contradict it.

| Layer | What it holds | Where |
|---|---|---|
| Practices | how each practice is done, with the evidence behind it | [team practices](docs/ai-sdlc/practices.md), skills under `claude/skills/` |
| Agent rules | what agents load in every session | `claude/CLAUDE.md`, `claude/rules/` |
| Defaults | stack and tool choices, each with alternatives | [decision points](docs/ai-sdlc/decision-points.md), [radar](docs/ai-sdlc/radar.md), `template/` |
| Distribution | how the kit is installed | `profiles/`, `scripts/` |

When a lower layer contradicts this document, this document wins, and the lower layer is fixed.

This repository holds only what a team shares. Two kinds of kit are installed on top of it, each in its own
repository:

- **An organisation's kit** adds that organisation's brand, systems and processes.
- **A person's kit** adds their own tooling: timesheets, personal credentials, model routing, writing style.

Each adds to the layers above it and never contradicts them. A rule a team needs belongs here, not in a
personal or organisational kit.

## 7. Amending this constitution

An amendment is a pull request that changes this file. It states which velocity signal it improves (section 1) or
which part of the safety floor it protects (section 2), and the evidence for it. A practice that serves neither has
no place here.

Changes to this file are one-way decisions (section 5), accepted by the named decider:

1. The pull request stays open for a stated objection window, three working days by default, and the team is told
   it exists.
2. Any objection pauses it until the decider resolves the objection, on the pull request.
3. When the window passes without an open objection, the decider merges it and informs the team.

No approving review is required. The window gives everyone the chance to object without making anyone wait on an
approval.
