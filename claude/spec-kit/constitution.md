# [PROJECT_NAME] constitution

<!-- Skeleton. An agent fills each COPY slot word for word from the named source, keeping its line breaks, then runs
the check in `bootstrapping-with-spec-kit` step 3. Nothing outside the slots is project-specific except the
placeholders in brackets. -->

Stage: `[STAGE]`. Tenancy: `[TENANCY]`. Copied on [DATE] from `CONSTITUTION.md` at praxis-kit commit `[COMMIT]`.

This file applies the kit's root constitution to this project for spec-kit's phase gates. The copied sections are not
edited here: when the stage, the tenancy mode or the root changes, copy them again. A deviation specific to this
project is an ADR. Links inside copied text are relative to the praxis-kit repository, not to this one.

## Safety floor

These hold at every stage; rule 5 names the floor's only two exceptions. `/speckit.analyze` reports any plan that breaks
one as Critical, and no risk acceptance applies. Two of them have gates of their own:

- Rule 4: Plan names the scoping identifier and where it comes from. Analyze rejects one taken from a request body,
  a query string or an LLM tool argument instead of the authenticated identity.
- Rule 5: Plan names every manual operational step. Analyze reports each one as Critical, except the bootstrap and
  the manual secret rotation that rule 5 allows. Plan records who runs each and how they check the identity it runs
  as, and for a rotation, the issue that approves it.

<!-- copy: CONSTITUTION.md -->
[COPY the five numbered rules of CONSTITUTION.md section 2]
<!-- end copy -->

## Tenancy

<!-- copy: rules/glossary.md -->
[COPY the tenancy table's header and separator rows from rules/glossary.md, then the row for this tenancy mode]
<!-- end copy -->

## Practices active at this stage

New code meets each practice as a gate. Existing code meets it as a ratchet:

<!-- copy: CONSTITUTION.md -->
[COPY the two bullets of CONSTITUTION.md section 3 that define a gate and a ratchet]
<!-- end copy -->

<!-- copy: CONSTITUTION.md -->
[COPY the practice table's header and separator rows from CONSTITUTION.md section 4, then each row active at this stage]
<!-- end copy -->

## Phase gates

Keep the rows for the practices active above and delete the others. Where a practice's cell gives a form ("one smoke
check", "logs", "per phase", "new code", "beyond fixes"), its gate applies in that form only. A gate that says
"review" is enforced only by a person reading the artifact; list each one under Governance as a gap.

| Practice | Spec-kit gate |
|---|---|
| Upgrades classified by reversibility and trust, after a cooldown (section 2) | Plan names every new or upgraded dependency, including prompt, model and dataset versions, with its version bound and class. More than five new dependencies need a stated reason. Tasks include a dependency-review task |
| Tests at the right tier: scenarios for cross-module flows, component tests for modules, structural checks | Specify writes each acceptance scenario as a fenced `gherkin` block. Before Plan, the person approving the spec saves the blocks as feature files under `tests/foundational/`, writes or approves their `Then` steps, and the spec links to the files. Plan's scenario tier is those files. Tasks put test tasks, including the `Given` and `When` steps, before implementation tasks. Analyze rejects a plan missing an active tier, or a spec whose acceptance scenarios have no feature file |
| Strictest typing and lint the language offers, including the complexity limit | Implement passes the project's lint and type checks with no raised threshold and no new exemption |
| Modules split by user-facing purpose, with flows between them kept explicit | Specify names the modules the feature touches. Plan declares any new public interface. Analyze runs the boundary check |
| A specification before implementing a non-trivial feature | Specify produces the spec before plan starts |
| A decision record for every one-way decision (section 5) | Plan flags each one-way decision. Checklist confirms its ADR exists and names a decider |
| Threat model for features that touch authentication, personal data, money, a tenancy boundary, an LLM tool surface or an external integration | Specify flags the trigger. It classifies the data (`classifying-data`) and names abuse scenarios (`writing-abuse-scenarios`). Plan writes the threat model (`threat-modeling`) |
| Security scan of code, secrets and infrastructure | Implement runs the project's security scan at the stage's cadence |
| Dependency audit for known vulnerabilities | Not per feature: runs at the stage's cadence (`auditing-deps`) |
| Traces, metrics and structured logs | Plan declares the feature's spans, metrics and log events. Checklist confirms they are emitted |
| Service levels, with alerts routed to the team | Plan states whether the feature changes a service level indicator. Checklist confirms `docs/slo.md` is current and each new alert has a runbook row |
| Smoke checks after every deploy, with automatic rollback | Checklist confirms each new customer entry path has a smoke check |
| Backups, with a restore rehearsed before availability is promised, then yearly and after any storage change | Plan flags a storage change. Checklist confirms a restore rehearsal follows it |
| Access granted on joining and removed on leaving, checked whenever someone leaves | Not per feature: review |
| Secrets rotated on schedule, each rotation logged | Plan names any new secret. Checklist confirms it is in the runbook index's secrets inventory |
| The board as the record of work, with actual effort and waiting time on close | Tasks become issues on the board. Done records actual effort and waiting time |

## Governance

- `/speckit.analyze` reports a breach of the safety floor or of an active practice's gate as Critical. A practice breach
  may be risk-accepted by a named accepter, recorded in the plan; a safety-floor breach may not.
- Agreements between people (branching, review, done, incidents) live in `docs/agreements.md`, not here.
- Stack choices live in the project's `.claude/CLAUDE.md` and its ADRs, not here.
- Gaps: [LIST the gates above that say "review", and any safety-floor rule the project cannot meet yet, each with an
  owner and a date]
