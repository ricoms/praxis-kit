# OWASP API Top 10 Checklist with Code

## Contents

- [API1 — Broken Object-Level Authorization (BOLA)](#api1-broken-object-level-authorization-bola)
- [API2 — Broken Authentication](#api2-broken-authentication)
- [API3 — Broken Object Property Level Authorization (BOPLA)](#api3-broken-object-property-level-authorization-bopla)
- [API4 — Unrestricted Resource Consumption](#api4-unrestricted-resource-consumption)
- [API5 — Broken Function-Level Authorization (BFLA)](#api5-broken-function-level-authorization-bfla)
- [API6 — Unrestricted Access to Sensitive Business Flows](#api6-unrestricted-access-to-sensitive-business-flows)
- [API7 — Server-Side Request Forgery (SSRF)](#api7-server-side-request-forgery-ssrf)
- [API8 — Security Misconfiguration](#api8-security-misconfiguration)
- [API9 — Improper Inventory Management](#api9-improper-inventory-management)
- [API10 — Unsafe Consumption of APIs](#api10-unsafe-consumption-of-apis)

Companion to `SKILL.md`. Each category: threat → check → code pattern.

## API1 — Broken Object-Level Authorization (BOLA)

**Threat:** an authenticated user can access another user's / tenant's object by guessing or learning IDs.

Check every endpoint that takes an object ID (`GET /resources/:id`, `PUT /resources/:id`, etc.):

```python
async def get_resource(resource_id: UUID, ctx: SessionContext) -> Resource:
    resource = await db.fetch_one(
        "SELECT * FROM resources WHERE id = :id AND tenant_id = :tenant_id",
        {"id": resource_id, "tenant_id": ctx.tenant_id},  # <-- THIS LINE
    )
    if resource is None:
        raise NotFoundError()  # never disclose existence in another tenant
    return Resource(**resource)
```

Rules:

- Filter by `tenant_id` (or owning user) on **every** read/write
- Postgres RLS as belt-and-suspenders
- Return 404 not 403 for cross-tenant requests (don't disclose existence)

Test: integration test where user A queries user B's resource ID; assert 404.

## API2 — Broken Authentication

**Threat:** auth tokens forged, replayed, or stolen.

Checklist:

- [ ] OAuth 2.0 / OIDC for delegated auth (don't roll your own)
- [ ] MFA available (and enforced for high-privilege roles)
- [ ] JWT verified on every request (signature + exp + iss + aud)
- [ ] Tokens short-lived (≤15 min for access; refresh token rotation)
- [ ] Refresh tokens revocable; refresh rotation detects theft
- [ ] No long-lived API keys for end-users (use OAuth)
- [ ] Service-to-service: mTLS or short-lived bearer (e.g., WIF / OIDC)
- [ ] Rate limit on /login, /password-reset, /token endpoints
- [ ] Lockout policy (after N failed attempts)
- [ ] Password rules: length over complexity (NIST SP 800-63B); checked against breach corpora

## API3 — Broken Object Property Level Authorization (BOPLA)

**Threat:** mass assignment / over-disclosure. The endpoint accepts or returns properties the user shouldn't be allowed to modify or see.

Two failure modes:

**(a) Mass assignment** — user posts `{"name": "...", "is_admin": true}` and the framework happily binds `is_admin`.

```python
# BAD — accepts all fields
@router.put("/users/{user_id}")
async def update_user(user_id: UUID, body: dict, ctx: SessionContext):
    return await users.update(user_id, body)

# GOOD — explicit DTO with only updatable fields
class UserUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str | None = None
    locale: str | None = None
    # is_admin deliberately not here

@router.put("/users/{user_id}")
async def update_user(user_id: UUID, body: UserUpdate, ctx: SessionContext):
    return await users.update(user_id, body.model_dump(exclude_unset=True))
```

**(b) Over-disclosure** — the response includes fields the user shouldn't see (other users' emails, internal IDs, debug fields).

```python
# BAD — exposes internal state
class UserResponse(BaseModel):
    id: UUID
    email: str
    password_hash: str  # !!
    api_key: str        # !!

# GOOD — explicit allowlist of public fields
class UserPublicResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None
```

Use **separate read-DTOs and write-DTOs**, both explicit allowlists.

## API4 — Unrestricted Resource Consumption

**Threat:** attacker exhausts CPU / memory / DB / cost / quota.

Checklist:

- [ ] Pagination on all list endpoints (cursor-based per CLAUDE.md)
- [ ] Max page size enforced (e.g., 100; reject larger)
- [ ] Request body size limit (e.g., 1 MB default, 10 MB for uploads)
- [ ] Rate limits per user / per IP / per tenant
- [ ] Per-tenant cost / quota caps for expensive endpoints (LLM calls, exports, reports)
- [ ] Timeouts on all external calls
- [ ] Connection pool bounded
- [ ] Worker queue bounded (backpressure, not unbounded enqueue)

## API5 — Broken Function-Level Authorization (BFLA)

**Threat:** low-privilege user invokes admin-only endpoint.

Checklist:

- [ ] Every endpoint declares required role(s) explicitly
- [ ] Default-deny: missing declaration = no access
- [ ] Tested per role (one test per role × per endpoint at minimum for admin endpoints)
- [ ] No `if user.is_staff:` scattered through handlers — centralized policy

```python
# Pattern: route-level policy decorator
@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: UUID): ...
```

## API6 — Unrestricted Access to Sensitive Business Flows

**Threat:** automation abuses high-value flows (signup, password reset, refund, voucher redemption, large-discount purchase).

Defenses:

- CAPTCHA on high-value flows (signup, password reset)
- Rate limits per user / device / IP
- Velocity checks (e.g., "no more than 3 password resets per email per hour")
- Bot detection (User-Agent analysis, JavaScript challenge, proof-of-work)
- For commerce flows: require auth even for "browse"-style endpoints when they reveal pricing rules attackers care about

## API7 — Server-Side Request Forgery (SSRF)

**Threat:** API takes a URL and fetches it; attacker uses you to probe internal network or cloud metadata service (`169.254.169.254`).

Checklist:

- [ ] If your API takes URLs, restrict to an allowlist of domains
- [ ] If allowlist isn't possible, validate after DNS resolution (check resolved IP isn't in private ranges, link-local, or metadata IP)
- [ ] Disable HTTP redirects to internal IPs
- [ ] Block IMDS endpoints at the network layer (IMDSv2 + token requirement)
- [ ] Test with `127.0.0.1`, `localhost`, `[::1]`, `169.254.169.254`, `metadata.google.internal`, internal CIDRs (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)

## API8 — Security Misconfiguration

Checklist:

- [ ] No debug mode in prod (FastAPI `--reload`, Vue dev tools, debug endpoints)
- [ ] Security headers: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`
- [ ] CORS restricted (no `*` for `Access-Control-Allow-Origin` on auth-bearing endpoints)
- [ ] HTTP error responses don't leak stack traces, internal paths, framework versions
- [ ] HTTP 405 / 415 on wrong method / content-type (not 500)
- [ ] Cookies: `Secure`, `HttpOnly`, `SameSite=Lax|Strict`, scoped to path
- [ ] No "Server: nginx/x.y.z" header revealing exact versions

## API9 — Improper Inventory Management

**Threat:** old / undocumented / forgotten endpoints (debug routes, deprecated v1, internal-only) reachable from prod.

Checklist:

- [ ] OpenAPI spec generated and reviewed; deviations from spec audited
- [ ] /v1 → /v2 → /v3 migration completed; deprecated routes removed
- [ ] No /debug, /admin/_internal, /test routes in prod
- [ ] Staging endpoints not reachable from prod DNS
- [ ] Inventory of public-facing hosts (Subdomain takeover prevention — DNS records pointing at decommissioned services)

## API10 — Unsafe Consumption of APIs

**Threat:** your code calls a third-party API and trusts the response without validation.

Checklist:

- [ ] All third-party API responses validated against expected schema (Pydantic at the boundary)
- [ ] Outbound calls use TLS verification (no `verify=False`)
- [ ] Timeouts on outbound calls
- [ ] Circuit breaker on flaky deps
- [ ] No outbound calls to user-supplied URLs without SSRF defense (see API7)
- [ ] Webhook signature verification on inbound (Stripe, Twilio, GitHub etc.)
- [ ] No deserialization of untrusted data into objects (`pickle`, `yaml.load`, etc.)
