"""Step 1 of P05: each encoder as it comes, named by kNN against a gallery, on the real units; and the three answers
of the running pipeline. One row per (encoder, gallery) in --out, written as soon as the encoder is done; a rerun
skips the pairs already there. Unit by unit answers go to preds/ next to --out.

    .venv/bin/python -m bench.run_zeroshot --encoders dinov2_s,clip_l --galleries renders,iphone_all,iphone_front \
        --out results/zeroshot.csv

With --retime it only measures ms per crop again, for encoders whose rows were timed while another job had the GPU.
"""
import argparse
import csv
import statistics
import time
from pathlib import Path

import numpy as np
import torch

from bench import gallery as gal
from bench.calibrate import synthetic_threshold, synthetic_val
from bench.encoders import licence_id, make_encoder
from bench.knn import knn_predict
from bench.licenses import license_of
from bench.metrics import BINS, rate, unit_report
from bench.skus import HILO, HOLDOUT, TH_PAIR
from bench.testset import crop_unit, load_units, negatives, read_frame, scored

HERE = Path(__file__).resolve().parents[1]           # arch_bench/
SAMPLE = HERE.parent / "cv_output_sample"
CACHE = HERE / "data" / "cache"
BASELINES = {"yolo": "yolo_sku", "db_long": "db_old_sku", "db_greyfix": "db_fixed_sku"}
GALLERIES = {
    "renders": lambda: gal.render_gallery(),
    "iphone_all": lambda: gal.iphone_gallery(None, include_hilo=False),
    "iphone_front": lambda: gal.iphone_gallery({"front"}, include_hilo=False),
    "db": lambda: gal.db_gallery(()),                    # these two keep their own memmap in data/cache
    "db_holdout": lambda: gal.db_gallery(HOLDOUT),
}
GROUPS = ("acc", "th", "suahat", "h_lt40", "h_40_60", "h_60_90", "h_ge90", "neg_rej", "real_acc")
COLUMNS = (["encoder", "gallery"] + [g + s for g in GROUPS for s in ("", "_lo", "_hi", "_k", "_n")]
           + ["threshold", "ms_gpu", "ms_cpu", "license", "hilo_reject_before", "hilo_acc_after"])


def log(*what):
    print(time.strftime("%H:%M:%S"), *what, flush=True)


def pending_pairs(encoders: list[str], galleries: list[str], out: Path) -> list[tuple[str, str]]:
    """The (encoder, gallery) pairs that have no row in `out` yet."""
    done = set()
    if Path(out).exists():
        with open(out, encoding="utf-8", newline="") as f:
            done = {(r["encoder"], r["gallery"]) for r in csv.DictReader(f)}
    return [(e, g) for e in encoders for g in galleries if (e, g) not in done]


def answers(uids, pred, top1, threshold):
    """The kNN name of each unit, or None when the kNN has none or its best carton is below the threshold."""
    return {u: (p if p is not None and t >= threshold else None) for u, p, t in zip(uids, pred, top1)}


def baseline_pred(units, name):
    """What the running pipeline answered, from the label files: yolo, db_long (DB before the grey fix), db_greyfix."""
    return {u.uid: getattr(u, BASELINES[name]) or None for u in units}


def file_name(name):
    """An encoder name as it can stand in a file name (ft:<run> -> ft_<run>)."""
    return name.replace(":", "_").replace("/", "_")


def by_sku(sku, ans):
    """{sku: (answered right, crops)} for synthetic crops whose answers are ans[i]."""
    counts = {}
    for i, s in enumerate(sku):
        k, n = counts.get(s, (0, 0))
        counts[s] = (k + (ans[i] == s), n + 1)
    return counts


def _row(encoder, gallery, units, ans, **extra):
    test = scored(units) + negatives(units)
    rep = unit_report(test, ans)
    groups = dict(acc=rep["acc"], th=rep["th_pair"], suahat=rep["sua_hat"],
                  **{g: rep["by_height"][b] for g, b in zip(("h_lt40", "h_40_60", "h_60_90", "h_ge90"), BINS)},
                  neg_rej=rep.get("neg_rejected", rate(0, 0)),
                  real_acc=rate(sum(ans.get(u.uid) is not None for u in scored(units)), len(scored(units))))
    row = dict(encoder=encoder, gallery=gallery, **extra)
    for g, (k, n, lo, hi) in groups.items():
        row.update({g: round(k / n, 4) if n else "", f"{g}_lo": round(lo, 4) if n else "", f"{g}_hi": round(hi, 4) if n else "",
                    f"{g}_k": k, f"{g}_n": n})
    return row


def _append(out, row):
    new = not out.exists()
    with open(out, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        if new:
            w.writeheader()
        w.writerow(row)


def retime(out: Path, name: str, gpu_ms, cpu_ms):
    """New ms_gpu and ms_cpu in every row of `out` for this encoder; the other rows stay as they are."""
    with open(out, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for r in rows:
        if r["encoder"] == name:
            r.update(ms_gpu=gpu_ms, ms_cpu=cpu_ms)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _write_preds(path, units, raw, top1, ans):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "confidence", "height", "pred", "top1", "answer"])
        for u, p, t in zip(units, raw, top1):
            w.writerow([u.uid, u.label, u.confidence, u.box[3], p or "", "" if t is None else round(float(t), 4), ans[u.uid] or ""])


def get_gallery(name):
    """A gallery by its --galleries name, built once and kept in data/cache as a memmap."""
    if name.startswith("db"):
        return GALLERIES[name]()
    path = CACHE / f"gallery_{name}.npy"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        gal.save_gallery(GALLERIES[name](), path)
    return gal.load_gallery(path)


def ms_gpu(enc, crops):
    """Median ms per crop over batches of 64, leaving out the first batch."""
    times = []
    for i in range(0, len(crops) - 63, 64):
        torch.cuda.synchronize()
        t = time.perf_counter()
        enc.embed(crops[i:i + 64])
        torch.cuda.synchronize()
        times.append((time.perf_counter() - t) / 64 * 1000)
    return round(statistics.median(times[1:]), 3)


def ms_cpu(name, crops):
    """ms per crop on the CPU: 100 crops in batches of 16 on 8 threads, after one batch to warm up."""
    threads = torch.get_num_threads()
    torch.set_num_threads(8)
    enc = make_encoder(name, "cpu")
    enc.embed(crops[:16])
    t = time.perf_counter()
    for i in range(0, 100, 16):
        enc.embed(crops[i:min(i + 16, 100)])
    torch.set_num_threads(threads)
    return round((time.perf_counter() - t) / 100 * 1000, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoders", required=True)
    ap.add_argument("--galleries", default="renders,iphone_all,iphone_front")
    ap.add_argument("--out", type=Path, default=HERE / "results" / "zeroshot.csv")
    ap.add_argument("--retime", action="store_true",
                    help="only measure ms_gpu and ms_cpu again for --encoders and write them into their rows of --out")
    args = ap.parse_args()
    out = args.out
    if args.retime:
        val_crops, _ = synthetic_val()
        for name in args.encoders.split(","):
            enc = make_encoder(name, "cuda")
            enc.embed(val_crops[:704])                   # warm, as a scoring run is by the time it measures
            gpu_ms = ms_gpu(enc, val_crops[:704])
            del enc
            torch.cuda.empty_cache()
            cpu_ms = ms_cpu(name, val_crops[:116])
            retime(out, name, gpu_ms, cpu_ms)
            log(name, "re-timed; ms per crop gpu", gpu_ms, "cpu", cpu_ms)
        return
    preds = out.parent / "preds"
    preds.mkdir(parents=True, exist_ok=True)
    labels = HERE / "labels"
    units = load_units(sorted(labels.glob("th_labels_*.csv")) + sorted(labels.glob("vnm_labels_*.csv")))
    uids = [u.uid for u in units]

    for name in BASELINES:
        if pending_pairs([name], ["pipeline"], out):
            ans = baseline_pred(units, name)
            _write_preds(preds / f"{name}__pipeline.csv", units, [ans[u] for u in uids], [None] * len(units), ans)
            _append(out, _row(name, "pipeline", units, ans))
            log("baseline", name)

    pairs = pending_pairs(args.encoders.split(","), args.galleries.split(","), out)
    if not pairs:
        return
    device = "cuda" if torch.cuda.is_available() else "cpu"
    frames = {}
    unit_crops = np.stack([crop_unit(frames.setdefault(u.image, read_frame(SAMPLE, u.image)), u.box) for u in units])
    val_crops, val_sku = synthetic_val()
    hilo_q = gal.hilo_queries()
    every = gal.iphone_gallery(None, include_hilo=True)
    hilo_ref = every.crops[every.sku == HILO]
    log(len(units), "units,", len(val_crops), "synthetic crops,", len(hilo_ref), "+", len(hilo_q.sku), "HILO photos")

    for name in dict.fromkeys(e for e, _ in pairs):
        todo = [g for e, g in pairs if e == name]
        enc = make_encoder(name, device)
        u_emb, v_emb = enc.embed(unit_crops), enc.embed(val_crops)
        hq_emb, hr_emb = enc.embed(hilo_q.crops), enc.embed(hilo_ref)
        galleries = {}
        for gname in todo:
            g = get_gallery(gname)
            galleries[gname] = (enc.embed(g.crops), g.sku)
        gpu_ms = ms_gpu(enc, val_crops[:704]) if device == "cuda" else ""
        del enc
        torch.cuda.empty_cache()
        cpu_ms = ms_cpu(name, val_crops[:116])
        lic = license_of(licence_id(name))
        log(name, "embedded; ms per crop gpu", gpu_ms, "cpu", cpu_ms)
        for gname, (g_emb, g_sku) in galleries.items():
            v_pred, v_top1 = knn_predict(v_emb, g_emb, g_sku)
            thr = synthetic_threshold(v_top1)
            synthetic = by_sku(val_sku, answers(range(len(v_pred)), v_pred, v_top1, thr))
            new = not (out.parent / "synthetic_by_sku.csv").exists()
            with open(out.parent / "synthetic_by_sku.csv", "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["encoder", "gallery", "sku", "k", "n"])
                w.writerows([name, gname, s, k, n] for s, (k, n) in sorted(synthetic.items()))
            raw, top1 = knn_predict(u_emb, g_emb, g_sku)
            ans = answers(uids, raw, top1, thr)
            _write_preds(preds / f"{file_name(name)}__{gname}.csv", units, raw, top1, ans)
            p, t = knn_predict(hq_emb, g_emb, g_sku)
            before = answers(range(len(p)), p, t, thr).values()
            p, t = knn_predict(hq_emb, np.vstack([g_emb, hr_emb]), np.concatenate([g_sku, [HILO] * len(hr_emb)]))
            after = answers(range(len(p)), p, t, thr).values()
            _append(out, _row(name, gname, units, ans, threshold=round(thr, 4), ms_gpu=gpu_ms, ms_cpu=cpu_ms, license=lic,
                              hilo_reject_before=round(float(np.mean([a not in TH_PAIR for a in before])), 4),
                              hilo_acc_after=round(float(np.mean([a == HILO for a in after])), 4)))
            log(name, gname, "threshold", round(thr, 4))


if __name__ == "__main__":
    main()
