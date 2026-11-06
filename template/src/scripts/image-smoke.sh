#!/usr/bin/env bash
# Usage: scripts/image-smoke.sh IMAGE
set -euo pipefail

image=${1:?image}
name=image-smoke-$$
docker run -d --name "$name" -e PORT=8080 -p 8080:8080 "$image" >/dev/null
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  curl -fs -o /dev/null http://127.0.0.1:8080/health && break
  sleep 1
done

scripts/smoke.sh http://127.0.0.1:8080 || { docker logs "$name"; exit 1; }
