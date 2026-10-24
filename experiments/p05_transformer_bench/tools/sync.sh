#!/bin/bash
# Move the bench between the repo (hoang's machine) and long's GPU machine.
#   tools/sync.sh push   copy code, labels and tests to ~/Desktop/Datagent/arch_bench/
#                        (results/, data/ and .venv/ on long's machine are never touched)
#   tools/sync.sh pull   copy arch_bench/results/ back into the repo
# LONG_HOST is the SSH host of long's machine. It stays out of the repo, which is public.
set -euo pipefail
: "${LONG_HOST:?set LONG_HOST to the SSH host of the GPU machine of long}"
here="$(cd "$(dirname "$0")/.." && pwd)"
remote='~/Desktop/Datagent/arch_bench'

case "${1:-}" in
  push)
    ssh "$LONG_HOST" "mkdir -p $remote"
    tar -C "$here" --exclude=./results --exclude=./data --exclude=./.venv --exclude=__pycache__ --exclude=.pytest_cache -cf - . \
      | ssh "$LONG_HOST" "tar -xf - -C $remote"
    ;;
  pull)
    mkdir -p "$here/results"
    ssh "$LONG_HOST" "tar -C $remote -cf - results" | tar -C "$here" -xf -
    ;;
  *)
    echo "usage: tools/sync.sh push|pull" >&2
    exit 2
    ;;
esac
