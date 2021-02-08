#!/bin/bash
#
# Check that a branch name is the same as origin's default (HEAD).

set -e
set -o pipefail

readonly BRANCH="${1:-$CIRCLE_BRANCH}"
readonly REMOTE="${2:-origin}"

[[ "$(git rev-parse --abbrev-ref "$REMOTE/HEAD")" == "$REMOTE/$BRANCH" ]]
