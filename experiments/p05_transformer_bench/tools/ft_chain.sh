#!/bin/bash
# P05 step 2 on long's machine: the six fine-tune runs one after another, each in its own systemd unit
# (MemoryMax 22G, Nice 10, OOMScoreAdjust 1000). Start it detached from arch_bench/:
#   systemd-run --user --unit=p05-ft-chain --collect --working-directory=$PWD tools/ft_chain.sh
# A run that already wrote data/ft/<run>/training.json is skipped, so the chain can simply be started again.
# Each run logs to data/ft/<run>.log; start and end times go to results/finetune_runs.txt.
set -u
cd "$(dirname "$0")/.."
mkdir -p data/ft results
for run in dinov2_s dinov2_s:holdout siglip2_b siglip2_b:holdout siglip2_so400m siglip2_so400m:holdout; do
  backbone=${run%%:*}
  flag=""
  [ "$run" != "$backbone" ] && flag="--holdout"
  tag=$backbone${flag:+_holdout}
  [ -f "data/ft/$tag/training.json" ] && continue
  echo "$(date '+%Y-%m-%d %H:%M %z') start $tag" >> results/finetune_runs.txt
  systemd-run --user --wait --collect --quiet --unit="p05-ft-$tag" -p MemoryMax=22G -p Nice=10 -p OOMScoreAdjust=1000 \
    --working-directory="$PWD" /bin/bash -c ".venv/bin/python -m bench.finetune --backbone $backbone $flag --out data/ft/$tag > data/ft/$tag.log 2>&1"
  status=$?
  rm -f data/mmap/*.npy                                   # a run that stopped early leaves its 38 GB of crops behind
  echo "$(date '+%Y-%m-%d %H:%M %z') end $tag (exit $status)" >> results/finetune_runs.txt
done
