# Decision rights

One Accountable per decision type. Roles only: who holds each role is kept outside this repository, in the team's
engagement records. Change a row by PR, like any other document.

## Roles

| Role | Holds |
|---|---|
| Engagement lead | the engagement as a whole, including its AI usage spend |
| PM | scope and sprint flow, client cadence |
| Sprint owner | the sprint's commitment |
| Architecture decider | one-way decisions, releases to prod, incidents |
| Secret custodian | rotating and revoking secrets by hand, elevated only for the rotation |
| Release owner | running a release |
| Budget owner | the AI usage budget and its fallback |
| On-call | the first response to an incident |
| Client lead | the client's side of scope, accounts and releases |
| Client platform | the client's platform the product depends on |

## Matrix

| Decision | R | A | C | I |
|---|---|---|---|---|
| Scope change | PM | client lead | architecture decider | team |
| One-way decision (reverting would not restore an equivalent state, `CONSTITUTION.md` §5) | proposer | architecture decider | co-deciders | team |
| Reversible decision | proposer | proposer | — | log, confirm in a batch |
| Send a client question | author | author | team (internal check) | PM |
| Merge code | author | author | a reviewer, recommended for one-way changes | — |
| Merge docs | author | author | — | — |
| Release to prod | release owner | architecture decider | client lead | client |
| Scheduled secret rotation (its issue approved first) | secret custodian | architecture decider | consumers' owners | team |
| Revoke a compromised secret (issue opened within a day, approved afterwards) | secret custodian | architecture decider | on-call | team |
| Change in a client org or account | proposer | client lead | — | client |
| Sprint plan | PM | sprint owner | team | client |
| Actual and Waiting on close | assignee | assignee | — | PM |
| AI usage budget | budget owner | engagement lead | team | — |
| Incident | on-call | architecture decider | client platform | client |

The Accountable decides and informs the Consulted; no objection within 2 working days of the proposal is consent.
