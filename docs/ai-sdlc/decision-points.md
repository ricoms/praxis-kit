# Decision points

The kit is opinionated: each decision below ships a default that works. Each also names the alternatives and what in
a client's stack or constraints should move you to one. Change a default deliberately and record why in the
project's CLAUDE.md or an ADR. The tools and techniques behind these choices, adopted to rejected, are on the
[radar](radar.md).

## Chosen at render (copier questions)

| Decision | Default | Alternatives | Choose another when | Where |
|---|---|---|---|---|
| Tenancy | none: you must choose | `multi-tenant`, `single-tenant`, `single-user` | always a deliberate choice; it decides every scoping rule | `tenancy_mode`; kernel `## Tenancy` |
| Stage | none: you must choose | `explore`, `build`, `run`, `sustain` | always decided by facts: real data, promised availability, rate of change | `stage`; `CONSTITUTION.md` §4 |
| Team delivery | off | on: labels, question form, board close-out, digest, door check, ruleset, CODEOWNERS | more than one developer, or a client relationship to coordinate | `team_delivery`; [team practices](practices.md) |
| Release workflow | off | on: build once, deploy to dev on a pre-release, promote the same digest to prod, roll back through the pipeline; the project fills the registry, target-setup and deploy slots | the project deploys a container image to dev and prod | `release_workflow`; [template README](../../template/README.md) |

## Decided in the team practices and patterns

| Decision | Default | Alternatives | Choose another when | Where |
|---|---|---|---|---|
| HTTP API shape | versioned `/api/v1/` (a breaking change adds `/api/v2/` alongside); errors as `{"error": {"code", "message", "details"}}`; cursor pagination; ISO 8601 UTC timestamps; UUIDv4 ids; unauthenticated `GET /health` | the client's existing API conventions | the API extends an existing service or a published standard | project `.claude/CLAUDE.md` § Stack; `rules/security/owasp-api-top-10.md` |
| Repository layout | one repo the client inherits, from day 0 | a separate discovery repo with an end date and a migration checklist | discovery material cannot be shared with the client | Article I |
| Review | not required; the door check recommends a review on one-way changes; a second reviewer named per story | require one approval (ruleset `required_approving_review_count: 1`); require code-owner approval | regulation, audit or a client contract demands four-eyes on every change | Articles VII, XI |
| What counts as one-way | data reshaped, contracts others depend on, effects that cannot be called back, governance files — from `.github/doors.toml` | tune paths and patterns per stack; treat same-repo API consumers as two-way with atomic, versioned deploys | the stack is not Alembic/Rails/Django/SQL, or the frontend and API deploy as one unit | Article VII; `doors.toml` |
| Accepting one-way decisions | named decider accepts by agreement; CODEOWNERS requests them | decider approval required by the ruleset | decisions need a recorded, enforced sign-off | Articles IV, VII |
| Client questions | one per issue, recommendation and default-if-silent, sent within N days | batched documents | the client will not work in GitHub issues | Article VI |
| Sprints | milestones; one sprint system | an iteration field instead | the client's own planning uses iterations; never both | Article VIII |
| Story flow | spec per story, story branch, one PR per phase | trunk-based small PRs without a story branch | stories are small enough to land in one PR | Article IX |
| Foundational scenarios | expected values from observed legacy behaviour, written by a non-implementer | acceptance criteria agreed with the client | greenfield work with no legacy to observe | [foundational contract](patterns/foundational-contract.md) |
| Invariant rules | semgrep rules with fixtures, two rounds of widening then list the rest | structural guarantees only (default scopes, repositories) | the invariant can be made unrepresentable instead | [invariant rules](patterns/invariant-rules.md) |
| Release promotion | build once on a pre-release, promote the digest when dev's deployment record succeeded | Google Cloud Deploy; signed attestations with Binary Authorization | more than two environments, canaries, a console outside GitHub, or signed provenance | Article XIII; [release promotion](patterns/release-promotion.md) |
| Deploy verification | health and customer smoke checks through `APP_URL` after traffic shifts, with rollback | deploy without traffic, check a candidate URL, then promote | a bad release must never reach a customer, and the load balancer path can be tested separately | Article XII; `release.yml` |
| Environments | dev and prod (GitHub environments) | add staging (dispatch-only, drop and reseed) | testers or a client need a throwaway environment | Article XIII |
| Engagement state | a private ledger holding only what no other system holds (roster, who was told what and when, open external asks), in a store outside the repository | none: the board and chat as the record | a single developer with no client coordination | Article XV |

## Settled by the team

[`CONSTITUTION.md`](../../CONSTITUTION.md) section 5 requires every team to settle ten decisions and record the answers, and
lets a project adjust its working agreements by recording them. The `settling-agreements` skill runs both as one
session. Three
already have a default above: branching is **Story flow**, deployment is **Release promotion** and **Environments**,
and review norms are **Review**. The rows below cover the rest. Defaults marked *proposed* have no mechanism in the
kit yet. The template renders all ten into each project's `docs/agreements.md`, marked as proposed until the team
records its choice. Without `team_delivery`, review falls back to a review on one-way changes, and incidents to the
project owner with alarms in a channel the owner watches. Without `release_workflow`, the template renders no release
workflow, so the deployment, rollback and hotfix rows propose nothing and done stops at the merge.

| Decision | Default | Alternatives | Choose another when | Where |
|---|---|---|---|---|
| Rollback | automatic traffic rollback when the post-deploy smoke checks fail; a problem found later is rolled back by dispatching the release workflow on the last good tag with `rollback=true`, which redeploys that release's digest through the same checks without migrating; rehearsed once on dev before the first production release (*proposed*) | redeploy from a tagged build; a manual rollback only | the platform cannot shift traffic between revisions | Article XIII; `docs/runbooks/rollback.md`; `release.yml` |
| Hotfix path | a fix branch from `main` through the normal checks, then a final release that skips the pre-release and says so | a pre-release to dev first, even for hotfixes | the fix touches a one-way area and dev verification is worth the delay | Article XIII; `release.yml` |
| Definition of done | merged with checks green, deployed to dev and verified there, closed on the board with actual effort and waiting recorded | verified in production; accepted by the client | the client signs off each story, or dev cannot exercise the change | Articles VIII, XII, XIII |
| Versioning and release notes | semantic version tags on GitHub releases (`v1.4.0-rc.1` pre-release, then final), with notes generated by GitHub | a CHANGELOG generated from conventional commits (git-cliff, release-please); user-facing notes from per-change fragments | people outside the team read the release notes | `release.yml`; `authoring-project-docs` |
| Incident handling | the on-call role responds first, the architecture decider is accountable, alarms go to the team channel, and each production incident gets a blameless postmortem | the client's platform team on call; a paging rotation | the service has an off-hours commitment | Articles IV, XIV; `docs/raci.md`; `docs/runbooks/incidents/` |
| Response expectations | reviews and questions answered within one working day; nobody is expected to answer outside agreed working hours except on-call during an incident (*proposed*) | shorter windows during a release week; stated overlap hours across time zones | the team spans time zones, or a client contract sets response times | constitution section 1 |
| Changing these agreements | a PR to the agreements record; the named decider decides and informs, and silence for three working days is consent | decided at a retrospective | the team already runs regular retrospectives | Article IV |
