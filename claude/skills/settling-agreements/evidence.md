# Evidence for each decision

What to read in an ongoing or brownfield repository before asking about a decision. Each command is read-only.
Record what you find next to the row, with the numbers, and mark the row weak when the evidence is thin or mixed.

| Decision | Read | Evidence that settles it |
|---|---|---|
| Branching and merge strategy | `gh pr list --state merged --limit 50 --json mergeCommit,headRefName`, then `git log --merges --oneline -50` and `git log --first-parent --oneline -50` | how PRs merge (squash, merge commit, rebase), and whether branches are per story or short-lived. `mergeCommit` gives only the commit id; whether it has one parent or two, in `git log`, tells a squash from a merge commit |
| Deployment workflow and its environments | `.github/workflows/*`, `gh api repos/{owner}/{repo}/environments`, deploy scripts | what deploys, from which trigger, to which environments |
| Rollback workflow | the deploy workflow's inputs, runbooks, `gh run list --workflow <deploy>` | whether a rollback path exists and whether it has ever run |
| Hotfix path | branches and tags named like `hotfix/*`, releases outside the normal cadence | whether urgent fixes go through the same checks |
| Review norms | `gh pr list --state merged --limit 50 --json reviews,author`, `.github/CODEOWNERS`, the ruleset | the share of PRs reviewed, and whether a review is required |
| Definition of done | the PR template, issue close-out automation, closed issues' last comments | what has to be true before work is closed |
| Versioning and release notes | `git tag --sort=-creatordate`, `gh release list`, `CHANGELOG.md` | the tag scheme and where release notes come from |
| Incident handling | `docs/runbooks/incidents/`, postmortem docs, alerting config | who responds and where alarms go |
| Response expectations | PR time to first review: `gh pr list --state merged --json createdAt,reviews` | the median wait, which shows the practice rather than the intent |
| How these agreements change | existing `docs/agreements.md`, ADRs about process | whether a change process exists at all |

Floor checks to run on any brownfield repository, because a breach becomes a gap rather than an agreement:

- **Secrets:** `gitleaks detect` or the project's secrets recipe, over history as well as the tree.
- **Locked dependencies:** a committed lockfile for every manifest, and no open `>=` ranges.
- **Red merges:** `gh pr list --state merged --json statusCheckRollup` for PRs merged with failing checks.
- **Manual deploys:** deploy commands in runbooks or scripts meant to be run from a workstation.
