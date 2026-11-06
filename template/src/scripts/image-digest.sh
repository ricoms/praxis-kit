#!/usr/bin/env bash
# Usage: scripts/image-digest.sh REGISTRY/REPOSITORY:TAG
# Prints the image's digest. Exits 2 when the registry has no such tag, and 1 on any other error, so callers can
# tell "not built yet" from "cannot reach the registry". The registry login is the target-setup action's job.
set -uo pipefail
ref=${1:?usage: scripts/image-digest.sh REGISTRY/REPOSITORY:TAG}
err=$(mktemp)
trap 'rm -f "$err"' EXIT
if out=$(docker buildx imagetools inspect "$ref" --format '{{json .Manifest}}' 2>"$err"); then
  digest=$(jq -r '.digest // empty' <<<"$out")
  [ -n "$digest" ] || { echo "::error::$ref exists but has no digest" >&2; exit 1; }
  echo "$digest"
elif grep -Eqi '(: ?not found|manifest unknown)[[:space:]]*$' "$err"; then
  exit 2
else
  cat "$err" >&2
  exit 1
fi
