# Team practices

How a multi-developer team that builds with AI agents carries out the constitution. The values, the safety floor,
the stages and the agreements between people live in [`CONSTITUTION.md`](../../CONSTITUTION.md); this page
applies them and must not contradict them. It extends the single-owner loop in
[`../ai-driven-lifecycle.md`](../ai-driven-lifecycle.md) to a team.

This page is the index, not the mechanism. Each article names what enforces it. Every choice the kit makes, with
its default and alternatives, is listed in [decision points](decision-points.md); the tools and techniques, by
ring, in the [radar](radar.md). An article that could be a check
but is only written here is a defect in the kit.

**Status:** from one engagement, read three times from mid-delivery to the close and summarised in
[evidence](evidence.md). Articles marked *hypothesis* rest on that engagement alone; revise after a second engagement.

**Enforcement tags:** `check` CI, hook or Action fails or reports · `template` the bootstrap creates it ·
`skill` an agent procedure · `prose` written rule only. `(planned)` means the kit does not ship it yet. Template
items ship behind the copier question `team_delivery`; skills install with the `team-delivery` profile. Backticked paths are files in a rendered team project and
backticked skill names are skills in this repo; `just check-template` fails when one is missing or when a `check`,
`template` or `skill` claim names nothing and is not `(planned)`.

**Evidence:** each article's Evidence line links the section of the [engagement summary](evidence.md) it rests on.
Figures there are rounded ratios from that one engagement.

---

## Part A — Structure

### I. One repo, from day 0

The repo the client inherits is the only repo. Specs, ADRs, skills and open questions live there from the first
commit. Coordination state (roster, commercials, our read on the client) stays out of git. If a separate discovery
repo cannot be avoided, it gets an end date and a migration checklist: ADRs, constitution, open issues, skills,
and a grep for back-references.

- Enforced: `template` `README.md`, `docs/runbooks/` · `check` `scripts/private-refs.sh` with `.github/private-refs.txt`
  in CI fails on private repo names, internal links or other listed content
- Evidence: [repository](evidence.md#repository-and-checks) — ADRs moved by hand, dozens of back-references, about
  a third of the discovery issues stranded at archive, skills that never loaded.

### II. Team topology

Declare at bootstrap who plays which role and how the team interacts with each neighbour.

| Role | Owns | Exit criterion |
|---|---|---|
| Stream-aligned team (developers + their agents) | stories end to end | — |
| Enabling / platform (often the AI architect) | CI/CD, gates, skills, board automation | developers author and maintain skills themselves |
| Architecture decider | one-way decisions | — |
| Secret custodian | rotating and revoking secrets by hand, elevated only for the rotation | — |
| Flow (PM / PMO) | sprint, board, client cadence | — |

Interaction with an external platform team defaults to *as-a-service* (vendored contract + mock), switching to
*collaboration* only during incidents. Name the enabling role's bus factor as a risk until its exit criterion holds.

Departures follow the constitution's joining-and-leaving agreement. In a team project, the methods to hand over are
verification, triage and releases, and large inputs, such as a pentest report, stay out of someone's last days.

- Enforced: `template` topology pointer in `.claude/CLAUDE.md` · `prose`
- Evidence: [know-how](evidence.md#concentration-of-know-how) — the enabling role merged many small changes and did
  most board administration while developers wrote most of the code; developers wrote team skills early.
  *Hypothesis* beyond this team size. The same concentration is the hand-over risk: people who leave can still hold
  open issues, reviews, alarms and operator access, and a PM who learns of it late has too little time to reassign
  them or transfer the methods.

### III. Agents are members with listed rights

The constitution's agreements on agents apply, as adjusted in the project's `docs/agreements.md`. In a team project, the agent-rights block in `.claude/CLAUDE.md`
lists what agents may do without asking (branch, change, run checks, open PR, close-out after merge) and adds two
things they never do: close an estimated issue without asking for Actual, and override git identity. One
attribution trailer form is the default.

- Enforced: `template` agent-rights block in `.claude/CLAUDE.md` · `prose` one attribution trailer form; a mixed
  form is accepted by the accountable human, not gated
- Evidence: [agents](evidence.md#agents-and-ai-use) — actuals lost when an agent closed issues without asking; two
  trailer forms in use.

### IV. RACI by decision type

One matrix of decision types, one Accountable per row, roles not names. The role→person mapping is private
(Part D). Defaults:

| Decision | R | A | C | I |
|---|---|---|---|---|
| Scope change | PM | client lead | architecture decider | team |
| One-way decision (reverting would not restore an equivalent state, `CONSTITUTION.md` §5) | proposer | named decider | co-deciders | team |
| Reversible decision | proposer | proposer | — | log, batch-confirm |
| Send a client question | author | author | team (internal check) | PM |
| Merge code | author | author | reviewer, recommended for one-way doors | — |
| Merge docs | author | author | — | — |
| Release to prod | release owner | architecture decider | client lead | client |
| Change in client org / account | proposer | client lead | — | client |
| Sprint plan | PM | sprint owner | team | client |
| Actual / Waiting on close | assignee | assignee | — | PM |
| AI usage budget | budget owner | engagement lead | team | — |
| Incident | on-call | architecture decider | client platform | client |

Each row's Accountable is the named decider the constitution's decision agreements refer to.

- Enforced: `template` `.github/CODEOWNERS` requests the named decider on ADRs; acceptance is by agreement, not a
  gate · `check` `scripts/adr-lint.sh` requires a Status and a named Deciders line on every ADR ·
  `template` `docs/raci.md`
- Evidence: [decisions](evidence.md#questions-and-decisions) — approvals moved faster once the team switched to
  decide-and-inform. [Ledger](evidence.md#engagement-ledger) — RACI existed only as defaults, not per decision type.

## Part B — Flow

### V. Documents vs issues by lifecycle

What evolves and gets reviewed is a document, changed by PR. What has an owner and a clock is an issue. Approval
is a reproducible build from a commit, not a frozen copy. Material received from the client is stored verbatim and
never edited.

- Enforced: `template` `docs/adr/0001-record-architecture-decisions.md` · `prose` stored client material stays
  verbatim; a check was not adopted, no edit was ever observed
- Evidence: [decisions](evidence.md#questions-and-decisions) — approval tag never used;
  frozen package stale within hours.

### VI. Questions: one per issue, with a send deadline

Client questions follow the constitution's one-question agreement, one issue each. Labels `owner:` and
`asked`. Internal check first, then send within N working days. Replies go on the issue. Keep the open asks per
client contact few and visible: single questions are answered in a day, batches wait.

- Enforced: `template` `.github/ISSUE_TEMPLATE/client-question.yml`, `.github/labels.tsv` · `check`
  `.github/workflows/digest.yml`
- Evidence: [questions](evidence.md#questions-and-decisions) — client median answer about a day once asked;
  internal questions about five times as long; drafted questions unsent for weeks; single questions answered
  fastest, batches open longer, all on one client contact.

### VII. Decisions by reversibility

The constitution defines reversible and one-way decisions. In a team project, a one-way decision is written as an
ADR in two PRs, a proposal then an acceptance, linked to its issue; CODEOWNERS requests the named decider.

Two details of the one-way definition matter here. A same-repo frontend counts as an outside dependant unless both
deploy atomically with versioned assets. Governance files are one-way, so the rules cannot be loosened in the change
they govern. Changes made outside a PR stay under Article X.

- Enforced: `check` `.github/workflows/doors.yml` with `.github/doors.toml` labels every PR door:one-way or door:two-way
  and, on one-way, recommends a review and states that the ADR is required, never blocking; no label means unclassified · `template` `.github/pull_request_template.md` asks for the ADR · `prose`. An
  ADR-link gate was rejected: it would be satisfied by any link
- Evidence: [decisions](evidence.md#questions-and-decisions) — the test categories kept expensive decisions from
  passing as cheap; ADRs that followed failures. [Review](evidence.md#review-and-one-way-changes) — over every merged
  PR, about one in four one-way and about two in five of those reviewed; nearly every sampled unreviewed one-way PR
  was one-way on reading.

### VIII. The board is the source

One sprint system (milestones). Built-in project workflows keep Status. On close: Remaining Work 0, Actual asked,
Waiting recorded separately as decision latency. Estimates are re-weighted per phase from the team's own ratios.

- Enforced: `template` `scripts/board/bootstrap-project.sh`, `docs/runbooks/board.md` · `check`
  `.github/workflows/close-out.yml` · `skill` `reading-delivery-velocity`
- Evidence: [board](evidence.md#board-and-estimates) — built-in workflows zero drift; manual fields drifted until
  the agent rule; plan about 1.3×, verify about 0.7×; two sprint systems disagreed.

### IX. Story flow

Spec per story. A story branch with one PR per spec phase; main stays releasable. Foundational scenarios are written
by someone other than the implementer, and removing one requires a manifest change in the same diff. Freeze docs
and issues before a readout or delivery.

- Enforced: `prose` [foundational contract](patterns/foundational-contract.md): authorship rule, manifest and pending
  recipes per stack · `skill` `bootstrapping-with-spec-kit`
- Evidence: [repository](evidence.md#repository-and-checks) — AI-generated PRs reviewable in one sitting;
  [communication](evidence.md#communication-and-signals) — delivery day collided with new issues.

## Part C — Quality and release

### X. Anything checkable is a check

Local `just ci` runs what CI's `checks` job runs. Invariants from ADRs become custom static-analysis rules with fixtures that
run first; rules are never weakened or fixtures deleted. Each rule gets an effort cap: past it, record the residual
form for review instead of chasing every syntax variant. The security gate is not path-filtered; expect red days
from new advisories and fix them the same day.

- Enforced: `template` `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `justfile` · `prose`
  [invariant rules](patterns/invariant-rules.md): one rule per invariant with fixtures, two-round effort cap
- Evidence: [checks](evidence.md#repository-and-checks) — CI caught contract drift, foundational failures and boot
  failures on 2–3% of runs; a long run of rule fixes chasing syntax forms; a docs-only day went red from an
  advisory.

### XI. Review and merge

Merging follows the safety floor and the constitution's shared-work agreements, as adjusted in the project's
`docs/agreements.md`. Reviews are not required. CODEOWNERS requests the area's owners automatically; the door check
(Article VII) recommends a review on one-way changes. Review requests go through GitHub, not chat. Name a second
reviewer per story, so review requests do not queue on one person.

- Enforced: `template` `.github/rulesets/main.json` (required checks, squash only, no force-push, no bypass, no
  required approvals), `.github/CODEOWNERS` (requests owners), `.github/pull_request_template.md` · `check`
  `.github/workflows/doors.yml` and `.github/workflows/digest.yml` make one-way and waiting PRs visible
- Evidence: [review](evidence.md#review-and-one-way-changes) — about two thirds of merged PRs, and about nine in
  ten in the discovery repo, without an outside reviewer, while one-way application changes were mostly reviewed;
  about two in five one-way changes reviewed; review the internal bottleneck, with requests going through chat and
  queueing on a few people.

### XII. Verify the path, not the piece

The constitution's verify-the-path agreement applies. Deploy smoke tests exercise customer-facing behaviour, not
only the version endpoint. A check that fails fails the run and says so in team chat; a deployment recorded as a
success over a failed check is a silent failure.

Security testing is prepared before a vendor is booked: the in-scope list generated from the API contract and the
deployed layout, the rules of engagement in an issue, tester onboarding and offboarding with a removal date, the
alarms testers will trip routed to the team, and a release freeze agreed with the client.

- Enforced: `template` `.github/smoke.txt` and `scripts/smoke.sh`, run by `.github/workflows/release.yml` after
  every deploy, rolling traffic back to the previous revision on failure · `skill` `verifying-the-path`
  · `template` `.github/ISSUE_TEMPLATE/security-test.yml`, `scripts/security-scope.py`,
  `docs/runbooks/security-testing.md`
- Evidence: [signals](evidence.md#communication-and-signals) — customer-facing requests failed while the version
  smoke passed; a coverage claim contradicted by a fresh report; a check failed, the deployment recorded success and
  nobody saw it; security testing on short notice, its scope spread over chat messages and its rules agreed in a
  private message.

### XIII. Release through the pipeline only

Build once, push only on releases. A pre-release builds the image once, tests it, pushes it and deploys it to dev;
marking it final promotes that same digest to prod without building, once GitHub's deployment record shows dev
passed. A release that skipped the pre-release builds once and goes straight to prod, and says so. Each
environment's database is migrated right before that environment gets the new version; migrations work with the
previous release. Nothing reaches a shared environment any other way, except the bootstrap and the secret rotation
that rule 5 of the safety floor allows. Demos run scripted on dev and count as verification; keep a per-release demo of what dev
runs, so nobody outside the team has to ask.

- Enforced: `template` `.github/workflows/release.yml`, `docs/runbooks/rollback.md` · `prose` alternatives in
  [release promotion](patterns/release-promotion.md)
- Evidence: [repository](evidence.md#repository-and-checks) — releases about weekly, each built once and deployed
  to staging several times, with automatic rollback on a failed deploy.

## Part D — Communication and state

### XIV. Communication modalities

| Message | Record lives in | Announced in | Never |
|---|---|---|---|
| Decision | ADR or issue | team chat, with link | chat only |
| Client question | issue (Art. VI) | shared channel, batched | unsent past its deadline |
| Approval, commercials | email | — | chat |
| Status | board → weekly deck | client update | written from memory |
| Review | GitHub review request | — | chat ping |
| Client account change | heads-up naming every resource touched and untouched | shared channel | after the fact |
| Alarm | team channel | — | one person's inbox |

Absences and agreements reached in a direct message follow the constitution's agreements on questions and decisions.

Syncs: daily standup ≤15 min, weekly planning, weekly client update/demo, optional architect–developer pairing.
Meeting notes or transcripts are the record for absentees: one note-taker and one record language per meeting, and
a meeting without notes is marked as such. Team chat may use the team's language; the repo and
the shared channel use the client's. Shared artifacts must open for every recipient; export what must last.

- Enforced: `check` `.github/workflows/digest.yml` · `prose`
- Evidence: [communication](evidence.md#communication-and-signals) — client asked for status early; could not find
  the architecture doc; decks some could not open; decisions made async rather than in meetings; notes thinned
  toward the close; AI notes of the same meeting disagreeing on owners and dates; testing rules agreed only in a
  private message; alarms reaching one inbox.

### XV. Engagement ledger

A private, temporal store of facts no other system holds: roster and role→person mapping, the RACI instance, who
was told what and when through which channel, open external asks. Anything with a system of record elsewhere
(issues, board, roadmap) is read through, not copied. Writes use closed vocabularies (message kinds, channels,
audience keys validated against the roster). Log a message after it is sent.

- Enforced: `prose` · closed vocabularies are validated by the engagement-state tool itself on write, not by
  this kit · *hypothesis*: ingest observed chat and GitHub events instead of manual writes
- Evidence: [ledger](evidence.md#engagement-ledger) — the comms log stayed live; roadmap, weekly updates and
  pending asks duplicated other systems and went stale; message kinds multiplied and audience keys were
  inconsistent.

### XVI. AI operations

Name an AI usage budget owner and a fallback (extra seats or overage) before the first sprint. Personal automations
do not run on team quota. Corrections become setup as the constitution's agreements on agents describe. Before an
agent sweeps a source, check which account its connector is signed in to; an empty result is an error until shown
otherwise.

- Enforced: `prose` · `skill` `authoring-instruction-files`
- Evidence: [AI use](evidence.md#agents-and-ai-use) — quota exhausted on several days across developers; nearly
  half of agent-memory entries were team-process rules learned by correction; a sweep against connectors signed in
  to the wrong account returned empty results that read like "nothing new".
