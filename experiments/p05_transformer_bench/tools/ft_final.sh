#!/bin/bash
# P05, after the fine-tune chain: score the so400m checkpoints with the GPU to themselves, time every encoder again
# in one job, then write results/finetune.csv and results/summary.md. Log in data/ft_final.log. Start it detached
# from arch_bench/ while the chain runs; it waits for the chain to end:
#   systemd-run --user --unit=p05-ft-final --collect -p MemoryMax=1G -p Nice=10 --working-directory=$PWD tools/ft_final.sh
cd "$(dirname "$0")/.."
say() { echo "$(date '+%Y-%m-%d %H:%M %z') $*" >> data/ft_final.log; }
unit() { systemd-run --user --wait --collect --quiet --unit="$1" -p MemoryMax=20G -p Nice=10 -p OOMScoreAdjust=1000 \
           --working-directory="$PWD" /bin/bash -c "$2"; }
say "waiting for p05-ft-chain"
while systemctl --user is-active -q p05-ft-chain; do sleep 60; done
runs=(dinov2_s dinov2_s_holdout siglip2_b siglip2_b_holdout siglip2_so400m siglip2_so400m_holdout)
done_runs=() ; new=()
for r in "${runs[@]}"; do
  if [ -f "data/ft/$r/training.json" ]; then done_runs+=("$r"); else say "no training.json for $r"; fi
done
for r in siglip2_so400m siglip2_so400m_holdout; do [ -f "data/ft/$r/training.json" ] && new+=("ft:$r"); done
if [ ${#new[@]} -gt 0 ]; then
  enc=$(IFS=,; echo "${new[*]}")
  say "scoring $enc"
  unit p05-ft-eval ".venv/bin/python -m bench.run_zeroshot --encoders $enc --galleries renders,db,db_holdout --out results/zeroshot.csv >> results/zeroshot.log 2>&1"
  say "scoring exit $?"
fi
all="dinov2_s,dinov2_b,dinov2_l,siglip2_b,siglip2_so400m,clip_l,long_ft,greyfix_ft"
for r in "${done_runs[@]}"; do all="$all,ft:$r"; done
say "re-timing $all"
unit p05-retime ".venv/bin/python -m bench.run_zeroshot --retime --encoders $all --out results/zeroshot.csv >> results/zeroshot.log 2>&1"
say "re-timing exit $?"
unit p05-report ".venv/bin/python -m bench.finetune --report ${done_runs[*]} && .venv/bin/python -m bench.report"
say "report exit $?; done"
