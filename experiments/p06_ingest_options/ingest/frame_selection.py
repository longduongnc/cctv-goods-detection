"""E4 (an indicator, not used to decide): how far the count of one frame strays from the whole clip, and how often a
person covers the shelf.

    python -m ingest.frame_selection --clip-json ~/Desktop/Datagent/carton_recognition/checked_videos_types \
        --merl data/merl --merl-roi inputs/merl_shelf_roi.csv --person-model ~/Desktop/Datagent/yolo/yolo26s.pt \
        --out results/frame_selection.csv

The phone clips are hand-held, so part of the frame-to-frame change is the view moving, not people in the way.
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean, median

import cv2
import numpy as np

from ingest.edge_filter import overlaps


def clip_files(folder: Path) -> list[Path]:
    """The per-clip result files (a dict with "frames"); the folder also holds summary.json, a list over all clips."""
    clips = []
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "frames" in data:
            clips.append(path)
    return clips


def counts_per_frame(frames: dict[str, list[dict]]) -> list[Counter]:
    """Cartons per SKU (YOLO's type) in each frame, in frame order."""
    return [Counter(u["yolo_type"] for u in frames[k]) for k in sorted(frames, key=int)]


def median_counts(counts: list[Counter]) -> dict[str, float]:
    """Median count of every SKU seen in any frame; a frame without the SKU counts 0."""
    skus = sorted(set().union(*counts)) if counts else []
    return {s: float(median(c.get(s, 0) for c in counts)) for s in skus}


def deviation(c: Counter, med: dict[str, float]) -> float:
    """Sum over SKUs of |count in this frame − median count|."""
    return float(sum(abs(c.get(s, 0) - med.get(s, 0.0)) for s in set(med) | set(c)))


def random_frame_deviation(counts: list[Counter], n: int = 1000, seed: int = 0) -> dict:
    """What one frame picked at random (a blind snapshot) misses by, against the clip's median."""
    med = median_counts(counts)
    devs = [deviation(c, med) for c in counts]
    rng = random.Random(seed)
    sample = [devs[rng.randrange(len(devs))] for _ in range(n)]
    return dict(mean=float(mean(sample)), p50=float(np.percentile(sample, 50)), p90=float(np.percentile(sample, 90)))


def occlusion_stats(flags: list[bool], fps: float) -> dict:
    """flags: one per frame, True when a person covers the shelf."""
    longest = run = 0
    for covered in flags:
        run = 0 if covered else run + 1
        longest = max(longest, run)
    occluded = sum(flags)
    return dict(frames=len(flags), occluded=occluded, occluded_share=occluded / len(flags) if flags else 0.0,
                longest_clean_s=longest / fps)


def merl_flags(video: Path, roi: tuple[int, int, int, int], person_model: Path) -> tuple[list[bool], float]:
    """Per frame, whether YOLO26s (COCO) finds a person overlapping the shelf region; and the clip's frame rate."""
    from ultralytics import YOLO
    model = YOLO(str(person_model))
    cap = cv2.VideoCapture(str(video))
    fps, flags = cap.get(cv2.CAP_PROP_FPS), []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        boxes = model.predict(frame, classes=[0], imgsz=640, conf=0.4, device="cpu", verbose=False)[0].boxes
        flags.append(any(overlaps(b, roi) for b in boxes.xyxy.cpu().numpy()))
    cap.release()
    return flags, fps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip-json", type=Path, required=True)
    ap.add_argument("--merl", type=Path, required=True)
    ap.add_argument("--merl-roi", type=Path, required=True)
    ap.add_argument("--person-model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = []
    for path in clip_files(args.clip_json):
        counts = counts_per_frame(json.loads(path.read_text(encoding="utf-8"))["frames"])
        stats = random_frame_deviation(counts)
        stats["median_units"] = sum(median_counts(counts).values())
        rows += [dict(source="phone", clip=path.stem, frames=len(counts), metric=k, value=round(v, 3)) for k, v in stats.items()]
    with open(args.merl_roi, encoding="utf-8") as f:
        rois = {r["clip"]: tuple(int(r[k]) for k in "xywh") for r in csv.DictReader(f)}
    for clip, roi in rois.items():
        flags, fps = merl_flags(args.merl / clip, roi, args.person_model)
        stats = occlusion_stats(flags, fps)
        rows += [dict(source="merl", clip=clip, frames=stats["frames"], metric=k, value=round(v, 3))
                 for k, v in stats.items() if k != "frames"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "clip", "frames", "metric", "value"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
