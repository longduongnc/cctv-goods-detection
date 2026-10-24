"""Step 2 of P05: fine-tune an encoder with the recipe of carton_recognition_greyfix/train_embedder.py --types (CosFace
s=30 m=0.3, AdamW, the same 239,920 crops and augmentation with grey=0), for a fixed number of epochs instead of a
time budget, optionally with the three HOLDOUT SKUs left out of the training data.

    .venv/bin/python -m bench.finetune --backbone siglip2_b [--holdout] --out data/ft/siglip2_b
"""
import argparse
import csv
import importlib.util
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from bench.calibrate import DATASET, GREYFIX, HERE, long_data
from bench.encoders import FT_DIR, HF, TIMM
from bench.skus import HOLDOUT, KIND_TO_SKU

SIZE = 224
MMAP = HERE / "data" / "mmap"


def training_rows(rows: list[dict], holdout: tuple[str, ...] = ()) -> list[dict]:
    """Rows whose kind is not one of the held-out SKUs (background and other-brand rows always stay)."""
    return [r for r in rows if KIND_TO_SKU.get(r["kind"]) not in holdout]


class FtNet(torch.nn.Module):
    """A backbone with the head of CartonNet: pooled feature next to the mean of the tokens -> 768 -> 256, unit length.
    timm models pool with their summary token; Hugging Face vision towers with their pooler_output."""
    dim = 256

    def __init__(self, backbone: str, pretrained: bool = True):
        super().__init__()
        self.kind = "hf" if "/" in backbone else "timm"
        if self.kind == "timm":
            import timm
            self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0, img_size=SIZE)
            d = self.backbone.num_features
        else:
            from transformers import AutoConfig, AutoModel
            # the image-text model's vision tower; without weights it is built from the same config, so the keys match
            full = AutoModel.from_pretrained(backbone) if pretrained else AutoModel.from_config(AutoConfig.from_pretrained(backbone))
            self.backbone = full.vision_model
            d = self.backbone.config.hidden_size
        self.proj = torch.nn.Sequential(torch.nn.Linear(2 * d, 768), torch.nn.BatchNorm1d(768), torch.nn.ReLU(), torch.nn.Linear(768, self.dim))

    def forward(self, x):
        if self.kind == "timm":
            t = self.backbone.forward_features(x)
            f = torch.cat([t[:, 0], t[:, self.backbone.num_prefix_tokens:].mean(1)], dim=-1)
        else:
            o = self.backbone(pixel_values=x, interpolate_pos_encoding=True)
            f = torch.cat([o.pooler_output, o.last_hidden_state.mean(1)], dim=-1)
        return F.normalize(self.proj(f), dim=-1)


def statistics(backbone: str) -> tuple[list[float], list[float]]:
    """The mean and std a backbone was pretrained with."""
    if "/" in backbone:
        from transformers import AutoImageProcessor
        p = AutoImageProcessor.from_pretrained(backbone)
        return list(p.image_mean), list(p.image_std)
    import timm
    cfg = timm.get_pretrained_cfg(backbone)
    return list(cfg.mean), list(cfg.std)


def _long_train():
    """long's train_embedder.py from carton_recognition_greyfix (to_input with the grey fix, knn_accuracy)."""
    long_data()                                       # puts the greyfix folder on sys.path, no caches written
    if "greyfix_train" not in sys.modules:
        spec = importlib.util.spec_from_file_location("greyfix_train", GREYFIX / "train_embedder.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["greyfix_train"] = module
    return sys.modules["greyfix_train"]


def _renorm(x, mean, std):
    """to_input normalises with ImageNet statistics; move a batch to the backbone's own."""
    imagenet_mean = torch.tensor([0.485, 0.456, 0.406], device=x.device).view(1, 3, 1, 1)
    imagenet_std = torch.tensor([0.229, 0.224, 0.225], device=x.device).view(1, 3, 1, 1)
    m, s = torch.tensor(mean, device=x.device).view(1, 3, 1, 1), torch.tensor(std, device=x.device).view(1, 3, 1, 1)
    return (x * imagenet_std + imagenet_mean - m) / s


@torch.no_grad()
def _embed(model, crops, device, mean, std, batch=256):
    model.eval()
    lt = _long_train()
    out = []
    for i in range(0, len(crops), batch):
        with torch.autocast("cuda", dtype=torch.float16, enabled=device == "cuda"):
            out.append(model(_renorm(lt.to_input(np.asarray(crops[i:i + batch]), device, False), mean, std)).float().cpu())
    return torch.cat(out).numpy()


def _type(r):
    return r["kind"] if r["brand"] != "none" else "none"


def _data(holdout):
    """Training and validation crops (BGR 224, memmaps in data/mmap) and their rows, as train_embedder.py --types."""
    os.environ["CROPS_MEMMAP_DIR"] = str(MMAP)
    MMAP.mkdir(parents=True, exist_ok=True)
    data = long_data()
    rows = data.load_objects(DATASET)
    train = (training_rows(data.sample_objects(rows, "train", 168000, seed=1, per_kind=True), holdout)
             + data.background_boxes(rows, "train", 30000, seed=3) + data.other_cartons(DATASET, "train", 40000, seed=5))
    val = (training_rows(data.sample_objects(rows, "val", 9600, seed=21, per_kind=True), holdout)
           + data.background_boxes(rows, "val", 3000, seed=22) + data.other_cartons(DATASET, "val", 3000, seed=23))
    ref_rows, ref_crops = data.reference_views(per_kind=160)
    keep = [i for i, r in enumerate(ref_rows) if KIND_TO_SKU.get(r["kind"]) not in holdout]
    x_train = data.cut_crops(train, DATASET, workers=16, as_array=True, room=len(keep))
    x_train[len(train):] = np.stack([ref_crops[i] for i in keep])
    x_val = data.cut_crops(val, DATASET, workers=16, as_array=True)
    return x_train, train + [ref_rows[i] for i in keep], x_val, val


def train(backbone: str, holdout: tuple[str, ...], epochs: int = 10, out_dir: Path = HERE / "data" / "ft", device: str = "cuda",
          batch: int = 192, _fake_rows: tuple[np.ndarray, list[str]] | None = None) -> Path:
    """Fine-tune `backbone` (an encoder name of bench.encoders or a timm / Hugging Face id) and return the path of the
    best checkpoint (by the kNN type accuracy of train_embedder.py on the validation crops). The step-based schedule:
    300 warm-up steps, then cosine to 2% over all the steps of `epochs` epochs. A batch that does not fit on the GPU
    is split into micro-batches whose gradients add up."""
    backbone = TIMM.get(backbone) or HF.get(backbone) or backbone
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    np.random.seed(0)
    started = time.time()
    lt = _long_train()
    if _fake_rows is None:
        x_train, train_rows, x_val, val_rows = _data(holdout)
        train_types, val_types = [_type(r) for r in train_rows], [_type(r) for r in val_rows]
        train_kinds = [r["kind"] for r in train_rows]
    else:
        x_train, train_kinds = _fake_rows
        x_val, train_types, val_types = x_train, list(train_kinds), list(train_kinds)
    classes = sorted(set(train_kinds))
    y_train = torch.tensor([classes.index(k) for k in train_kinds])
    print(f"{len(x_train)} training crops ({len(classes)} classes), {len(x_val)} validation crops, cut in {time.time() - started:.0f}s", flush=True)

    mean, std = statistics(backbone)
    model = FtNet(backbone).to(device)
    centres = torch.nn.Parameter(torch.randn(len(classes), model.dim, device=device) * 0.01)
    lrs = (3e-5, 9e-4)
    opt = torch.optim.AdamW([dict(params=model.backbone.parameters(), lr=lrs[0]),
                             dict(params=list(model.proj.parameters()) + [centres], lr=lrs[1])], weight_decay=0.05)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")
    batch = min(batch, len(x_train))
    steps_per_epoch = len(x_train) // batch
    total = epochs * steps_per_epoch
    gallery_idx = np.sort(np.random.default_rng(0).permutation(len(x_train))[:20000])
    micro, step, best, best_epoch, history, t0 = batch, 0, -1.0, 0, [], time.time()
    path = out_dir / "embedder.pt"
    prefetch = ThreadPoolExecutor(1)
    for epoch in range(1, epochs + 1):
        model.train()
        order = [np.sort(b) for b in np.array_split(torch.randperm(len(x_train)).numpy()[:steps_per_epoch * batch], steps_per_epoch)]
        upcoming = prefetch.submit(lambda b=order[0]: np.asarray(x_train[b]))
        running = 0.0
        for i, b in enumerate(order):
            crops = upcoming.result()
            if i + 1 < len(order):
                upcoming = prefetch.submit(lambda b=order[i + 1]: np.asarray(x_train[b]))
            factor = min(1.0, step / 300) * (0.02 + 0.98 * 0.5 * (1 + math.cos(math.pi * step / total)))
            for g, base in zip(opt.param_groups, lrs):
                g["lr"] = base * factor
            while True:
                try:
                    opt.zero_grad(set_to_none=True)
                    loss_sum = 0.0
                    for j in range(0, len(b), micro):
                        x = _renorm(lt.to_input(crops[j:j + micro], device, True, grey=0.0), mean, std)
                        y = y_train[torch.from_numpy(b[j:j + micro])].to(device)
                        with torch.autocast("cuda", dtype=torch.float16, enabled=device == "cuda"):
                            z = model(x)
                        logits = z.float() @ F.normalize(centres, dim=-1).T
                        loss = F.cross_entropy(30 * (logits - 0.3 * F.one_hot(y, len(classes))), y) * len(y) / len(b)
                        scaler.scale(loss).backward()
                        loss_sum += loss.item()
                    break
                except torch.cuda.OutOfMemoryError:
                    if micro <= 24:
                        raise
                    micro //= 2
                    torch.cuda.empty_cache()
                    print(f"out of GPU memory: micro-batches of {micro}", flush=True)
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            scaler.step(opt)
            scaler.update()
            running += loss_sum
            step += 1
        g = _embed(model, x_train[gallery_idx], device, mean, std)
        q = _embed(model, x_val, device, mean, std)
        types = np.array(train_types)[gallery_idx]
        acc = lt.knn_accuracy(g, types, q, np.array(val_types))
        history.append(dict(epoch=epoch, minutes=round((time.time() - t0) / 60, 1), loss=round(running / len(order), 4),
                            val_accuracy_types=round(acc, 4), micro_batch=micro))
        print(history[-1], flush=True)
        if acc >= best:
            best, best_epoch = acc, epoch
            torch.save(dict(weights={k: v.cpu() for k, v in model.state_dict().items()}, backbone=backbone, backbone_kind=model.kind,
                            dim=model.dim, size=SIZE, mean=mean, std=std, classes=classes, holdout=list(holdout), epochs=epochs,
                            best_epoch=epoch, history=history), path)
    minutes = round((time.time() - t0) / 60, 1)
    state = torch.load(path, map_location="cpu")
    state.update(history=history, train_minutes=minutes)
    torch.save(state, path)
    (out_dir / "training.json").write_text(json.dumps(dict(backbone=backbone, holdout=list(holdout), epochs=epochs, batch=batch,
                                                           train_crops=len(x_train), val_crops=len(x_val), train_minutes=minutes,
                                                           best_epoch=best_epoch, best_val_accuracy_types=best, history=history), indent=1))
    for f in MMAP.glob(f"crops_{os.getpid()}_*.npy"):
        f.unlink()
    print(f"done in {(time.time() - started) / 60:.1f} min; best validation type accuracy {best:.4f} -> {path}", flush=True)
    return path


REPORT_COLUMNS = ["run", "backbone", "holdout", "epochs", "best_epoch", "train_minutes", "gallery", "acc", "acc_lo", "acc_hi",
                  "holdout_real_k", "holdout_real_n", "holdout_real", "holdout_real_lo", "holdout_real_hi",
                  "holdout_synth_k", "holdout_synth_n", "holdout_synth", "holdout_synth_lo", "holdout_synth_hi"]


def report(results: Path, runs: list[str], ft_dir: Path = FT_DIR) -> list[dict]:
    """One row per (fine-tuned run, gallery) scored by run_zeroshot: training time and epochs, accuracy on all real units,
    and accuracy on the three HOLDOUT SKUs alone, on the real units labelled khá/chắc and on the synthetic val crops."""
    from bench.metrics import rate
    from bench.run_zeroshot import file_name
    with open(results / "zeroshot.csv", encoding="utf-8", newline="") as f:
        scored = {(r["encoder"], r["gallery"]): r for r in csv.DictReader(f)}
    with open(results / "synthetic_by_sku.csv", encoding="utf-8", newline="") as f:
        synthetic = list(csv.DictReader(f))
    rows = []
    for run in runs:
        meta = json.loads((ft_dir / run / "training.json").read_text())
        if "best_epoch" not in meta:              # runs started before best_epoch was written: the last of the best
            best = max(h["val_accuracy_types"] for h in meta["history"])
            meta["best_epoch"] = max(h["epoch"] for h in meta["history"] if h["val_accuracy_types"] == best)
        name = f"ft:{run}"
        for gallery in ("renders", "db", "db_holdout"):
            if (name, gallery) not in scored:
                continue
            z = scored[name, gallery]
            with open(results / "preds" / f"{file_name(name)}__{gallery}.csv", encoding="utf-8", newline="") as f:
                held = [p for p in csv.DictReader(f) if p["label"] in HOLDOUT and p["confidence"] in ("khá", "chắc")]
            real = rate(sum(p["answer"] == p["label"] for p in held), len(held))
            s = [r for r in synthetic if r["encoder"] == name and r["gallery"] == gallery and r["sku"] in HOLDOUT]
            synth = rate(sum(int(r["k"]) for r in s), sum(int(r["n"]) for r in s))
            row = dict(run=run, backbone=meta["backbone"], holdout="yes" if meta["holdout"] else "no", epochs=meta["epochs"],
                       best_epoch=meta["best_epoch"], train_minutes=meta["train_minutes"], gallery=gallery,
                       acc=z["acc"], acc_lo=z["acc_lo"], acc_hi=z["acc_hi"])
            for key, (k, n, lo, hi) in (("holdout_real", real), ("holdout_synth", synth)):
                row.update({f"{key}_k": k, f"{key}_n": n, key: round(k / n, 4) if n else "",
                            f"{key}_lo": round(lo, 4) if n else "", f"{key}_hi": round(hi, 4) if n else ""})
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backbone", help="encoder name (dinov2_s, siglip2_b, ...) or a timm / Hugging Face id")
    ap.add_argument("--holdout", action="store_true", help=f"leave {', '.join(HOLDOUT)} out of the training data")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=192)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--report", nargs="+", metavar="RUN", help="write results/finetune.csv for these runs of data/ft/ instead")
    args = ap.parse_args()
    if args.report:
        results = HERE / "results"
        rows = report(results, args.report)
        with open(results / "finetune.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
            w.writeheader()
            w.writerows(rows)
        (results / "ft").mkdir(exist_ok=True)
        for run in args.report:
            (results / "ft" / f"{run}_training.json").write_text((FT_DIR / run / "training.json").read_text())
        return
    train(args.backbone, HOLDOUT if args.holdout else (), epochs=args.epochs, out_dir=args.out, batch=args.batch)


if __name__ == "__main__":
    main()
