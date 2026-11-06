# Invariant rules

Team practices Article X. A pattern, not template code: rules are written per project and language.

## What they are for

An invariant rule turns one decision the project cannot afford to get wrong into a static-analysis check: the
breach vector it exists to close (a query not scoped to its tenant, a customer id taken from a request parameter),
or an architecture boundary an ADR set (a module importing another's internals). One rule per invariant, each
citing its ADR in the message.

They are not a general linter. A rule earns its place when the invariant is decided, a violation would be serious,
and the violation has a recognisable shape in code.

## Shape

Semgrep, one rule per file with a fixture file of the same name. Fixtures mark what must match and what must not:

```yaml
# rules/unscoped-order-query.yaml
rules:
  - id: unscoped-order-query
    languages: [python]
    severity: ERROR
    message: Order queries must be scoped to the tenant (ADR 0004). Use scoped_orders(tenant_id).
    pattern: Order.objects.filter(...)
```

```python
# rules/unscoped-order-query.py
# ruleid: unscoped-order-query
Order.objects.filter(id=order_id)

# ok: unscoped-order-query
scoped_orders(tenant_id).filter(id=order_id)
```

CI runs `semgrep --test rules/` first, then the rules on the code. A rule is never weakened and a fixture never
deleted to make CI pass, and no inline `# nosemgrep` is added to pass it (`CONSTITUTION.md` §3). A genuine false
positive is fixed in its own PR that narrows the rule and adds a fixture for the case. Rules are governance files,
so that PR is one-way and needs an accepted ADR.

## Effort cap

A pattern rule can always be spelled around, and an agent will happily chase every syntax variant one commit at a
time. Each rule gets **two rounds** of widening after it first ships. After that, list the forms it does not catch in
the rule's message or a comment, and leave them to review and tests.

The better fix is structural: make the unsafe form unavailable (a default scope, a repository that requires the
tenant, a module that does not export its internals). Then the rule only has to catch the escape hatch.

## Evidence

One rebuild ([evidence](../evidence.md#repository-and-checks)): rules with fixtures, written by several
people, blocked real findings. A long run of consecutive commits went into closing syntax variants of the same
rules, and reviewers still found forms they missed — which is where the cap comes from.
