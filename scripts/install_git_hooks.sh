#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

git config core.hooksPath .githooks
if [ -f ".githooks/pre-commit" ]; then
    chmod +x .githooks/pre-commit
fi

echo "Git hooks installed."
echo "core.hooksPath=$(git config --get core.hooksPath)"
