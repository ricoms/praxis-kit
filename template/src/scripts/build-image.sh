#!/usr/bin/env bash
# Usage: scripts/build-image.sh TAG
# Builds the deployable image. CI and the release both call this, so the image CI tests is built the same way the
# release builds it. This is the project's slot: replace this body with the build, for example
#   docker build -f Dockerfile -t "$1" .
# The image must listen on $PORT (8080 in CI) and answer GET /health: scripts/image-smoke.sh starts it and checks.
echo "::error::scripts/build-image.sh is not written: build the project's image here" >&2
exit 1
