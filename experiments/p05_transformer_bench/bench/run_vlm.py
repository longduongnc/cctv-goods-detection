"""Step 3 of P05: Qwen2.5-VL chooses among the names of the group YOLO gave (TH pair or Sữa hạt), and Florence-2 reads
the text for sku_from_ocr, on the real units with a khá/chắc label in those groups. YOLO's own answers on the same
units are written alongside. Needs at least 20 GB of free GPU memory.

    .venv/bin/python -m bench.run_vlm --models qwen,florence
"""
import argparse
import csv
import statistics
import time
from pathlib import Path

import torch

from bench.metrics import rate
from bench.testset import load_units, read_frame, scored
from bench.vlm import Florence, QwenVL, candidates_for, sku_from_ocr, tight_crop

HERE = Path(__file__).resolve().parents[1]           # arch_bench/
SAMPLE = HERE.parent / "cv_output_sample"
COLUMNS = ["model", "n", "answered", "right", "acc", "acc_lo", "acc_hi", "right_of_answered", "ms_per_crop"]


def log(*what):
    print(time.strftime("%H:%M:%S"), *what, flush=True)


def summary(model: str, rows: list[dict]) -> dict:
    """A unit without an answer (None) counts as wrong; right_of_answered is the share right among the answers."""
    n, answered = len(rows), sum(r["pred"] is not None for r in rows)
    k, _, lo, hi = rate(sum(r["pred"] == r["label"] for r in rows), n)
    ms = [r["ms"] for r in rows if r["ms"] is not None]
    return dict(model=model, n=n, answered=answered, right=k, acc=round(k / n, 4), acc_lo=round(lo, 4), acc_hi=round(hi, 4),
                right_of_answered=round(k / answered, 4) if answered else "", ms_per_crop=round(statistics.median(ms), 1) if ms else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="qwen,florence")
    ap.add_argument("--out", type=Path, default=HERE / "results" / "vlm.csv")
    args = ap.parse_args()
    labels = HERE / "labels"
    units = [u for u in scored(load_units(sorted(labels.glob("th_labels_*.csv")) + sorted(labels.glob("vnm_labels_*.csv"))))
             if candidates_for(u)]
    frames, crops = {}, []
    for u in units:
        crops.append(tight_crop(frames.setdefault(u.image, read_frame(SAMPLE, u.image)), u.box))
    log(len(units), "units in the TH pair or Sữa hạt groups named by YOLO")
    free = torch.cuda.mem_get_info()[0] / 1e9
    if free < 20:
        raise SystemExit(f"only {free:.1f} GB of GPU memory free; the plan asks for 20")

    results = {"yolo": [dict(label=u.label, pred=u.yolo_sku, ms=None, answer=u.yolo_sku) for u in units]}
    for model in args.models.split(","):
        rows = []
        try:
            vlm = QwenVL() if model == "qwen" else Florence()
        except Exception as e:                       # the plan drops Florence-2 if it does not load
            log(model, "did not load:", type(e).__name__, str(e)[:300])
            continue
        for u, crop in zip(units, crops):
            if model == "qwen":
                pred, answer, ms = vlm.choose(crop, candidates_for(u))
            else:
                answer, ms = vlm.ocr(crop)
                pred = sku_from_ocr(answer, candidates_for(u))
            rows.append(dict(label=u.label, pred=pred, ms=ms, answer=answer))
        results[model] = rows
        log(model, "done")
        del vlm
        torch.cuda.empty_cache()

    preds = args.out.parent / "preds"
    preds.mkdir(parents=True, exist_ok=True)
    for model, rows in results.items():
        with open(preds / f"vlm_{model}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "label", "confidence", "yolo_sku", "pred", "ms", "answer"])
            for u, r in zip(units, rows):
                w.writerow([u.uid, u.label, u.confidence, u.yolo_sku, r["pred"] or "", "" if r["ms"] is None else round(r["ms"], 1),
                            " ".join(r["answer"].split())])
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(summary(model, rows) for model, rows in results.items())
    log("written", args.out)


if __name__ == "__main__":
    main()
