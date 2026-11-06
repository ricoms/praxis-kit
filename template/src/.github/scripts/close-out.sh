#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=/dev/null
source .github/team-delivery.env

: "${GH_TOKEN:?PROJECT_TOKEN secret is not set; see docs/runbooks/board.md}"
: "${PROJECT_OWNER:?PROJECT_OWNER variable is not set; see docs/runbooks/board.md}"
: "${PROJECT_NUMBER:?PROJECT_NUMBER variable is not set; see docs/runbooks/board.md}"

repo_owner=${GITHUB_REPOSITORY%/*}
repo_name=${GITHUB_REPOSITORY#*/}

# shellcheck disable=SC2016
item=$(gh api graphql -F owner="$repo_owner" -F repo="$repo_name" -F num="$ISSUE_NUMBER" -f query='
query($owner: String!, $repo: String!, $num: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $num) {
      projectItems(first: 20) {
        nodes {
          id
          project {
            id
            number
            owner { ... on Organization { login } ... on User { login } }
            fields(first: 50) { nodes { ... on ProjectV2FieldCommon { id name } } }
          }
          fieldValues(first: 50) {
            nodes {
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
        }
      }
    }
  }
}' | jq -c --arg owner "$PROJECT_OWNER" --argjson number "$PROJECT_NUMBER" '
  .data.repository.issue.projectItems.nodes[]
  | select(.project.number == $number and .project.owner.login == $owner)')

if [[ -z $item ]]; then
  echo "::error::Issue #$ISSUE_NUMBER is not on project $PROJECT_OWNER/$PROJECT_NUMBER. Check the project's auto-add workflow."
  exit 1
fi

field_id() { jq -r --arg n "$1" '.project.fields.nodes[] | select(.name == $n) | .id' <<<"$item"; }
field_value() { jq -r --arg n "$1" '[.fieldValues.nodes[] | select(.field.name == $n) | .number][0] // empty' <<<"$item"; }

remaining_id=$(field_id "$FIELD_REMAINING")
if [[ -z $remaining_id ]]; then
  echo "::error::Project has no \"$FIELD_REMAINING\" field. Run scripts/board/bootstrap-project.sh."
  exit 1
fi

# shellcheck disable=SC2016
gh api graphql -f project="$(jq -r .project.id <<<"$item")" -f item="$(jq -r .id <<<"$item")" -f field="$remaining_id" \
  -f query='mutation($project: ID!, $item: ID!, $field: ID!) {
    updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item, fieldId: $field, value: {number: 0}}) {
      projectV2Item { id }
    }
  }' >/dev/null

estimate=$(field_value "$FIELD_ESTIMATE")
actual=$(field_value "$FIELD_ACTUAL")
if [[ -n $estimate && -z $actual ]]; then
  mentions=""
  for login in ${ASSIGNEES:-}; do mentions+="@$login "; done
  GH_TOKEN=$ISSUE_TOKEN gh issue comment "$ISSUE_NUMBER" --body \
    "${mentions}This closed with an estimate of $estimate d and no $FIELD_ACTUAL. Record $FIELD_ACTUAL (days of work) and $FIELD_WAITING (days blocked) on the board."
fi
