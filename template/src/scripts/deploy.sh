#!/usr/bin/env bash
# Usage: scripts/deploy.sh current ENVIRONMENT          prints what serves the environment now (empty if nothing)
#        scripts/deploy.sh release ENVIRONMENT IMAGE    deploys IMAGE (by digest) and routes all traffic to it
#        scripts/deploy.sh revert  ENVIRONMENT ID       routes all traffic back to ID, as printed by `current`
# This is the project's slot, called by release.yml. The environment's variables arrive as JSON in DEPLOY_VARS.
# Replace this body with the project's deploy; until then every command fails, so no release reports success.
echo "::error::scripts/deploy.sh is not written: implement current, release and revert for this project's target" >&2
exit 1
