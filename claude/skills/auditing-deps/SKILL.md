---
name: auditing-deps
description: >-
  Audit deps for CVEs, supply-chain risk, stale maintenance. uv / pnpm /
  cargo runbooks + triage rubric + CVE response. Use after dep changes,
  weekly, or when a CVE drops.
allowed-tools: Bash(uv *) Bash(pnpm *) Bash(cargo *) Bash(pip-audit *) Bash(trivy *) Bash(git *) Read Grep Glob
metadata:
  tags:
    - security
    - supply-chain
    - dependencies
    - owasp-api-top-10
---

# Auditing Deps

Supply-chain attacks now outnumber traditional code vulns. Dep audits are not optional.

## Audit checklist

Copy this checklist into your response and tick off as you progress:

```
Dep Audit Progress:
- [ ] Step 1: Run scanners (uv run pip-audit / pnpm audit / cargo audit / cargo deny check)
- [ ] Step 2: Diff lockfiles vs main (git diff main -- pnpm-lock.yaml uv.lock Cargo.lock)
- [ ] Step 3: Triage findings by severity + reachability (effective severity, not just CVSS)
- [ ] Step 4: For each Critical/High: pin to safe version, audit code paths touching the dep
- [ ] Step 5: Rotate any secrets the dep had access to (env vars, mounted files)
- [ ] Step 6: Open tracking issue per finding with reach analysis
- [ ] Step 7: Document in docs/runbooks/security-incidents.md (if compromise response)
```

## Run the scanners

```bash
# Python
cd backend && uv run pip-audit --strict --vulnerability-service=osv

# Node
cd frontend && pnpm audit --prod --audit-level=high

# Rust
cargo audit --deny warnings
cargo deny check advisories sources licenses bans

# Container images (if Docker images present)
trivy image --severity HIGH,CRITICAL <image:tag>
```

`just security-scan` should orchestrate these (see `scanning-security` skill for the gate).

## Severity rubric

| Severity | Action | Timeline |
|---|---|---|
| Critical | Block merge / hotfix-patch / pin to safe version + audit usage | Same day |
| High | Block merge unless explicitly accepted with justification + tracking issue | Within 7 days |
| Medium | Track in security backlog; upgrade in next planned dep refresh | Within 30 days |
| Low | Bundle into next dep refresh | Quarterly |

Use the CVE's CVSS as a starting point but override down for unreachable code paths (CVE in a sub-dep that your call graph never touches → effective Low) and override up for paths that touch auth, secrets, or tenant boundaries (CVE in your authn lib → effective Critical regardless of CVSS).

## Lockfile review

Lockfiles are the actual artifact deployed. Diff them on PRs that touch deps:

```bash
git diff main -- pnpm-lock.yaml uv.lock Cargo.lock
```

Watch for:

- **New transitive deps appearing** without a top-level dep change — supply-chain shenanigans
- **Version churn across many deps** in one change — fine only for a two-way, low-trust-risk group (see Upgrade discipline); otherwise split it
- **Removed packages still in lockfile** — incomplete dep change
- **Multiple versions of the same package** — bloat, hard to patch when CVE drops

## Maintenance assessment (NON-NEGOTIABLE per CLAUDE.md)

Before *recommending* any dep, verify it's actively maintained. Stale = not safe regardless of CVSS:

- Last commit > 12 months ago → **stale**
- No response to issues / PRs > 6 months → **stale**
- Major version still 0.x with no progress → **immature; reconsider**
- Sole maintainer, gone silent → **stale**

Preference order:

1. Official / vendor-provided libs (e.g., `anthropic`, `@anthropic-ai/sdk`, `boto3`)
2. Well-funded foundation projects (CNCF, Apache, OpenJS, PSF)
3. Active community projects (multiple maintainers, recent commits, responsive issues)
4. Inline implementation if the dep is small enough to write yourself

**NEVER** describe a stale dep as "battle-tested" or "widely-used" without checking commit history and issue activity first. "Many GitHub stars" is not a maintenance signal.

## Pinning policy

This table is the single home for pinning syntax; `CLAUDE.md` and the constitution point here. npm and Cargo cap stable libraries at the minor version, stricter than Python's major cap, so `npm install` or `cargo update` never pulls an unreviewed minor release. On npm, high-risk libraries therefore use the same `~` as stable ones.

| Manager | Stable lib | High-risk lib | Compromised-history lib |
|---|---|---|---|
| `pyproject.toml` | `>=x.y,<X+1.0` (cap major) | `>=x.y,<x.Y+1` (cap minor) | `==x.y.z` (exact) |
| `package.json` | `~x.y.z` | `~x.y.z` (still ~) | `x.y.z` exact, no caret/tilde |
| `Cargo.toml` | `=x.y` | `=x.y.z` exact | `=x.y.z` exact |

**No open `>=`** — the pre-commit lint enforces this. Lockfiles always committed.

**Which version:** the newest release that is at least 3 days old, so a broken or compromised release has time to be
caught; **immediately** when the version in use has a security advisory. Bounds are set from that version, never left
stale. Dependabot implements it with `cooldown: default-days: 3`, which never delays security updates, and opens one
PR per dependency.

| Artifact | Pin |
|---|---|
| Terraform core | `required_version = ">= x.y.z, < X+1.0.0"` |
| Terraform providers | `version = "x.y.z"` exact (`terraform init` would otherwise take a release younger than 3 days) |
| GitHub Actions | full commit SHA with a `# vX.Y.Z` comment |
| Container images | `image:tag@sha256:<digest>` |

The package manager enforces the cooldown itself where it can, so `add`, `lock --upgrade` and a fresh lock all
respect it, not only Dependabot's PRs:

| Manager | Setting |
|---|---|
| uv (≥ 0.9.17) | `[tool.uv] exclude-newer = "3 days"` in `pyproject.toml`; the lockfile records the span, not a date |
| pip (≥ 26.1) | `--uploaded-prior-to P3D`, or the same key in pip config |
| npm (≥ 11.10) | `min-release-age=3` (days) in `.npmrc` |
| pnpm (≥ 10.16) | `minimumReleaseAge: 4320` (minutes) in `pnpm-workspace.yaml` |
| Bun | `[install] minimumReleaseAge = 259200` (seconds) in `bunfig.toml` |
| Cargo, Terraform, Actions, images | no built-in setting: Dependabot's cooldown |

**On an advisory** for a version in use: exempt only that package from the cooldown (uv:
`exclude-newer-package = { <name> = false }`, then `uv lock --upgrade-package <name>`; pnpm: list it under
`minimumReleaseAgeExclude`), ship the fixed release, and
remove the exemption once the cooldown has passed.

## CVE response runbook

When a CVE drops for a dep you might use:

1. **Check lockfiles** — `grep -r "<package-name>" *.lock package.json pyproject.toml Cargo.toml`
2. **Determine reachability** — does your code path touch the vulnerable function? (`grep` for the function name in source)
3. **Pin to a safe version** — exact pin in lockfile + manifest
4. **Audit logs / IOCs** — does the CVE come with indicators (specific URLs, hashes, behavior)? Search recent logs for evidence
5. **Rotate any secrets** the dep had access to (env vars, mounted files)
6. **Open a tracking issue** with reach analysis and remediation
7. **Document in `docs/runbooks/security-incidents.md`** — what was found, what was rotated, what was patched

## Upgrade discipline

Every upgrade is classified on two axes before it merges, and the person who merges it owns the classification.
Time between upgrades does not matter; what matters is that each risky upgrade can be tested and reverted on its own.

**Reversibility** follows the one-way door definition in `CONSTITUTION.md`. Most upgrades are two-way: reverting the
lockfile and redeploying restores the previous state. An upgrade is one-way when it migrates data (an ORM or
database driver that changes the schema or storage format), changes a contract other systems depend on (a
serializer, an API client, a wire protocol), or changes what credentials or tokens look like (auth or crypto
libraries).

**Trust risk** is high when the upgrade adds a new dependency, comes from a new publisher or maintainer, runs install
scripts or native build steps, runs where secrets are present (CI, or the auth, tenant or data path), or touches a
package in the high-risk or compromised-history tier of the pinning table. A malicious release that ran with secrets
is a one-way door even when its code change is not: reverting the lockfile does not undo what it sent out.

| Upgrade | Handling |
|---|---|
| Two-way, low trust risk | May be grouped, e.g. a weekly batch of patch and minor upgrades (Dependabot `groups`), in its own commit with the full suite |
| One-way | Alone, changelog read, door label on the PR, reviewed; canary deploy when it is on the auth, tenant or data path |
| High trust risk | Alone, cooldown never skipped except for an advisory fix, publisher and provenance checked, named owner in the PR |

For every upgrade, whatever its class:

- Read the changelog of anything that is not a patch release
- Run the full test suite

## Per-stack notes

### Python (uv)

- `uv lock --upgrade-package <name>` — single-package upgrade
- `uv tree` — see the dep tree, find why a transitive is included
- Set `tool.uv.dev-dependencies` for dev-only — they don't ship to prod, audit lighter

### Node (pnpm)

- `pnpm why <package>` — find the import chain
- `pnpm update --interactive --latest` ignores the manifest's bounds and crosses majors. Use it only to pick candidates, then classify each one (see Upgrade discipline)
- `pnpm dedupe` — collapse duplicate versions (after careful review)

### Rust (cargo)

- `cargo tree` — dep tree
- `cargo deny check advisories` — wraps RustSec advisory DB
- `cargo deny check bans` — enforce a banned-deps list (e.g., known-bad crates)
- `cargo deny check sources` — only allow registries you trust

## Anti-patterns

- **Unclassified refreshes** ("update everything to latest" in one change). Mixing a one-way or high-trust-risk upgrade into a batch hides it and makes the batch impossible to bisect
- **Open `>=` ranges**. Surprise upgrades in CI
- **Ignoring transitive deps**. Most CVEs are in transitive
- **Stale deps with high stars**. Stars ≠ maintenance
- **No lockfile diff review on PR**. The actual shipped versions live there

## See also

- `scanning-security` — orchestrates this within the broader scan gate
- `responding-to-supply-chain-compromise` — full IOC + rotation flow when a known-bad package is found
- `CLAUDE.md` § Safety floor, item 2 (locked and upper-bounded dependencies)
