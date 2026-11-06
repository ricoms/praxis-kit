# Deriving the gate column

On-demand detail for step 4. Open it when the project's stack, layout or enforcement is not the kit's.

The copied sections never change: the safety floor, the tenancy row and the practices of the project's stage hold for
every project. What changes is **how each practice is checked**, which is the gate column. Derive it when any of these
hold:

- The stack is not ours — a client's Rails monolith, an inherited Django app, someone else's conventions to follow
- The architecture is not concept-first, so "modules split by user-facing purpose" maps to a different boundary rule
- The project already has agreed architecture characteristics, which means it already has a priority order
- The enforcement available is not `just lint` / `just test` / `just security-scan`

A gate that names a check the repository does not have is worse than none: every phase reads it, finds nothing to
check, and passes trivially.

## The method

### 1 · Take the priority order from the project, not from here

If the project has already agreed an order of characteristics, write it under Governance with a one-line pointer to
where it came from, and use it to settle conflicts between gates. Importing a second order creates two, and the one
nobody was in the room for loses.

### 2 · Map each practice to the project's own boundary and tools

| Practice | What its gate becomes when the project is not the kit's |
| --- | --- |
| Modules split by user-facing purpose | Whatever the actual boundary rule is — a trust boundary, a namespace rule, a module contract |
| Tests at the right tier | The project's tiers and their real tools |
| Threat model | Usually several gates, one per concern that has its own check |
| Upgrades classified by reversibility and trust | Same rule, that ecosystem's lockfile and audit tool |
| Traces, metrics and structured logs | Keep the requirement; the client's observability stack, if mandated |

A project-specific rule that is not a practice of the root, such as a client's own invariant, goes in an ADR and gets
its own row in the gate table, marked as the project's.

### 3 · Every gate names how a violation is caught

**This is the discipline that makes a constitution real.** For each practice, state the gate: which phase catches it, and by what mechanism.

Three honest kinds:

- **Structural** — the unsafe operation is unavailable. Nothing to disable, nothing to misconfigure. Strongest, and always prefer it
- **Pipeline** — a linter, a custom rule, a scanner threshold, a blocking test. Name the tool and the phase
- **Review** — a person reading a diff

A rule with no gate is a preference. Either find it a gate or move it out of the articles.

### 4 · The honesty pass

Go back through every gate and mark the review-enforced ones. Then, in Governance:

> Where a gate says review-enforced, that is a gap and not a decision.

List them, and say what closing each would take — usually a new lint or scanner rule. This is the highest-value paragraph in the document, because **a gate nobody can fail buys confidence without earning it**, and the confidence is what stops anyone looking again.

Expect two or three. If a first draft has none, the gates were asserted rather than checked.

### 5 · Cite enforcement that exists; flag enforcement with no owner

Where a rule is already enforced — an ADR that chose the scanners, a custom lint rule, a CI gate — **cite it rather than restating it**, so there is one home per fact.

Then check each cited mechanism has a maintainer. A custom ruleset nobody owns degrades to generic coverage while the pipeline still reports green, which is the worst available failure shape: the practice looks enforced and is not. **No maintainer is a finding**, and it belongs in an issue, not a caveat.

### 6 · What cannot be risk-accepted is already decided

Analyze can risk-accept a breach of a practice's gate with a named accepter. It can never risk-accept a breach of the safety floor; that set is fixed by the root, not chosen per project.

### 7 · Release-stage governance, which the root leaves to the team

Three things the Release gate needs and rarely has. Ask for them explicitly, and record whose they are:

- **The severity threshold** — what blocks a release, not just what blocks a merge
- **The vulnerability policy** — remediation windows per severity for what is found after shipping
- **The override record** — who may override a blocking finding, and where that decision is written down

On a client engagement these are usually **theirs, not yours**, and usually undefined. An unanswered override path means the plan absorbs stalls of unknown length, so it is a delivery question as much as a security one.

### 8 · Governance and ratification

- A change to the gate column is a pull request with a rationale and a date; the copied sections change only by copying again
- Amendments do not apply retroactively to in-flight work unless stated
- **Say whether it is ratified.** On a client engagement the gate column usually needs their sign-off, and the whole document is unenforced until spec-kit is initialised. A constitution that claims force it does not have is the same defect as a gate that cannot fail

## Shape check

Before committing, read it against these:

- Does every active practice name a gate?
- Is at least one gate structural?
- Are the review-enforced ones listed as gaps in Governance?
- Does the priority order cite where it came from?
- Does it describe the repository that actually exists?

## Worked example

A client engagement: Laravel 11 in a library consortium's own GitHub organisation, a patron-facing holds system consuming the consortium's catalog API, tenancy by `branch_id`, and an existing set of five agreed architecture characteristics.

The old fixed baseline was the wrong shape there: its concept-first article described a Python layout the project did not have. The engagement predates the stage model, so it wrote its own articles; under this method the same findings land in the gate column and the gaps:

- **Priority order** taken from the project's own characteristics: *Security → Correctness → Availability → Auditability → Maintainability*, cited to the document that set it
- **Eight articles of its own**, six non-negotiable; under this method the floor and practices would be copied and these would become gate rows and ADRs. Article I became *the trust boundary*; Article II *branch and patron scope*; III and IV carried circulation-data handling (*a hold is never double-fulfilled*, *a return is processed exactly once*); V auditability and immutability; VI the test contract; VII secrets and supply chain; VIII the AI policy, portable as-is
- **The honesty pass surfaced three review-enforced rules** — a cache key missing the branch id, recomputation of a fine amount the catalog API resolves, and personal data reaching logs. All three recorded as gaps in Governance, each closable with one new custom lint rule
- **Two cited mechanisms had no maintainer** — the custom rules that check the tenancy invariant and the trust boundary. Filed as an issue rather than footnoted
- **Two Release-stage items were the client's and did not exist** — the security gate and the vulnerability policy. Recorded as asks

Six of the eight articles are portable to any project on that stack. The priority order and Articles I to V are not, which is the point.
