---
name: isolating-multi-tenant-llm
description: >-
  Prevent cross-tenant data leakage in multi-tenant LLM apps. Propagate
  tenant_id from auth through queries / tools / RAG / audit. Use when
  designing or auditing any multi-tenant LLM endpoint.
metadata:
  tags:
    - llm-security
    - multi-tenancy
    - isolation
    - owasp-llm-top-10
---

# Isolating Multi-Tenant LLM

Multi-tenant LLM apps fail in two distinct ways: cross-tenant leakage in **retrieval** (vector index returns another tenant's docs) and cross-tenant leakage in **tools** (LLM-generated tool args reach into another tenant's data). Both are catastrophic. Both are preventable with one rule:

> The tenant identifier comes from the **session context**, derived from authenticated identity. It never comes from the user's text, the LLM's output, or a tool's args.

Throughout: `tenant_id` is the generic name. In the kit's projects it's `org_id`; some apps use `workspace_id`, `account_id`, or domain-specific names like `merchant_id`. The pattern is identical.

## Quick start

Three rules:

1. `tenant_id` comes from the **authenticated session** (JWT claim), never from user input or LLM args
2. Every query / tool call / RAG retrieval / audit log carries `tenant_id`
3. Pre-filter by `tenant_id` **before** vector search, never after

```python
ctx = SessionContext(tenant_id=jwt.claims["tenant_id"], ...)  # from auth, ALWAYS
rows = await db.fetch_all(
    "SELECT * FROM resources WHERE tenant_id = :t AND id = :i",
    {"t": ctx.tenant_id, "i": resource_id},
)
```

Postgres RLS as belt-and-suspenders. 5 layers + cross-tenant detection + assertions below.

## The propagation rule

```python
@dataclass(frozen=True)
class SessionContext:
    user_id: UUID
    tenant_id: UUID    # set once, at session start, from JWT/auth
    role: Role
    mode: SessionMode
    locale: str

# At session start (after auth):
ctx = SessionContext(
    user_id=jwt.sub,
    tenant_id=jwt.claims["tenant_id"],   # from auth, NEVER from request body
    role=Role(jwt.claims["role"]),
    mode=SessionMode.READ,
    locale="en",
)
```

Every downstream call takes `ctx` as a parameter. Every layer enforces `tenant_id` against `ctx.tenant_id`.

## Layer 1 — Database queries

Every query filters by `tenant_id`:

```python
async def search_records(query: str, ctx: SessionContext, limit: int = 10) -> list[Record]:
    rows = await db.fetch_all(
        "SELECT * FROM records WHERE tenant_id = :tenant_id AND title ILIKE :q LIMIT :n",
        {"tenant_id": ctx.tenant_id, "q": f"%{query}%", "n": limit},
    )
    return [Record(**r) for r in rows]
```

Belt-and-suspenders: enable Postgres Row-Level Security (RLS):

```sql
ALTER TABLE records ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON records
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

Set `app.current_tenant_id` per request from `ctx.tenant_id`. Even if a developer forgets the WHERE clause, RLS catches it.

## Layer 2 — Tool calls

Tool implementations receive `ctx`, ignore any `tenant_id` in args:

```python
async def get_resource(args: dict, ctx: SessionContext) -> ToolResult:
    # NEVER trust args["tenant_id"] — overwrite with context
    resource = await db.fetch_one(
        "SELECT * FROM resources WHERE id = :id AND tenant_id = :tenant_id",
        {"id": args["resource_id"], "tenant_id": ctx.tenant_id},
    )
    if resource is None:
        return ToolResult.error("not_found")  # never disclose existence in another tenant
    return ToolResult.ok(resource)
```

If `args` contains `tenant_id` (perhaps because the LLM hallucinated it), **log a security event** — that's a model trying to scope-escalate.

## Layer 3 — RAG / vector retrieval

Pre-filter by tenant **before** vector search, not after:

```python
results = await db.fetch_all(
    """
    SELECT id, content, embedding <=> :query_embedding AS distance
    FROM documents
    WHERE tenant_id = :tenant_id
    ORDER BY distance
    LIMIT :k
    """,
    {"query_embedding": query_emb, "tenant_id": ctx.tenant_id, "k": 5},
)
```

Post-filtering is wrong — cheaper but lets the index see other tenants' vectors and risks return-then-discard bugs. For external vector DBs (Pinecone, Qdrant, Weaviate), use namespace-per-tenant or filter on metadata at query time.

**Never use a single shared collection without filter.** That's the canonical multi-tenant RAG vulnerability.

## Layer 4 — Audit logs

Every event includes `tenant_id`:

```json
{
  "event_type": "tool_call",
  "session_id": "...",
  "tenant_id": "abc-123",
  "user_id": "...",
  "tool": "get_resource",
  ...
}
```

Logs queryable per-tenant: a security-incident response can pull *one tenant's* events without sifting through everyone.

## Layer 5 — Prompt context

What goes into the model's context window? If it's the user's data, fine. If it's *retrieved* data, ensure:

- Retrieval already filtered by `ctx.tenant_id`
- Retrieved chunks are wrapped/marked as data, not instructions (the two-channel pattern: retrieved text is data, never instructions)
- No tenant-identifying metadata leaks unnecessarily (e.g., don't include other tenants' anonymized examples in few-shot)

## Cross-tenant detection

When something *does* slip through, detect it:

- Query log: rows returned with `tenant_id != ctx.tenant_id` → critical security event, halt session
- Tool result: returned object's `tenant_id` differs from `ctx.tenant_id` → same
- LLM output: the model mentions a tenant name / ID that isn't in the user's session — usually a sign retrieval misfired

```python
def assert_tenant(obj: Any, ctx: SessionContext) -> None:
    obj_tenant = getattr(obj, "tenant_id", None)
    if obj_tenant is not None and obj_tenant != ctx.tenant_id:
        log_security_event(
            "cross_tenant_leak", expected=ctx.tenant_id, actual=obj_tenant, kind=type(obj).__name__,
        )
        raise CrossTenantLeakError()
```

Run this assertion at the boundary of every concept service that returns objects.

## Examples by domain

- **Customer support across tenants**: each tenant's tickets / KB / users isolated; one agent shared across tenants but `ctx.tenant_id` enforces visibility
- **Dev / coding agent over private repos**: each repo (or org) is a tenant; agent must not surface other repos' code in completion or search
- **RAG over docs (multi-team)**: each team is a tenant; documents indexed with `tenant_id`; queries pre-filtered
- **MCP server**: the calling agent passes a tenant context via auth; the MCP server enforces — never trust the agent to scope itself

## Anti-patterns

- **Trusting `tenant_id` from request body / query string / LLM tool args.** Always derive from auth
- **Single shared vector index without tenant filter.** Build per-tenant collections or use metadata filters
- **Concept-internal helpers that don't take `ctx`.** They will eventually get called from a different tenant's code path
- **Logging without `tenant_id`.** Forensics needs to slice by tenant
- **Allowing the LLM to "see all tenants" via a meta-tool** (admin-only). If you must, isolate that path entirely — different agent, different model, separate auth

## See also

- `rules/glossary.md` § Tenant identifier (uses `org_id` as the concrete name)
