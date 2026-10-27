#!/bin/bash
# Run one command on long's machine as a capped, low-priority job and wait for it to finish:
#   tools/remote_job.sh NAME 'command, run from ~/Desktop/Datagent/ingest_bench'
# The job is a transient systemd user unit p06-NAME (8 GB of RAM at most, nice 10, killed first when memory runs
# out), so it cannot crowd out long's own work. Its output goes to results/NAME.log there; the exit code is the
# command's. LONG_HOST is the SSH host of long's machine. It stays out of the repo, which is public.
set -euo pipefail
: "${LONG_HOST:?set LONG_HOST to the SSH host of the GPU machine of long}"
[ $# -eq 2 ] || { echo "usage: tools/remote_job.sh NAME 'COMMAND'" >&2; exit 2; }
name="$1"
# the command travels base64-encoded so that its quotes, globs and ~ reach the remote bash untouched
encoded="$(printf '%s' "$2" | base64 -w0)"
opts=(-o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
ssh "${opts[@]}" "$LONG_HOST" "mkdir -p ~/Desktop/Datagent/ingest_bench/results && systemd-run --user --unit=p06-$name --collect --wait --quiet -p MemoryMax=8G -p Nice=10 -p OOMScoreAdjust=1000 --working-directory=\$HOME/Desktop/Datagent/ingest_bench /bin/bash -c 'echo $encoded | base64 -d | bash >> results/$name.log 2>&1'"
