# OWASP API Security Top 10 (2023) — Quick Checklist

Always-on. Apply to every new/modified API endpoint. Deeper walkthrough with code examples: `skills/reviewing-api-security`.

**Mode-dependent.** Tenant checks (API1, API4 per-tenant rate-limit, cross-tenant 404, invariants 1 + 4) apply only when `tenancy_mode = multi-tenant` (see glossary); `single-tenant` → owner/user scoping; `single-user` → existence checks. All other rules apply in ALL modes.

| ID | Risk | One-line check |
|---|---|---|
| API1 | BOLA | `multi-tenant` → filter by `tenant_id`, cross-tenant 404. `single-tenant` → filter by `owner_id`. `single-user` → existence check |
| API2 | Broken Authentication | OAuth 2.0 / OIDC; short-lived tokens; rate limit on login/reset; MFA available |
| API3 | BOPLA | Explicit DTO with allowlisted fields both directions. No mass assignment, no over-disclosure |
| API4 | Unrestricted Resource Consumption | Pagination + max page size + body size limit + rate limit + cost cap |
| API5 | BFLA | Every endpoint declares required role(s); default-deny; tested per role |
| API6 | Sensitive Business Flows | CAPTCHA / velocity checks / bot detection on signup, reset, refund, voucher redeem |
| API7 | SSRF | URL allowlist OR resolved-IP block on private ranges + IMDS; no redirects to internal IPs |
| API8 | Security Misconfiguration | No debug in prod; security headers; CORS scoped; cookies Secure/HttpOnly/SameSite |
| API9 | Improper Inventory | OpenAPI in repo; no debug routes in prod; deprecated routes removed |
| API10 | Unsafe API Consumption | Outbound responses validated; TLS verify; timeouts; webhook signatures verified |

## Default-deny invariants (NON-NEGOTIABLE; 1 + 4 mode-dependent)

1. **Every data-touching endpoint scopes by the right identifier** — `tenant_id` / `owner_id` / none, per declared mode. Internal endpoints too (SSRF reaches them); so does an endpoint that seeds an LLM/chatbot session with the resource — the model relaying it back is still the data leaving unscoped
2. **Every write endpoint uses an explicit DTO** — Pydantic `model_config = {"extra": "forbid"}`
3. **Every response DTO is an allowlist** — never `**model.dict()` on user-facing endpoints
4. **Cross-scope access returns 404, not 403** — don't disclose existence (N/A in `single-user`)
5. **Stack traces never reach the client** — `debug=False` + custom exception handlers
