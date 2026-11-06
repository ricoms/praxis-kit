#!/usr/bin/env bash
# Usage: scripts/adr-lint.sh [ADR_DIR]
set -euo pipefail

dir=${1:-docs/adr}
status=0

for adr in "$dir"/[0-9][0-9][0-9][0-9]-*.md; do
  [[ -e $adr ]] || continue
  if ! grep -qE '^- Status: (proposed|accepted|superseded by .+)$' "$adr"; then
    echo "$adr: needs '- Status: proposed | accepted | superseded by [NNNN](...)'"
    status=1
  fi
  if ! grep -qE '^- Deciders: [^<[:space:]]' "$adr"; then
    echo "$adr: needs '- Deciders: <the named decider>' filled in"
    status=1
  fi
done

exit "$status"
