#!/bin/bash
# Move the bench between the repo (hoang's machine) and long's GPU machine.
#   tools/sync.sh push   copy code, inputs and tests to ~/Desktop/Datagent/ingest_bench/
#                        (results/, data/ and .venv/ on long's machine are never touched)
#   tools/sync.sh pull   copy ingest_bench/results/ back into the repo
# LONG_HOST is the SSH host of long's machine. It stays out of the repo, which is public.
set -euo pipefail
: "${LONG_HOST:?set LONG_HOST to the SSH host of the GPU machine of long}"
here="$(cd "$(dirname "$0")/.." && pwd)"
remote='~/Desktop/Datagent/ingest_bench'
# a stalled connection (the machine is often under heavy load) fails after a minute instead of hanging
opts=(-o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
remote_sh() { ssh "${opts[@]}" "$LONG_HOST" "$@"; }

case "${1:-}" in
  push)
    # through a file and scp: piping tar into the Windows ssh client now and then never reached end of input
    tarball="$(mktemp)"
    trap 'rm -f "$tarball"' EXIT
    tar -C "$here" --exclude=./results --exclude=./data --exclude=./.venv --exclude=__pycache__ --exclude=.pytest_cache -cf "$tarball" .
    remote_sh "mkdir -p $remote"
    scp -q "${opts[@]}" "$tarball" "$LONG_HOST:Desktop/Datagent/ingest_bench/.push.tar"
    remote_sh "tar -xf $remote/.push.tar -C $remote && rm $remote/.push.tar"
    ;;
  pull)
    mkdir -p "$here/results"
    remote_sh "tar -C $remote -cf - results" | tar -C "$here" -xf -
    ;;
  *)
    echo "usage: tools/sync.sh push|pull" >&2
    exit 2
    ;;
esac
