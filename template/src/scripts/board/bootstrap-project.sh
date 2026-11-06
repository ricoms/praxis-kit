#!/usr/bin/env bash
# Usage: scripts/board/bootstrap-project.sh OWNER PROJECT_NUMBER
set -euo pipefail

owner=${1:?owner (org or user login)}
number=${2:?project number}

existing=$(gh project field-list "$number" --owner "$owner" --format json --limit 100 | jq -r '.fields[].name')

create() {
  local name=$1; shift
  if grep -qxF "$name" <<<"$existing"; then
    echo "exists: $name"
  else
    gh project field-create "$number" --owner "$owner" --name "$name" "$@" >/dev/null
    echo "created: $name"
  fi
}

create "Estimate" --data-type NUMBER
create "Actual" --data-type NUMBER
create "Remaining Work" --data-type NUMBER
create "Waiting" --data-type NUMBER
create "Phase" --data-type SINGLE_SELECT --single-select-options "Plan,Implement,Verify,Release"
