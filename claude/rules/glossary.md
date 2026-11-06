# Glossary

Always-on. Single source of truth for cross-cutting terms; per-skill terminology stays inside each skill.

## Tenancy mode (declare per project)

Every project declares one of these in its `CLAUDE.md`. THIS is the canonical definition. Most tenant-scoping language elsewhere in these rules is CONDITIONAL on the declared mode.

| Mode | When to pick | Implications |
|---|---|---|
| `multi-tenant` | B2B SaaS, multiple customer orgs share one deployment | `tenant_id` / `org_id` scoping NON-NEGOTIABLE on every data-touching endpoint and table. BOLA checks, cross-tenant returns 404 not 403. Apply `isolating-multi-tenant-llm` skill |
| `single-tenant` | Internal tool, one-customer build, multi-user app for one org | User-level ownership checks NON-NEGOTIABLE. NO `tenant_id` column — BOLA becomes ownership-check (object.owner_id == user.id). Auth + RBAC still required |
| `single-user` | Personal tool, research code, single-user CLI, library | No scoping rules; auth itself OPTIONAL. Input validation, SSRF, security headers, secrets lifecycle, supply-chain rules still apply |

Default: NONE — declare explicitly, never assume `multi-tenant`; check the declared mode before applying any scoping rule.

## Tenant identifier (synonyms) — only when `tenancy_mode = multi-tenant`

`tenant_id` (generic; preferred when authoring portable skills) ≡ `org_id` (what the kit's projects use in code) ≡ `workspace_id` / `account_id` / `merchant_id` (domain-specific examples). Same thing: derived from authenticated identity at session start, never from user input or LLM args. Canonical definition in `isolating-multi-tenant-llm`. `single-tenant` → `owner_id` / `user_id`, no tenant column. `single-user` → scoping language does not apply.

## Concept-first / WYSIWID architecture

- **concept** — independent module under `src/concepts/<name>/` with its own models, service, schemas, public interface. Concepts NEVER import each other's internals — public interfaces or syncs only
- **sync** — module under `src/syncs/` orchestrating cross-concept flow: trigger → condition → effect

## OWASP acronyms

- **BOLA** (API1) — Broken Object-Level Authorization: cross-tenant access via guessable IDs
- **BOPLA** (API3) — Broken Object Property-Level Authorization: mass assignment + over-disclosure
- **BFLA** (API5) — Broken Function-Level Authorization: low-priv user invokes admin endpoint
- **SSRF** (API7) — Server-Side Request Forgery: server fetches attacker-supplied URL
- **LLM01..LLM10** — OWASP Top 10 for LLM Apps: 01 prompt injection · 02 insecure output · 03 training-data poisoning · 04 model DoS · 05 supply chain · 06 sensitive info disclosure · 07 insecure plugin design · 08 excessive agency · 09 overreliance · 10 model theft
