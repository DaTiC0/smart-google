#!/usr/bin/env bash
set -euo pipefail

pattern='(/home/[[:alnum:]_.-]+/|/Users/[[:alnum:]_.-]+/|[A-Za-z]:\\\\Users\\\\)'

matches="$(git ls-files -z | xargs -0 grep -nIE "$pattern" || true)"

if [[ -n "$matches" ]]; then
  echo "Absolute local paths detected in tracked files:"
  echo "$matches"
  echo
  echo "Replace local machine paths with relative paths, env variables, or configurable settings."
  exit 1
fi

echo "No local absolute paths detected."
