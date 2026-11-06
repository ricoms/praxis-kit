# STRIDE Question Primers + Document Template

## Contents

- [Spoofing](#spoofing)
- [Tampering](#tampering)
- [Repudiation](#repudiation)
- [Information disclosure](#information-disclosure)
- [Denial of service](#denial-of-service)
- [Elevation of privilege](#elevation-of-privilege)
- [Document template](#document-template)
- [Example diagram](#example-diagram)

Companion to `SKILL.md`. Use when walking each category.

## Spoofing

- Can a request impersonate another user's session? (JWT replay, session-fixation)
- Can a tool call impersonate a system actor?
- Can an LLM-generated response claim authority it doesn't have?
- Can an upstream caller forge `tenant_id`?

## Tampering

- Can request bodies be modified after auth (TLS broken / MITM)?
- Can persisted data be corrupted (race, missing transaction, missing FK)?
- Can a poisoned doc tamper with retrieval results (LLM04)?

## Repudiation

- If something goes wrong, can we prove who did what?
- Are audit logs append-only? Tamper-evident? Per-tenant slice-able?
- Are timestamps trusted (server-side, not client-supplied)?

## Information disclosure

- Cross-tenant leakage in DB / vector store / cache / logs / errors?
- PII in error responses?
- LLM regurgitating training data?
- Side channels (timing, response size, cache hit/miss)?
- Public storage with sensitive content?

## Denial of service

- Unbounded user input length?
- Unbounded query result set?
- Unbounded LLM tokens / cost per session?
- Unbounded retries?
- No rate limit per tenant / IP / user?
- Queue without backpressure?

## Elevation of privilege

- Tool call args bypassing role check?
- Mass-assignment on update endpoints?
- LLM in admin-mode reachable without admin auth?
- Confused-deputy via webhook?
- Role escalation through forgotten dev / debug endpoint?

## Document template

Threat model goes in `docs/threat-models/<feature-or-system>.md`:

```markdown
# Threat Model: <feature/system>

**Date:** YYYY-MM-DD
**Author:** <name>
**Status:** draft | reviewed | accepted

## Scope
<one paragraph + diagram>

## Assets
- ...

## Actors
- End-user (role X)
- ...

## Trust boundaries
- ...

## Threats

### T-001 — Spoofing: <one-line threat>
- **STRIDE category:** Spoofing
- **Severity:** High
- **Description:** <2-3 sentences>
- **Mitigation:** <what we'll do>
- **Status:** open | mitigated | accepted-risk

### T-002 — Information Disclosure: ...
...

## Out of scope
- <explicit non-goals>

## Compensating controls
- <existing controls that lower risk>

## Review
- Reviewed by: ...
- Date: ...
```

## Example diagram

Text-art is fine:

```
[End-user (any tenant)]
        │ HTTPS, JWT auth
        ▼
[API Gateway] ── trust boundary ──> [App service]
                                        │
                                        │ DB query, scoped by tenant_id
                                        ▼
                                    [Postgres + RLS]
                                        │
                                        │ Embedding query, scoped by tenant_id
                                        ▼
                                    [Vector store]
                                        │
                                        │ HTTPS, API key
                                        ▼
                                    [LLM provider]
```
