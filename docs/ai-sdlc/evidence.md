# Evidence from one engagement

Terms such as RACI, door classifier and engagement ledger are explained in the [README's Terms table](../../README.md#terms).

This page summarises the one engagement the [team practices](practices.md) and their patterns were measured against.
Each article's Evidence line links the section below that it rests on. With a single engagement behind them, the
articles stay open to revision after a second one. The figures are rounded, and the underlying research is private.

## The engagement

A small vendor team rebuilt a mid-size legacy application, and the client inherits the repository. The team had an
AI architect in an enabling and platform role, developers who built with AI agents, an architect who decided one-way
changes, and a PM. A separate discovery repository came first and was archived once delivery began. The repository,
the delivery board, team and shared chat, meeting notes and a private engagement ledger were read three times, from
mid-delivery to the close, without writing to any of them.

## Figures

| Measure | Rounded value |
|---|---|
| CI runs that failed, all workflows | 2–3% |
| Merged PRs with no review from anyone but the author | about two thirds |
| Discovery-repository PRs merged without review | about nine in ten |
| PRs approved by someone other than the author, mid-delivery and near launch | about a third, then about one in eight |
| Merged PRs the door classifier marks one-way | about one in four |
| One-way PRs with an outside review | about two in five |
| Sampled unreviewed one-way PRs that were one-way on reading | nearly all |
| Client answer time once a question was sent, median | about one day |
| Team's own questions, median time to close | about five days |
| Sprint items moved to a later sprint | about one in five |
| Actual ÷ estimate, all estimated work | about 1.0 |
| Actual ÷ estimate by phase: plan / implement / verify / release | about 1.3 / 1.2 / 0.7 / 0.6 |
| Estimated done work with an Actual, before and after an agent rule | about a quarter, then about four fifths |
| Discovery-repository issues still open when it was archived | about a third |
| Agent-memory entries that were team-process rules learned from a correction | nearly half |
| Commits that were AI-assisted | nearly all |
| Lines of spec, decision and process prose churned, against lines of code | about equal |

## Repository and checks

CI failures were real defects: drift between the API contract and the frontend, failing foundational scenarios, and
an image that would not boot. Lint never failed in CI, because hooks ran it before push. The security gate went red
on days with no code change, when a new advisory appeared, and was fixed the same day. Custom static-analysis rules
turned ADR invariants into checks and blocked real findings. A long run of commits then went into closing syntax
variants of the same rules, and reviewers still found forms the rules missed. Developers wrote and kept the
foundational test contract themselves. Its manifest diff never caught a removal, but it meant none could happen out
of sight. Story slices kept AI-generated PRs small enough to review in one sitting. Releases went out about weekly,
each built once and deployed to staging several times, with automatic rollback when a deploy failed.

The discovery repository did not carry over cleanly. Its ADRs were moved by hand, the code repository gathered dozens
of references back to it, and about a third of its issues were stranded when it was archived. Its skills never loaded
during application work, because no code lived there.

## Review and one-way changes

About two thirds of merged PRs had no outside review, and approvals fell toward launch rather than rising. Review
requests mostly went through chat and queued on a few people.
Over every merged PR, the door classifier marked about one in four as one-way, and about two in five of those had an
outside review. One-way application changes were mostly reviewed. Pipeline, access-control and security-rule changes
mostly were not. Nearly every sampled unreviewed one-way PR was one-way on reading. No destructive data migration
occurred, so the data rules never fired.

## Board and estimates

GitHub's built-in project workflows kept Status in step with no drift. The fields people set by hand (Remaining Work,
Actual, Waiting) drifted until an agent rule asked for them at close. Two sprint systems run side by side disagreed
on a few percent of items. Estimates were close overall but biased by phase: planning ran about 30% over, and
verification and release about 30–40% under. A delivery margin can be compared only with the reading taken on the
same day, because replaying today's board fields against a past date does not reproduce it.

## Questions and decisions

Once a question reached the client, the client answered in about a day. Single questions with a recommended answer
were answered fastest, batches waited longer, and all of them went to one client contact. The team's own questions
took about five times as long, and drafted client questions sometimes sat unsent for weeks after the internal check.
ADR approvals moved faster once the team switched to deciding and informing the co-deciders. Test categories for
expensive decisions kept them from passing as cheap, and several ADRs followed a failure. A frozen copy of the
discovery deliverable went stale within hours, and the approval tag meant to replace it was never used.

## Communication and signals

The client asked for status early and could not find the architecture document. Some shared decks did not open for
every recipient. Most decisions were made asynchronously in GitHub and chat rather than in meetings. Meeting notes
thinned toward the close, and AI notes of the same meeting named different owners and dates. The discovery delivery
day collided with newly opened issues. Alarms reached one person's inbox. A version-only smoke check once passed while
customer-facing requests failed. Another time a deploy whose check failed was recorded as a success, and nobody saw
it. A claim about test coverage did not survive a fresh report. Security testing arrived at short notice, with its
scope spread over chat messages and its rules of engagement agreed in a private message.

## Concentration of know-how

The enabling role merged many small changes quickly and did most of the board administration, while developers wrote
most of the code. Developers began writing team skills themselves early in delivery. Near the close, know-how had
concentrated in a few roles.

## Engagement ledger

The ledger's log of who was told what, and when, stayed current. Its copies of the roadmap, weekly updates and open
external asks duplicated the board and went stale. Message kinds multiplied, and free-text audience keys made the log
hard to query. RACI existed only as defaults, never per decision type.

## Agents and AI use

Two attribution trailer forms were in use. Agents closed estimated issues without asking for Actual until a rule
stopped them. AI usage quota ran out on several days for more than one developer, with no budget owner. Nearly half of the agent-memory entries were team-process rules learned from a
correction. One sweep against connectors signed in to the wrong account returned empty results that looked like
nothing new.
