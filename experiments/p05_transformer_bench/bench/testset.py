"""The real test units (hand labels of the 39-frame sample) and the one crop function every model is scored on."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from bench.skus import normalize_label


@dataclass(frozen=True)
class Unit:
    uid: str
    image: str
    capture_id: str
    box: tuple[int, int, int, int]      # x, y, w, h in the frame
    store: str
    label: str                          # SKU code, NEG, AMBIG or SKIP
    confidence: str                     # chắc, khá, thấp or ""
    yolo_sku: str
    db_old_sku: str | None
    db_fixed_sku: str | None


def load_units(paths: list[Path]) -> list[Unit]:
    """Units from label files in the layout of th_labels_2026-10-24.csv."""
    units = []
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                units.append(Unit(
                    uid=r["id"], image=r["image_filename"], capture_id=r["capture_id"],
                    box=tuple(json.loads(r["bounding_box"])),
                    store=r["image_filename"].split("_")[0].split("-")[1],          # PHONE-S01-A_… -> S01
                    label=normalize_label(r["label"]), confidence=r["confidence"], yolo_sku=r["yolo_sku_id"],
                    db_old_sku=r["db_old_sku_id"] or None, db_fixed_sku=r["db_fixed_sku_id"] or None))
    return units


def scored(units: list[Unit], confident_only: bool = True) -> list[Unit]:
    """Units with a SKU label; with confident_only, only labels marked khá or chắc."""
    return [u for u in units if u.label.startswith("TMP-MLK-") and (not confident_only or u.confidence in ("khá", "chắc"))]


def negatives(units: list[Unit]) -> list[Unit]:
    """Units that are not one of our 12 products (pouches, 1 L boxes, other brands)."""
    return [u for u in units if u.label == "NEG"]


def read_frame(sample_dir: Path, image: str) -> np.ndarray:
    """A sample frame as cv2 reads it (BGR)."""
    frame = cv2.imread(str(sample_dir / "images" / image))
    if frame is None:
        raise FileNotFoundError(sample_dir / "images" / image)
    return frame


def crop_unit(img_bgr: np.ndarray, box: tuple[int, int, int, int], size: int = 384) -> np.ndarray:
    """The box (x, y, w, h) with a 6% margin, fitted into a grey square without stretching, as RGB.

    The same geometry as carton_recognition/embedder.crop_box, which takes x0, y0, x1, y1 and returns BGR."""
    h, w = img_bgr.shape[:2]
    x, y, bw, bh = box
    m = 0.06 * max(bw, bh)
    xa, ya = int(max(np.floor(x - m), 0)), int(max(np.floor(y - m), 0))
    xb, yb = int(min(np.ceil(x + bw + m), w)), int(min(np.ceil(y + bh + m), h))
    c = img_bgr[ya:max(yb, ya + 1), xa:max(xb, xa + 1)]
    s = size / max(c.shape[:2])
    c = cv2.resize(c, (max(1, round(c.shape[1] * s)), max(1, round(c.shape[0] * s))),
                   interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    out = np.full((size, size, 3), 124, np.uint8)
    oy, ox = (size - c.shape[0]) // 2, (size - c.shape[1]) // 2
    out[oy:oy + c.shape[0], ox:ox + c.shape[1]] = c[..., ::-1]
    return out
