#!/usr/bin/env bash
# Usage: scripts/repo/apply-ruleset.sh [OWNER/REPO]   (defaults to the current repo)
set -euo pipefail

repo=${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
file=.github/rulesets/main.json
name=$(jq -r .name "$file")

id=$(gh api "repos/$repo/rulesets" -q ".[] | select(.name == \"$name\") | .id")

if [[ -n $id ]]; then
  gh api -X PUT "repos/$repo/rulesets/$id" --input "$file" >/dev/null
  echo "updated ruleset \"$name\" ($id) on $repo"
else
  gh api -X POST "repos/$repo/rulesets" --input "$file" >/dev/null
  echo "created ruleset \"$name\" on $repo"
fi
