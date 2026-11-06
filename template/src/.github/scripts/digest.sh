#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=/dev/null
source .github/team-delivery.env

unsent=$(gh issue list --state open --label "$CLIENT_OWNER_LABEL" --limit 500 \
  --json number,title,url,createdAt,labels |
  jq -r --arg asked "$ASKED_LABEL" --argjson days "$ASK_DEADLINE_DAYS" '
    map(select(all(.labels[]; .name != $asked)))
    | map(. + {age: ((now - (.createdAt | fromdateiso8601)) / 86400 | floor)})
    | sort_by(-.age)
    | map("- <\(.url)|#\(.number)> \(.title) (\(.age) d\(if .age >= $days then ", past deadline" else "" end))")
    | .[]')

waiting=$(gh pr list --state open --limit 200 \
  --json number,title,url,isDraft,createdAt,reviews,author |
  jq -r --argjson hours "$REVIEW_WAIT_HOURS" '
    map(select(.isDraft | not))
    | map(.author.login as $a | select([.reviews[] | select(.author.login != $a)] | length == 0))
    | map(. + {age: ((now - (.createdAt | fromdateiso8601)) / 3600 | floor)})
    | map(select(.age >= $hours))
    | sort_by(-.age)
    | map("- <\(.url)|#\(.number)> \(.title) by \(.author.login) (\(.age) h)")
    | .[]')

if [[ -z $unsent && -z $waiting ]]; then
  echo "Nothing waiting." | tee -a "$GITHUB_STEP_SUMMARY"
  exit 0
fi

text="*${GITHUB_REPOSITORY} — waiting on us*"
[[ -n $unsent ]] && text+=$'\n\n*Client questions not yet asked*\n'"$unsent"
[[ -n $waiting ]] && text+=$'\n\n*PRs without a review after '"$REVIEW_WAIT_HOURS"$' h*\n'"$waiting"

printf '%s\n' "$text" | tee -a "$GITHUB_STEP_SUMMARY"

if [[ -z ${SLACK_WEBHOOK_URL:-} ]]; then
  echo "::warning::SLACK_WEBHOOK_URL is not set; the digest is only in this run's summary."
  exit 0
fi

curl -fsS --retry 3 -X POST -H 'Content-Type: application/json' \
  --data "$(jq -n --arg t "$text" '{text: $t}')" "$SLACK_WEBHOOK_URL"
