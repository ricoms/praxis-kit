#!/usr/bin/env bash
# Usage: scripts/private-refs.sh [PATTERNS_FILE]
set -euo pipefail

file=${1:-.github/private-refs.txt}
patterns=$(grep -vE '^\s*(#|$)' "$file" || true)
[[ -z $patterns ]] && exit 0

# The copier answers file must name its template source and is rewritten on every update; it is deleted at hand-over.
hits=$(git grep -n -I -E -f <(printf '%s\n' "$patterns") -- . ":(exclude)$file" ":(exclude).copier-answers.praxis-kit.yml" \
  | grep -v 'private-ref-ok' || true)
if [[ -n $hits ]]; then
  printf '%s\n' "$hits"
  echo "private-refs: the lines above match $file; remove them or mark an intended mention with private-ref-ok" >&2
  exit 1
fi
