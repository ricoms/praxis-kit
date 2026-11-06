---
name: scanning-security
description: >-
  Run structured security scan gate. Use when the user says "security scan",
  after major implementation phases, before merging feature branches, or when
  auditing a project's security posture.
allowed-tools: Bash(just *) Bash(gitleaks *) Bash(git *) Bash(grep *) Read Grep Glob Agent
---

# Security scan gate

This skill is the scan that the stage table in `CONSTITUTION.md` §4 asks for: "security scan of code, secrets and
infrastructure", per phase in `build` and weekly from `run`. It works for any stack. The project's tools run through its own
`just security-scan` recipe; this skill decides what counts as a finding and how sure we are of it.

Two modes:

- **Guidance** (the default): answer a question about one change or one area, read-only, and write nothing.
- **Full scan**, when asked or at the stage's cadence: every step below, ending in a report.

## Safety rules

- Never touch a live endpoint, a shared environment or real user data. Use local code, local services and dummy
  principals only.
- Never run the target's code outside a sandbox that limits network, files and time. Without one, keep the lead as
  *needs validation* and name the missing capability.
- The scan describes fixes; it does not change the code under review.

## Full scan

1. **State the scope.** List what this scan covers (services, entry points, data stores) and what it does not. An area
   that was not reviewed is reported as out of scope, never as covered.
2. **Read the declared tenancy mode** in the project's `CLAUDE.md` (at the root or in `.claude/`). If it is missing,
   ask before going on. The mode decides step 4.
3. **Run the project's automated checks:** `just security-scan`. It runs the secrets scan (`just secrets`), then the
   project's audits (`just audit`). If the project has not written `audit` yet, record that as a gap, not a pass, and
   make sure the secrets scan ran; if it did not, run `gitleaks detect --source . --no-banner -v` directly.
4. **Audit authorization on every entry point.** Scoping follows the tenancy mode (`rules/glossary.md`):
   - `multi-tenant`: every data access is bound to the tenant from the authenticated identity, never from the
     request. A tenant field on a record is not isolation; find the query, key or policy that enforces it on every
     read and write path. Cross-tenant access returns 404. See [data-isolation.md](data-isolation.md).
   - `single-tenant`: every object access checks ownership against the authenticated user.
   - `single-user`: no scoping, and authentication is optional; check that the entry points are not exposed beyond the
     one user.

   In the first two modes, every entry point also requires authentication or states why it is public.
5. **Check exposure:** listening ports and published services, debug endpoints, CORS, and infrastructure files that
   open access to everyone. Run the project's infrastructure scanner if it has one.
6. **Verify each candidate independently.** For every candidate finding, start a fresh agent that did not find it.
   Give it the claim and the cited locations, tell it to disprove the claim, and have it reread the source and repeat
   any decisive check it can run safely. Never pass it another verifier's conclusion. The agent that found an issue
   never confirms it.
7. **Write the report** (below).

## Verdicts and severity

Each finding gets exactly one verdict:

- **confirmed**: the verifier established the complete path from entry point to effect, and the result it observed
  or read in source. Only confirmed findings get a severity.
- **needs validation**: a specific, source-grounded hypothesis blocked by one missing fact (a deployment setting, a
  provider policy, a runtime behaviour). Name the fact and a safe way to establish it. It has no severity, and it is
  never a parking place for a speculative idea.
- **rejected**: disproved by source, a visible control, missing impact or an impossible precondition. Kept in the
  report so a later scan does not repeat the claim without new evidence.

Severity never exceeds the impact shown:

- **critical**: an unauthenticated actor gains code execution, full data-store access, or takeover of arbitrary
  accounts.
- **high**: an actor fully defeats an explicit control with real consequences: authentication bypass, cross-tenant
  read or write, stored script execution affecting other users, authenticated code execution, or an unauthenticated
  remote stop of a shared service.
- **medium**: a real boundary violation with limited reach, uncommon preconditions, or effects on a narrow set of
  resources.
- **low**: disclosure of non-secret internals, or an effect that takes sustained effort for little gain.

The high/medium test: does the result fully defeat a control, or only weaken it? If you cannot state the concrete
damage, the severity is lower than it feels. A missing extra layer of defence is a hardening note, not a finding.

Confirmed critical and high findings block the merge, and so does a failing `just security-scan` (`CONSTITUTION.md`
§2, rule 3: nothing merges while checks are red). A secret the scan finds is revoked first and investigated after
(§2, rule 1).

## Report

Write `docs/security-scans/YYYY-MM-DD-scan.md` with: the scope (covered and out of scope), the tenancy mode, the output
of `just security-scan`, the confirmed findings, the leads that need validation in their own section, hardening notes,
and the fingerprints of rejected claims with their reasons. Rejected claims are not findings and are not counted as
findings. Each record has the same shape, so a threat model or a PR review can reuse it:

```markdown
### <title>
- **Fingerprint**: <stable id: rule or class + file + symbol, so a re-scan recognises a known finding>
- **Verdict**: confirmed | needs validation | rejected
- **Trace**: <entry point> → … → <effect>, each step `path/to/file:line`
- **Severity**: critical | high | medium | low (confirmed only)
- **Missing fact and how to establish it**: <needs validation only>
- **Reason**: <rejected only>
- **Fix**: <the narrowest change that enforces the invariant, and its regression test>
- **Status**: open | fixed
```

## See also

- `threat-modeling`: design-time threats; its scoring follows the same rule that severity never exceeds the impact
  shown
- `reviewing-api-security`, `rules/security/owasp-api-top-10.md`: the API checklist
- `auditing-deps`, `scanning-iac`: dependency and infrastructure detail
- `verifying-the-path`: a check counts once it has been seen failing with the defect present

The verdicts, the severity scale, independent verification and the safety rules are adapted from Cloudflare's
[security-audit skill](https://github.com/cloudflare/security-audit-skill) (MIT licence, notice in
[LICENSE-cloudflare.txt](LICENSE-cloudflare.txt)).
