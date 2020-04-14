#!/bin/bash
# Tests for the get_demo_vars script.

readonly SCRIPT="$(dirname "${BASH_SOURCE[0]}")/get_demo_vars.sh"
readonly GIT_USER="git -c user.email=test@example.com -c user.name=TEST"
readonly HEAD="$(git rev-parse --short HEAD)"
EXIT=0

function test_with_branch_and_tag {
  local test_name=$1
  local branch=$2
  local tag=$3
  local expected_result=$4
  echo "Testing $test_name..."
  local result="$(CIRCLE_PROJECT_USERNAME="bayes" CIRCLE_PROJECT_REPONAME="bob" CIRCLE_TAG=$tag CIRCLE_BRANCH=$branch $SCRIPT $HEAD)"
  if [[ $expected_result != $result ]]; then
    EXIT=1
    echo "Unable to parse vars for $test_name." &1>2
    echo "expected \"$expected_result\", got \"$result\"." &1>2
  fi
}

test_with_branch_and_tag "a release tag for Actiris" "" "release_ACTIRIS_01" "path=%2Factiris%2Fbilan&env=ACTIRIS_"

test_with_branch_and_tag "the master branch" "master" "" ""

test_with_branch_and_tag "a release tag" "" "2020-02-18_01" ""

# A branch with "normal" changes.
git checkout -q -b cyrille-branch
touch something > /dev/null
git add something > /dev/null
$GIT_USER commit -qnm "A simple commit." > /dev/null
test_with_branch_and_tag "a simple branch" "cyrille-branch" "" "repo=bayes%2Fbob&branch=bayes:cyrille-branch&path=&env="
git checkout -q - > /dev/null
git branch -D cyrille-branch > /dev/null

# A branch with a path.
git checkout -q -b cyrille-path
touch something > /dev/null
git add something > /dev/null
$GIT_USER commit -qnm "A simple commit.

PATH=/eval" > /dev/null
test_with_branch_and_tag "a commit with a set path" "cyrille-path" "" "repo=bayes%2Fbob&branch=bayes:cyrille-path&path=%2Feval&env="
git checkout -q - > /dev/null
git branch -D cyrille-path > /dev/null

# A branch with only Actiris changes.
git checkout -q -b cyrille-actiris-branch
touch actiris.py > /dev/null
git add actiris.py > /dev/null
$GIT_USER commit -qnm "An actiris commit." > /dev/null
test_with_branch_and_tag "an Actiris branch" "cyrille-actiris-branch" "" "repo=bayes%2Fbob&branch=bayes:cyrille-actiris-branch&path=%2Factiris%2Fbilan&env=ACTIRIS_"
git checkout -q - > /dev/null
git branch -D cyrille-actiris-branch > /dev/null

# A branch with only actiris commits.
git checkout -q -b cyrille-acti-commit-branch
touch something > /dev/null
git add something > /dev/null
$GIT_USER commit -qnm "[Actiris] An Actiris commit."
test_with_branch_and_tag "a branch with Actiris commit" "cyrille-acti-commit-branch" "" "repo=bayes%2Fbob&branch=bayes:cyrille-acti-commit-branch&path=%2Factiris%2Fbilan&env=ACTIRIS_"
git checkout -q - > /dev/null
git branch -D cyrille-acti-commit-branch > /dev/null

exit $EXIT
