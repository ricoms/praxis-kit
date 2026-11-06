#!/usr/bin/env bash
set -euo pipefail

marker='<!-- doors -->'
script=$(mktemp)
git show "$BASE:.github/scripts/doors.py" >"$script" 2>/dev/null || cp .github/scripts/doors.py "$script"
result=$(python3 "$script" "$BASE" "$HEAD")
one_way=$(jq -r .one_way <<<"$result")
label() {
  gh pr edit "$PR" --add-label "$1" --remove-label "$2" >/dev/null 2>&1 \
    || gh pr edit "$PR" --add-label "$1" >/dev/null \
    || echo "::warning::cannot set $1 (read-only token on a fork PR?)"
}

comment_id=$(gh api "repos/$GITHUB_REPOSITORY/issues/$PR/comments" --paginate \
  --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$marker\"))) | .id" | head -n 1)

if [[ $one_way == true ]]; then
  reasons=$(jq -r '.reasons[] | "- **\(.condition)** `\(.path)`: \(.why)"' <<<"$result")
  body="$marker
**One-way door.** Reverting this after it has been live may not restore an equivalent state:

$reasons

Recommended: a review by someone other than the author. Required before merge: an ADR for the decision, accepted by its named decider (CONSTITUTION.md section 5)."
  label "door:one-way" "door:two-way"
elif [[ -n $comment_id ]]; then
  body="$marker
**Two-way door** since the latest push: nothing in this change is one-way any more."
  label "door:two-way" "door:one-way"
else
  label "door:two-way" "door:one-way"
  echo "Two-way door." | tee -a "$GITHUB_STEP_SUMMARY"
  exit 0
fi

printf '%s\n' "$body" | tee -a "$GITHUB_STEP_SUMMARY"
if [[ -n $comment_id ]]; then
  gh api -X PATCH "repos/$GITHUB_REPOSITORY/issues/comments/$comment_id" -f body="$body" >/dev/null \
    || echo "::warning::cannot edit the doors comment (read-only token on a fork PR?)"
else
  gh pr comment "$PR" --body "$body" >/dev/null || echo "::warning::cannot comment (read-only token on a fork PR?)"
fi
