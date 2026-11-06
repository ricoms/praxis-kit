# Data isolation

Read this reference during step 4 of the scan when the project holds data for more than one tenant or owner. It
follows one record through every copy and every change of state. Adapted from Cloudflare's
[security-audit skill](https://github.com/cloudflare/security-audit-skill), `DATA-ISOLATION-AND-LIFECYCLE.md`
(MIT licence, notice in [LICENSE-cloudflare.txt](LICENSE-cloudflare.txt)).

## The discipline

- A tenant or owner field on a record is not isolation. Find the query, key, path, policy or row-level control that
  enforces it, for each read and each write path.
- Follow derived copies. Data that is safe in its primary store can leak through search, caches, analytics, exports,
  previews, logs, replicas and backups, which often have different access rules and retention.
- Deletion and revocation are promises about every copy: current, historical, cached, indexed, exported, restored
  and queued.
- A privacy or retention preference is not a vulnerability by itself. A finding needs an explicit access boundary or
  deletion promise, and an unauthorized reader or later operation that breaks it.

## Where isolation breaks

| Class | What to look for |
|---|---|
| Missing tenant or owner binding | A read, update, delete, list, count or bulk query that finds an object without binding it to the authenticated tenant, or takes that identity from the request body. Compare direct lookups with nested, background, admin, import and legacy paths |
| Key and namespace collision | Cache keys, object paths, unique constraints, search ids, temporary files or deduplication keys that leave out the tenant or environment |
| Policy and query disagree | Row-level policy, default scopes, authorization filters and raw or service clients applying different predicates; check joins, aggregates, views and paths where the context is missing |
| Signed links overreach | Object keys, attachment ids, shared links or signed URLs that allow more than the issuing principal could, or stay valid after access changes |
| Derived copies drift | A search index, cache, thumbnail, preview or embedding that keeps serving a record after its access changed or it was deleted |
| Logs as another reader | Private content or credentials written to logs, traces or analytics with broader access or longer retention |
| Existence oracles | Counts, filters, errors, unique-constraint messages or timing that reveal another tenant's records |
| Export and restore | Exports, backups or reports that include other tenants or deleted data; imports and restores that skip ownership, validation or current policy |
| Migrations | Old records without tenant or access fields, or old and new code applying different defaults during a rollout |
| Stale authorization | Removing a member, changing a role or revoking a secret without invalidating sessions, caches, subscriptions or queued jobs |

## How to test it safely

Pick one protected record and draw its write, query, cache, index, event, export, backup, deletion and restore paths,
marking the principal and tenant on every edge. Then compare two dummy tenants through the same local service calls,
again after an access change, a deletion and a restore. Never use real user data. Start with background jobs,
migrations, service clients, global uniqueness and cache keys: these paths most often lose the request's identity.
