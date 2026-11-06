---
name: responding-to-supply-chain-compromise
description: >-
  Incident response for a malicious dependency (OWASP LLM05): contain, scope,
  rotate secrets, hunt IOCs, eradicate, post-mortem. Use on a typosquat or
  hijacked maintainer, not a routine CVE bump.
metadata:
  tags:
    - security
    - supply-chain
    - incident-response
    - owasp-llm-top-10
---

# Responding to Supply-Chain Compromise

A malicious dependency is worse than a leaked secret: the package ran with **your code's privileges** — env vars, CI tokens, postinstall scripts, network egress. Assume exposure and hunt; don't just bump the version.

This is the orchestration runbook between detection and rotation:

`auditing-deps` (detects: "is this package bad?") → **this runbook** (responds) → `rotating-secrets` (rotates what was exposed).

## When to invoke

A dependency (direct or transitive) is found **actively malicious or compromised**:

- typosquat / dependency-confusion package pulled in
- a maintainer account hijacked and a backdoor published
- a CVE with evidence of active exploitation in a version you shipped
- a lockfile or build shows a known-bad version

NOT for a routine CVE with a clean upgrade path — that's `auditing-deps` + a normal bump.

## Severity first (30 seconds)

Did the bad version run in **CI** or **production**, or only on a dev machine?

- **CI / prod → full incident.** CI secrets (WIF/OIDC tokens, registry creds) and prod env are presumed exposed. Run every phase.
- **Dev-only, never built/deployed → contain + eradicate**, lighter rotation (local creds only).

## Phase 1 — Contain

- Pin or remove the bad package; **freeze deploys** for affected services.
- Find every instance: grep all lockfiles across every repo/service for the bad version (`uv.lock`, `pnpm-lock.yaml`, `Cargo.lock`). Blast radius is rarely one repo.
- Do **not** re-resolve (`uv sync`, `pnpm install`) until pinned — you'll re-pull it.

## Phase 2 — Scope access

What could the package reach where it ran?

- Env / `.env`, CI secrets, WIF/OIDC tokens, cloud creds, registry/publish tokens, signing keys.
- Did it have a `postinstall` / build hook (arbitrary code at install time)? Did it run in the prod process (runtime access)?
- Was network egress allowed from CI/prod? (the exfil path)

List the credentials and data in reach — that list drives Phase 3.

## Phase 3 — Rotate (assume-exposed)

Every credential from Phase 2 → **revoke FIRST, reissue after**, per `rules/security/secrets-lifecycle.md`. Hand off to `rotating-secrets`.

- WIF/OIDC: rotate provider trust if CI was hit; SA keys → delete + reissue (prefer WIF over keys).
- Registry/publish tokens; signing keys if the build pipeline was touched.
- Order: revoke → reissue → roll consumers → search logs for **post-revocation use** (use-after-revoke = something was missed).

## Phase 4 — Hunt IOCs

- Search logs + egress for the package's known C2 / exfil indicators (the advisory usually lists them).
- Look for: postinstall execution, unexpected outbound connections, new/modified files, `.npmrc` / `.pypirc` / lockfile tampering, persistence (cron, startup hooks), modified CI config.
- Check build artifacts for tampering — diff against a known-clean rebuild.

## Phase 5 — Eradicate & rebuild

- Replace with a vetted version/alternative — apply `auditing-deps`' maintenance rubric **before** adopting the replacement.
- **Purge caches** that may carry the bad artifact: package caches (`uv cache clean`, `pnpm store prune`) and Docker layers (rebuild `--no-cache`; the kernel requires immutable digest refs — re-pin the new digest).
- Rebuild from clean state. Republish any artifact shipped while compromised (and notify consumers if you publish packages).

## Phase 6 — Document + post-mortem

- Incident doc `docs/runbooks/incidents/YYYY-MM-DD-<id>.md` (per `secrets-lifecycle.md`): timeline, what the package could access, what was rotated, the leak vector, IOCs found.
- File / subscribe to the upstream advisory; notify downstream consumers.
- Post-mortem: how did an un-vetted or known-bad version get in? Tighten the gate (upper-bound pins, lockfile review, `auditing-deps` cadence). Supply-chain rules are **NON-NEGOTIABLE** per the kernel.

## Anti-patterns

- **Bumping the version and moving on.** The code already ran; rotate + hunt regardless.
- **Rotating only the obvious key.** Phase 2 enumerates everything in reach — rotate all of it.
- **Trusting a rebuild on a poisoned cache.** Purge caches/layers first, or you rebuild the compromise.
- **Scoping to one repo.** Grep every lockfile; transitive deps spread silently.

## See also

- `auditing-deps` — detection + the maintenance rubric for the replacement
- `rotating-secrets` — the rotation mechanics Phase 3 hands off to
- `rules/security/secrets-lifecycle.md` — revoke-first flow + incident-doc convention
- OWASP LLM05 (supply chain) / general SCA
