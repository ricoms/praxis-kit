---
name: reviewing-api-security
description: >-
  Walk an API surface against the OWASP API Top 10 (BOLA, BOPLA, BFLA, SSRF
  and the rest). Use before merging API changes, during release review, or
  when auditing an existing API surface.
metadata:
  tags:
    - security
    - api-security
    - owasp-api-top-10
---

# Reviewing API Security

OWASP API Top 10 (2023) walk-through. Apply before any API surface change merges, and on a periodic full-surface audit.

Reference rules: `~/.claude/rules/security/owasp-api-top-10.md`. Full per-API checklist with code examples: [api-checklist.md](api-checklist.md).

## Step 0 — confirm tenancy mode

Before walking the checklist, read the project's `CLAUDE.md` for the declared `tenancy_mode` (per global CLAUDE.md `## Tenancy`). Apply the rules below in the mode-appropriate form:

- `multi-tenant` → BOLA = filter by `tenant_id`; cross-tenant returns 404; per-tenant rate-limits
- `single-tenant` → BOLA = ownership check (`object.owner_id == current_user.id`); cross-owner returns 404; per-user rate-limits
- `single-user` → BOLA degenerates to "object exists and is visible to the user"; no cross-scope concept; rate-limits per IP or session

Non-tenant rules (API2, API3, API5, API6, API7, API8, API9, API10) apply identically in all modes. If `CLAUDE.md` has no declared mode, STOP the review and ask the user — do not pick for them.

## Review process

For a PR touching API surface:

1. Pull the diff for `api/`, `routers/`, `controllers/`, etc.
2. For each new/modified endpoint, walk API1–API10 — most won't apply per change, but the BOLA/BOPLA/BFLA trio almost always applies (in mode-appropriate form)
3. Check the integration tests — does the test suite cover cross-scope access (cross-tenant or cross-owner per mode) for the new endpoint? Skip this step for `single-user`
4. Sign off on the PR with a comment listing which API1–API10 you considered

For a periodic audit:

1. Generate the full OpenAPI spec (`fastapi-cli openapi-export`)
2. Walk every endpoint
3. Output: `docs/audits/api-security-YYYY-MM.md` with findings per category

## Default-deny invariants

Non-negotiable (per `rules/security/owasp-api-top-10.md`). Items 1 + 4 are mode-dependent; 2, 3, 5 apply in all modes.

1. Every endpoint that touches data scopes by the right identifier (`tenant_id` / `owner_id` / none per mode). No exceptions where scoping applies
2. Every write endpoint uses an explicit DTO with `extra="forbid"`
3. Every response DTO is an allowlist
4. 404 (not 403) on cross-scope access — applies in `multi-tenant` and `single-tenant`; N/A in `single-user`
5. Stack traces never reach the client

## Severity rubric

| OWASP ID | Applies when | Block merge if violated? |
|---|---|---|
| API1 BOLA | Any endpoint with object ID in path. Form varies by tenancy mode | Yes (mode-appropriate form) |
| API2 broken auth | Any auth-bearing endpoint | Yes |
| API3 BOPLA | Any write endpoint | Yes |
| API4 unrestricted resources | Any list / search / upload | Yes |
| API5 BFLA | Any endpoint with role gates | Yes |
| API6 sensitive flows | Signup, reset, refund, payment | Yes |
| API7 SSRF | Any endpoint accepting URLs | Yes |
| API8 misconfig | All | Warning unless production |
| API9 inventory | Periodic audit | Warning |
| API10 unsafe API consumption | Any outbound caller | Yes |

## See also

- [api-checklist.md](api-checklist.md) — full walkthrough with code examples
- `threat-modeling` — STRIDE for design-phase, complementary to this checklist
- `scanning-security` — runtime scan gate
- `isolating-multi-tenant-llm` — same BOLA/BFLA principles, applied to LLM tool surfaces
- `rules/security/owasp-api-top-10.md`
- OWASP API Security Top 10 (2023): <https://owasp.org/www-project-api-security/>
