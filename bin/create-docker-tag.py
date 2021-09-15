#!/bin/bash
# Decide what name to use to tag Docker image and demo server from the CircleCI pipeline.
if [ -n "$CIRCLE_BRANCH" ]; then
  if [ -e skip-frontend ]; then
    # Will not start any demo as this branch does not affect frontend.
    TAG=""
  else
    TAG="branch-$CIRCLE_BRANCH"
  fi
elif [ -n "$CIRCLE_TAG" ]; then
  TAG="tag-$CIRCLE_TAG" ;
fi
echo $TAG
