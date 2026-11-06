#!/usr/bin/env bash
# Usage: scripts/smoke.sh BASE_URL [CHECKS_FILE]
set -euo pipefail

base=${1:?base URL}
base=${base%/}
file=${2:-.github/smoke.txt}
status=0
checks=0

while read -r method path expected _ || [[ -n ${method:-} ]]; do
  [[ -z ${method:-} || $method == \#* ]] && continue
  expected=${expected%$'\r'}
  case $method in
    GET) body=() ;;
    HEAD) body=(--head) ;;
    *) body=(--data '') ;;
  esac
  checks=$((checks + 1))
  code=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" ${body[@]+"${body[@]}"} --max-time 10 "$base$path") || code=000
  if [[ $code == "$expected" ]]; then
    echo "ok   $method $path $code"
  else
    echo "FAIL $method $path: got $code, expected $expected"
    status=1
  fi
done <"$file"

if ((checks == 0)); then
  echo "FAIL no checks in $file"
  exit 1
fi
exit "$status"
