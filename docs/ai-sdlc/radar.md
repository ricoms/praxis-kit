# Technology radar

Generated from [`radar.toml`](radar.toml) by `hugin radar render`; edit the data, not this page. Each entry
links the file that backs it, and the check fails when that file stops saying so. Decisions with their
alternatives are in [decision points](decision-points.md).

| Ring | Meaning |
|---|---|
| Adopt | the template ships it |
| Trial | a documented alternative, with when to pick it |
| Assess | a hypothesis: untried, or resting on one engagement |
| Hold | rejected; do not reintroduce without new evidence |

## Techniques

| Ring | Entry | Why | Backed by |
|---|---|---|---|
| Adopt | Build once, promote the digest | Prod runs the image dev tested; promotion is gated on dev's deployment record | [`docs/ai-sdlc/patterns/release-promotion.md`](patterns/release-promotion.md) |
| Adopt | Advisory one-way/two-way door check | Labels changes that revert + redeploy cannot undo and recommends a review; never blocks | [`template/src/.github/doors.toml`](../../template/src/.github/doors.toml) |
| Adopt | 3-day dependency cooldown | Newest release at least 3 days old; an advisory fix goes in immediately | [`claude/skills/auditing-deps/SKILL.md`](../../claude/skills/auditing-deps/SKILL.md) |
| Adopt | Smoke checks with rollback to the serving revision | Customer-path checks after traffic shifts; failure returns traffic to the revision that had it | [`template/src/.github/workflows/release.yml.jinja`](../../template/src/.github/workflows/release.yml.jinja) |
| Adopt | One client question per issue | Each question has an owner, a recommendation and a default if the client stays silent | [`template/src/.github/ISSUE_TEMPLATE/client-question.yml.jinja`](../../template/src/.github/ISSUE_TEMPLATE/client-question.yml.jinja) |
| Adopt | Foundational scenarios from observed legacy behaviour | Expected values come from what the old system did, written by someone who did not implement it | [`docs/ai-sdlc/patterns/foundational-contract.md`](patterns/foundational-contract.md) |
| Adopt | Invariant rules with fixtures | Static-analysis rules for the breach vector, each with passing and failing fixtures | [`docs/ai-sdlc/patterns/invariant-rules.md`](patterns/invariant-rules.md) |
| Adopt | Verify the path, not the piece | A gate counts as tested only when it fails on the real target with the bug present | [`claude/skills/verifying-the-path/SKILL.md`](../../claude/skills/verifying-the-path/SKILL.md) |
| Adopt | Private-reference check | Fails CI on links to chat archives and other records the inheriting client cannot open | [`template/src/scripts/private-refs.sh`](../../template/src/scripts/private-refs.sh) |
| Trial | Staging environment | Dispatch-only, dropped and reseeded; worth it when testers or the client need a throwaway environment | [`docs/ai-sdlc/decision-points.md`](decision-points.md) |
| Trial | Trunk-based small PRs without a story branch | When stories are small enough to land in one PR | [`docs/ai-sdlc/decision-points.md`](decision-points.md) |
| Assess | Effort cap on custom static-analysis rules | Two rounds of widening, then list the residual forms; rests on one engagement | [`docs/ai-sdlc/practices.md`](practices.md) |
| Assess | Ledger fed from observed chat and GitHub events | Would replace manual writes to the engagement ledger; untried | [`docs/ai-sdlc/practices.md`](practices.md) |
| Assess | Object-centric event log of the delivery lifecycle | Would measure change fail rate, rework and recovery time from issues, PRs, CI runs, releases and deployments; untried | [`docs/references/2508.00116-no-ai-without-pi.md`](../../docs/references/2508.00116-no-ai-without-pi.md) |
| Hold | Required approving reviews | Checks gate the merge and the author owns it; use only where regulation or a contract demands four-eyes | [`docs/ai-sdlc/practices.md`](practices.md) |
| Hold | ADR-link gate | Any link satisfies it; a path is not a decision | [`docs/ai-sdlc/practices.md`](practices.md) |
| Hold | Approval by frozen document package | The frozen copy went stale within hours and the approval tag was never used | [`docs/ai-sdlc/practices.md`](practices.md) |

## Tools

| Ring | Entry | Why | Backed by |
|---|---|---|---|
| Adopt | copier | Renders the project template; answers are kept for updates | [`copier.yml`](../../copier.yml) |
| Adopt | Dependabot | One PR per dependency after the cooldown; security updates skip it | [`template/src/.github/dependabot.yml.jinja`](../../template/src/.github/dependabot.yml.jinja) |
| Adopt | gitleaks | Secret scan over full history in CI and at commit | [`template/src/.github/workflows/ci.yml.jinja`](../../template/src/.github/workflows/ci.yml.jinja) |
| Adopt | actionlint + shellcheck | The kit lints every rendered workflow and script | [`src/hugin/check_template.py`](../../src/hugin/check_template.py) |
| Adopt | just | One task runner for install, test, lint and smoke | [`template/src/justfile.jinja`](../../template/src/justfile.jinja) |
| Trial | Google Cloud Deploy | More than two environments, canaries or a release console outside GitHub | [`docs/ai-sdlc/patterns/release-promotion.md`](patterns/release-promotion.md) |
| Trial | Binary Authorization attestations | When signed provenance must be enforced at deploy | [`docs/ai-sdlc/decision-points.md`](decision-points.md) |
| Trial | Dependabot groups | Batch two-way, low-trust-risk upgrades in one PR; one-way and high-trust-risk upgrades still go alone | [`claude/skills/auditing-deps/SKILL.md`](../../claude/skills/auditing-deps/SKILL.md) |

## Platforms

| Ring | Entry | Why | Backed by |
|---|---|---|---|
| Adopt | GitHub Actions, rulesets and Projects | CI, required checks without required reviews, and the board's fields | [`template/src/.github/rulesets/main.json.jinja`](../../template/src/.github/rulesets/main.json.jinja) |
| Hold | Service-account keys in CI | Long-lived secrets in CI; short-lived federated credentials (WIF, OIDC) replace them | [`claude/rules/security/secrets-lifecycle.md`](../../claude/rules/security/secrets-lifecycle.md) |

## Languages and frameworks

| Ring | Entry | Why | Backed by |
|---|---|---|---|
