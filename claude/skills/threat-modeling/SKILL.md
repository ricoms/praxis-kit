---
name: threat-modeling
description: >-
  Threat-model a feature with STRIDE, as a short doc of assets, trust
  boundaries, threats and mitigations. Use for features touching auth, data,
  tenants, integrations, or production state.
metadata:
  tags:
    - security
    - threat-modeling
    - stride
    - design-review
---

# Threat Modeling

Threat-model **before** implementation, not after. The cost of fixing a security flaw drops 10× when caught at design vs caught at audit.

When to threat model (any of these triggers it):

- New feature touching auth, authz, payments, or PII
- New external integration (third-party API, webhook source, file upload)
- Change to tenant-boundary or `org_id` propagation
- Change to data export / sharing surface
- Change that introduces or modifies a tool exposed to an LLM
- New user-facing role or permission
- Anything storing customer credentials / API keys

When **not** to threat model: pure refactors with no surface change, internal-only debugging utilities, static-content updates.

Question primers per STRIDE category and full document template in [stride-prompts.md](stride-prompts.md).

## Process

Copy this checklist into your response and tick off as you progress:

```
Threat-Model Progress:
- [ ] Step 1: Frame the system (assets, actors, trust boundaries + diagram)
- [ ] Step 2: Walk STRIDE per asset / boundary (6 questions each)
- [ ] Step 3: Score threats (Critical / High / Medium / Low)
- [ ] Step 4: Document in docs/threat-models/<feature>.md
- [ ] Step 5: Schedule review (design + post-implementation)
```

### 1. Frame the system

One paragraph + a simple diagram. Cover **assets** (what's worth protecting), **actors** (users / services / attackers), **trust boundaries** (where auth / authz / sanitization happens).

### 2. Walk STRIDE per asset / boundary

For each major asset and trust boundary, ask the 6 STRIDE questions:

| Letter | Question |
|---|---|
| **S**poofing | Can an attacker pretend to be someone they're not? |
| **T**ampering | Can data be modified (in transit, at rest, in memory)? |
| **R**epudiation | Can an action be denied / not auditable? |
| **I**nformation disclosure | Can private data leak? |
| **D**oS | Can an attacker exhaust resources? |
| **E**levation of privilege | Can a low-privilege actor gain higher privileges? |

For each YES, name the **threat** in one line, then **mitigation** in one line.

Per-category question primers in [stride-prompts.md](stride-prompts.md).

### 3. Score

| Severity | Likelihood × Impact | Action |
|---|---|---|
| Critical | High likelihood, catastrophic impact | Mitigate before shipping |
| High | High either dimension | Mitigate before shipping unless explicit risk-accept with sign-off |
| Medium | Moderate | Mitigate in next sprint; track |
| Low | Low likelihood, contained impact | Acknowledge in doc; monitor |

Score a threat no higher than the impact you can state: if you cannot name the concrete damage, it scores lower than it
feels. DREAD is a more granular alternative. Pick one, stick with it project-wide.

### 4. Document

Threat model goes in `docs/threat-models/<feature-or-system>.md`. Template in [stride-prompts.md](stride-prompts.md).

### 5. Review and re-review

- First review at design phase, before code
- Second review post-implementation, before merge
- Re-review if scope changes, dependencies change, or a new attack class emerges

## Worked example — one threat entry

What a complete threat looks like in `docs/threat-models/<feature>.md`:

```markdown
### T-007 — Information Disclosure: Cross-tenant leakage via vector search

- **STRIDE category:** Information Disclosure
- **Severity:** Critical (any user can see another tenant's documents)
- **Description:** The current RAG implementation queries the shared vector
  collection without a tenant filter. A user from tenant A whose query is
  semantically close to documents in tenant B will retrieve B's content as
  LLM context.
- **Mitigation:** Pre-filter retrieval by `tenant_id` before vector
  similarity ranking. Add an
  assertion at the retrieval boundary that all returned chunks have
  `tenant_id == ctx.tenant_id`; raise `CrossTenantLeakError` otherwise.
- **Test:** `tests/integration/test_rag_isolation.py::test_cross_tenant_returns_empty`
- **Status:** mitigated (PR #234)
- **Owner:** <owner>
```

The `Mitigation` field maps the threat to a specific defense, so an audit can trace each threat to the control that answers it.

## Examples by domain

- **Multi-tenant SaaS feature**: focus on **I** (cross-tenant leak) and **E** (role escalation across tenants)
- **External webhook ingress**: focus on **S** (signature verification), **T** (tampering before signature), **D** (replay / flood)
- **LLM tool-use surface**: focus on **E** (excessive agency), **I** (output leak), **T** (poisoned retrieval)
- **Payment flow**: focus on **R** (audit), **T** (idempotency, exact-once), **S** (3DS / signature)

## Anti-patterns

- **Threat-modeling once at the end.** Catches design flaws too late
- **Listing every possible threat.** Prioritize by likelihood × impact; ignore the unlikely
- **Generic mitigations** ("we use HTTPS"). Map each mitigation to the specific threat
- **No re-review.** Scope drifts; threats change
- **Threat models that nobody reads.** Keep them under 2 pages, link from PRs

## AI/ML systems

For AI/ML features, name threats with **MITRE ATLAS** technique IDs (the ATT&CK-style adversarial-AI taxonomy, grounded in real incidents) alongside STRIDE — a shared vocabulary keeps AI risks from collapsing into a checkbox. Complements Google SAIF. App-layer threats still map to OWASP LLM Top 10; ATLAS additionally covers the **model-level TTPs** that lens misses — data poisoning, evasion, model extraction/theft. For an agent's tool and data graph, also check every path that joins private data, untrusted content and egress. <https://atlas.mitre.org/>

## See also

- [stride-prompts.md](stride-prompts.md) — per-category question primers + document template
- `reviewing-api-security` — OWASP API Top 10 checklist (some STRIDE threats map directly)
- `scanning-security` — runtime scan gate, complementary to design-time threat model
- `isolating-multi-tenant-llm` — tenant isolation for LLM features
- `rules/security/owasp-api-top-10.md`
