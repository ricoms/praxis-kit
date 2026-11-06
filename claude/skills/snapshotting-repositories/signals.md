# Signals

Each signal `hugin snapshot` computes, where it comes from, how, and what has gone wrong measuring it. "Window"
means `since <= t < until`; "cumulative" means everything before `until`.

## Edge list

Nodes: `repo`, `pr:<n>`, `issue:<n>`, `commit:<sha>`, `release:<tag>`, `deployment:<id>`, `run:<id>`,
`branch:<name>`, `milestone:<title>`, `person:<role>`. With `--board`, an issue node carries its board fields. No node
holds a login or a PR or issue title; a milestone node holds the milestone's title.

| Edge | From → to | Source |
| --- | --- | --- |
| `authored` | person → PR | `pullRequest.author` |
| `reviewed` | person → PR, with state, time and whether it was the author | `pullRequest.reviews` (first 100) |
| `merged_as` | PR → commit | `pullRequest.mergeCommit` |
| `closes` | PR → issue | `closingIssuesReferences`, same repo only |
| `filed`, `assigned` | person → issue | issue author, assignees |
| `tags` | release → commit | `commits/{tag}` |
| `deploys` | deployment → commit | `deployment.sha` |
| `milestoned`, `demilestoned` | issue → milestone, with time | `issue.timelineItems` (first 50) |
| `contains` | deployment → commit | `compare/{previous deploy in the env}...{sha}` |

These edges carry `source: api`. The edges below are read from PR and issue titles and bodies and from commit messages,
carry `source: text`, and record the field and pattern in `evidence`, never the text. A text edge is kept only when its
target node exists.

| Edge | From → to | Pattern |
| --- | --- | --- |
| `reverts` | PR or commit → PR or commit | `Reverts owner/repo#N`; `This reverts commit <sha>` |
| `review_of` | PR or commit → PR | `review of #N` |
| `decides` | issue → ADR | an issue title citing an ADR with decide, decision, accept, approve or ratify |
| `cites` | PR, issue, commit or check file → ADR | `ADR 0012`, `ADR-12`, `decisions/0012-`, outside a decide title |
| `references` | PR or issue → PR or issue | `#N`, minus numbers already matched above |

A commit merged as a PR's squash commit is attributed to that PR. With `--checkout`, a revert commit brought into the
default branch by a merge commit gives its `reverts` edge the merge commit's PR as source: the oldest first-parent
commit in `git rev-list --ancestry-path <sha>..origin/<default>`, skipped when the commit is itself on the first-parent
line. That edge then joins the one read from the revert PR's body.

## Flow

| Signal | Formula | Trap |
| --- | --- | --- |
| Opened, merged, closed unmerged | PRs whose created, merged or closed time is in the window | The window's start must be exact, or the snapshot overlaps the previous one |
| Open → merge time | median, p75, p90 of merged − created, hours; also per role | A median hides a team split between minutes and days; read per role |
| Size | additions + deletions; median and share ≥ 1,000 lines | Generated files (lockfiles, OpenAPI, types) inflate it |
| Merge target | merged into the default branch or another | Story or feature-branch slices are reviewed at a different point |

## Review

| Signal | Formula | Trap |
| --- | --- | --- |
| No outside review | merged PRs with no review by someone other than the author, bots excluded | Reviews in chat or calls are invisible; a bot reviewer counted as a person inflates coverage |
| No outside approval | as above, approvals only | Differs a lot from the first; report both |
| Reviewer concentration | reviews given in the window by role; top reviewer's share | — |
| Ruleset | each ruleset's enforcement and required approvals | A written review rule and the enforced one can disagree |

## CI

| Signal | Formula | Trap |
| --- | --- | --- |
| Failure rate | failed ÷ all runs, in the window and cumulative; per workflow | The runs API returns at most 1,000 results per query, so runs are fetched per day and a capped day is warned |
| Failed on the default branch | failed runs whose head branch is the default | A new security advisory turns runs red with no code change |

## DORA estimates, per environment

| Signal | Formula | Trap |
| --- | --- | --- |
| Deploy frequency | deployments in the window, and per week | Measures staging until production deploys exist |
| Change failure rate | deployments whose latest status other than `inactive` is `error` or `failure`, ÷ deployments | A deploy that records success after a failed check is invisible here |
| Time to restore | failed deployment → next successful one in the same environment, hours | A planned test window that fails on purpose counts as a failure |
| Merge → deploy | PR merged → first deployment whose `contains` or `deploys` edge reaches its merge commit, hours | Compare is capped at 250 commits; slices merged into a feature branch reach a deploy only through the branch's own merge |

## Issues and hygiene

| Signal | Formula | Trap |
| --- | --- | --- |
| Open, opened, closed, closed not planned | issue state and times | Open counts are at collection time |
| Open by kind | first label that is `bug`, `enhancement`, `question` or `type:*` | A project with other kind labels shows them as `none` |
| Unassigned, assigned by role | open issues and their assignees | A departing role's open assignments are the handover list |
| Stale open PRs | open PRs older than 14 days at `until` | — |
| Merged, not deleted | live branches named as the head of a merged PR, with no open PR | Counting by ancestry instead misses squash merges |

## Board, with `--board`

Sprints are milestones, as in `reading-delivery-velocity`; both call the same functions in `hugin`'s velocity module,
`src/hugin/velocity.py`.

| Signal | Formula | Trap |
| --- | --- | --- |
| Planned and done per sprint | sum of Estimate per sprint, all and Done; done ÷ capacity | An item moved between sprints moves its credit, so read elapsed sprints together |
| Margin | capacity × sprints due on or after the board's `as_of` date, minus open work (Remaining Work, else Estimate) up to the target | Fields are as of collection; the board has no history, so a past margin cannot be replayed |
| Actual ÷ estimate | by Phase and by `type:` label, Σ and median; under 5 pairs is a small sample | Low Actual coverage limits the ratio, not the burn |
| Carry-over | per sprint, items ever in it, and items that left it while open for a later sprint after it began (a demilestone and a milestone within a minute); share over elapsed sprints. A sprint begins at the previous sprint's due date; the first begins at its due date minus the gap between the first two due dates, and with only one sprint carried-over and re-planned are `null` (unknown). Re-planned early and other departures are separate columns | Events record the milestone's title at the time. Renames are resolved when an issue's last event names the old title and it now sits in the new one; conflicting or missing evidence leaves the title unresolved |

## Lineage

| Query | Path | Sources | Trap |
| --- | --- | --- | --- |
| Revert chains | revert in the window → reverted PR → its first deploy → failed deploys between that deploy and the revert, in any environment, that carried the change: their `contains` or `deploys` edge reaches the reverted commit | text, api | A fix-forward PR is not a revert; failed deploys with no revert need their run logs read. Without `--checkout`, a revert merged through a merge-commit PR yields two chains, one from the commit and one from the PR body, and the reading warns; its commit is timed at its own date, not the merge |
| Story rollups | story PR merged into the default branch in the window ← slices merged into its head branch; review of each; merge → deploy | api | A slice is reviewed at the story's merge, so its own missing review is not a gap by itself |
| Decision lineage | ADR ← decide issues ← citing PRs and commits ← check files citing it (with `--checkout`) | text | Citation is not compliance: a check that names an ADR may test only part of it. A decide issue for a new ADR that names the one it amends counts for the amended one |
