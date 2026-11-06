---
name: managing-github-issues
description: >-
  Finishable GitHub issues, epics, and boards: track-by-state (never markdown
  checklists), native sub-issues, close on real completion. Use when
  creating/updating any issue, epic, or board, or splitting work.
metadata:
  tags:
    - github
    - issues
    - project-management
    - workflow
---

# GitHub Issues & Project Boards

How to structure issues, epics, and the project board so work stays trackable and actually finishes. Apply whenever creating or updating GitHub issues, epics, or a project board.

## Issues must be finishable

- An issue is a unit of work with a clear beginning/middle/end that **closes**. Scope it so completion is reachable; avoid open-ended "tracking" issues that accumulate comments and linger forever.
- When work mixes altitudes — *foundation* (prerequisites) vs *per-unit execution* vs *cleanup/retirement* — split it into separate issues. A single issue spanning all three can't reach "done." Slice by the real unit of completion (e.g. per-report, not per-shared-dependency).

## Track by issue state, never by checklist

- **NEVER use in-issue markdown checklists (`- [ ]`) as progress trackers.** They don't get ticked — they rot while comments pile up underneath, falsely reading "in progress" forever.
- Track progress by what teams actually maintain: an issue's **open/closed** state and the board's **Status** field.
- Group related work as **native sub-issues** under an epic — the sub-issue progress bar is driven by open/closed, so it updates itself (the checklist that ticks itself).
- Convey phase/ordering via **title prefixes** (e.g. `[Foundation]` / `[Activation]` / `[Retire]`) or a board single-select field — not checkboxes.
- A short operator runbook of steps *inside* an issue is fine — but don't treat its unticked boxes as progress signal.

## Cross-repo initiatives

- One **coordination epic** in the home repo + per-repo **native sub-issues** (cross-repo sub-issues work).
- Keep every child on the board with a **Status** (Todo → In Progress → Done) and an **assignee**, updated *as work moves* — not batched at the end.

## Screenshots and other images

GitHub has no API or `gh` command for issue attachments. Images that only the CLI can upload therefore go into the repo under a dated tag. Never use a branch for them: a branch for assets lives forever and invites a merge.

```sh
f=ui/YYYY-MM-DD-<slug>.png; tag=issue-assets/YYYY-MM-DD[-<slug>]
blob=$(git hash-object -w <image-path>)
sub=$(printf '100644 blob %s\t%s\n' "$blob" "${f#ui/}" | git mktree)
root=$(printf '040000 tree %s\tui\n' "$sub" | git mktree)
commit=$(git commit-tree "$root" -m "docs: screenshot for <issue topic>")
git tag -a "$tag" "$commit" -m "<what the images show>"
git push origin "refs/tags/$tag"
```

- The commit has no parent, so it shares no history with the default branch and never touches the working tree.
- Embed with `https://github.com/<owner>/<repo>/blob/<tag>/<f>?raw=true`. Tags are immutable, so a later batch gets a new tag.
- Before tagging, check that the repo has no workflow triggered by tag pushes (`on: push: tags:`). A release-triggered deploy does not fire, because pushing a tag publishes no release.
- A pre-push hook still runs on a tag-only push. If it fails, find out why before retrying. Never pass `--no-verify`.
- In a private repo the image loads only for a signed-in browser. Ask the user to confirm that it renders.

## Closing

- Close on merge/done. If a PR's closing keyword (`Closes #N`) auto-closed an issue **prematurely** — e.g. the adapter merged but the cutover/sign-off isn't done — **reopen it**. Issue state must reflect *real* completion, not "code merged."
- **Close the board fields in the same step.** A closed issue has Status Done and Remaining Work 0, and an open one is never Done. Ask the owner for the Actual; never estimate it. Capacity is read off these fields, so a stale one distorts the next plan.
- **Scope grew mid-issue?** Fold the new work into the open issue's "Done when" and re-estimate it, rather than filing a sibling that nobody links back.

## What becomes an issue

- Only live, finishable work or a live ask. Items found while retiring a document that are already past, or that nobody still wants, are dropped, not filed.
- **One question per issue**, labelled as a question and with the owner of the answer. A batch of questions closes only when the slowest one is answered, and the fast answers sit invisible inside it.

## Adopting the labelling rule

Applies the first time the `labelling-issues` rule meets a repo that already has issues.

Measure before writing the project's section: label definitions, usage counts, how many carry no **kind**, then skim titles for defects that never got `bug` (`fix:` prefixes, wrong output, crashes, silent failures). Propose the corrections — never bulk-relabel unasked.

Count the missing kinds by intersecting against the kind set, never by looking for issues with *no* labels — one carrying only `track:`/`size:` still cannot be counted:

```sh
gh issue list --state open --limit 100 --json number,title,labels \
  --jq '.[] | select([.labels[].name] | any(. == "bug" or . == "enhancement" or . == "question") | not)
        | "#\(.number) \(.title)"'
```

Backfill kinds, but **not sizes** — an estimate invented long after filing is fiction, and the no-revision rule means it will never be corrected. Leave old issues sizeless.

Where a kind is genuinely arguable *and* the classification reads as a judgement about a person's work rather than the system's, leave it off and say why. A contested label is worse than a gap, because the gap is visible.

Decide explicitly whether the project reads `bug` strictly (*behaved incorrectly*) or broadly (*went wrong in any sense*), then make the labels match the choice. Either is defensible; drifting between them is not.

## Anti-patterns

Markdown checklists as the source of truth for progress · open-ended tracking issues that never close · cross-repo work crammed into one mega-issue · updating board Status/assignee in a batch at the end · leaving an issue closed when the work isn't actually done · slicing issues by shared dependency when completion happens per consumer · a long-lived branch holding issue screenshots.

## See also

- `labelling-issues` (rule, always-on) — kind/track/size axes and the `bug` boundary
