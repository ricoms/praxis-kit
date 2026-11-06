---
name: rotating-secrets
description: >-
  Rotate a secret cleanly: issue → propagate → verify → revoke → audit.
  Per-type runbooks (AWS / GCP / DB / JWT / OAuth / TLS). Use on compromise,
  schedule, or vendor breach.
disable-model-invocation: true
allowed-tools: Read Grep
metadata:
  tags:
    - security
    - secrets
    - incident-response
    - operations
---

# Rotating Secrets

Secrets aren't static. Rotation is hygiene; it's also the first move in incident response.

Per-secret-type runbooks (AWS / GCP / LLM provider keys / DB / JWT / OAuth / webhook / TLS / KMS) in [runbooks.md](runbooks.md).

## Who runs it

Prefer rotation the secret store or platform does on its own (managed rotation, cert-manager, automatic KMS key
rotation), configured through the pipeline. Everything below is for a secret that cannot rotate on its own: manual
rotation is the second exception to safety-floor rule 5 in `CONSTITUTION.md`, key management done by hand outside
the pipeline.

- **The secret custodian runs every command.** The role is in `docs/raci.md`; who holds it lives in the team's
  engagement records. The custodian is elevated for the rotation only, with MFA, and the elevation expires on its own.
- **The agent drafts and never runs.** It writes the issue, the commands from [runbooks.md](runbooks.md) filled in
  for this secret, and the checks. It never runs a cloud CLI, and it never generates, reads or prints a secret value:
  a value in a transcript is a leaked value.
- **A scheduled rotation needs its issue approved first.** The issue states the reason, the security impact, the
  consumers and the way back. The architecture decider approves it, and is someone other than the custodian wherever
  the project has a second eligible person. A project with one eligible person records that in `docs/agreements.md`
  as a gap with an owner.
- **A compromised secret is revoked at once.** The custodian revokes first, then opens the issue within a day, and
  the decider approves it afterwards.

These choices align with NIST SP 800-53r5 IA-5, SC-12, AC-5, AC-6(5) and AC-6(9), and with AC-2(2) for temporary
access; PCI DSS v4.0.1 6.5.1, 7.2.2 and 8.4.1, plus 3.6.1 and 3.7.4 for keys protecting stored account data; SOC 2
CC6.1 and CC8.1; and ISO/IEC 27001:2022 Annex A 8.2, 8.15, 8.24 and 8.32. PCI 3.7.6 adds dual control when anyone
handles a cleartext key by hand.

## When to rotate

| Trigger | Urgency |
|---|---|
| Confirmed compromise (key leaked, dep with malware found) | Immediate |
| Suspected compromise (anomalous use, vendor breach affecting your tenant) | Within 24h |
| Employee with access leaves | Within 7 days |
| Vendor reports breach (e.g., a SaaS vendor's secret store was leaked) | Within 7 days |
| Scheduled cadence | 90 days for prod, 30 days for high-risk |

A confirmed or suspected compromise takes the revoke-first path: its issue follows within a day. Every other trigger
takes the scheduled path, with its issue approved before the rotation runs.

## Universal procedure

```
0. Open the rotation issue; for a scheduled rotation, rehearse in staging where the
   secret has a staging counterpart, and wait for the issue's approval
1. Issue NEW secret (do not revoke old yet)
2. Update secret store (Secret Manager / Vault / sealed-secrets)
3. Trigger config refresh / restart of consumers
4. Verify consumers using NEW secret (logs, metrics, health checks)
5. Revoke OLD secret
6. Verify OLD secret no longer accepted
7. Audit logs for any uses of NEW secret you didn't expect
8. Document the rotation in docs/runbooks/rotations.log, linking the issue
```

Steps 1–4 first, **then** revoke at 5. Reverse order = downtime, which a compromise accepts (below).

If responding to compromise, revoke first: steps 5 and 6 come before 1–4, accepting the outage, and step 0 follows within a day. Also: search logs for old-secret use after rotation, search for IOCs (see `responding-to-supply-chain-compromise` if it's a dep CVE).

## Secret store hygiene (independent of rotation)

- Secrets only in Secret Manager / Vault / sealed-secrets — never in env files committed to git, never in TF state
- Audit who has read access — least privilege
- Audit logs on secret access (who fetched what, when)
- TTL on access — credentials issued via short-lived tokens (STS, WIF), not long-lived keys
- Secret scanners on commits (gitleaks pre-commit hook)

## Post-rotation audit

After rotating, sweep:

- Logs: search for the *new* secret being used in unexpected places
- Logs: search for the *old* secret still being used → unrolled consumer or attacker still has it
- Audit trail: who fetched the new secret from the secret store
- Cost: any spike post-rotation?

Document the rotation in `docs/runbooks/rotations.log`:

```
2026-05-01 — Rotated AWS IAM user key in prod (scheduled) by <person>
  - Approval: <issue link>, approved by <decider> (before)
  - Identifier: old AKIA…WXYZ → new AKIA…ABCD (key ids, never the secret)
  - Consumers rolled: api, worker, batch
  - Verification: prod traffic 100% on new key by 14:23 UTC
  - Old secret: disabled 14:25 UTC, deleted 2026-05-02
  - Audit: no anomalies in access logs
```

The template ships `docs/runbooks/rotations.log` with this format in its header.

## Anti-patterns

- **Revoke old before consumers are on new.** Outage
- **No verification step.** Half-rolled consumers fail silently until next deploy
- **Long-lived access keys when WIF / OIDC is available.** Avoid them entirely
- **Same-secret-everywhere.** Per-service / per-env scoped secrets reduce blast radius
- **No rotation cadence.** "Rotate when compromised" alone is insufficient
- **Manual rotation of a secret that could rotate on its own.** Use the platform's managed rotation
- **An agent running the commands.** Puts admin rights and secret values in the agent's context

## See also

- [runbooks.md](runbooks.md) — per-secret-type rotation runbooks (AWS / GCP / LLM keys / DB / JWT / OAuth / webhook / TLS / KMS)
- `responding-to-supply-chain-compromise` — broader runbook when a dep was malicious
- `scanning-security` — secrets-detection scan as preventive
- `auditing-deps` — when a dep CVE may have exposed secrets
- `rules/security/secrets-lifecycle.md` — issue / store / use / rotate / revoke / detect
- `rules/security/secrets-lifecycle.md` § Compromise response
