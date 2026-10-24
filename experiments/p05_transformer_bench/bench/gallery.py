"""Galleries of known images that a unit is named against: clean renders of the 12 cartons, the iPhone photos of the
13 products, and how a gallery is kept on disk (.npz, or .npy that loads back as a memmap)."""
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from bench.skus import HILO, KIND_TO_SKU
from bench.testset import crop_unit

HERE = Path(__file__).resolve().parents[1]          # arch_bench/
DATAGENT = HERE.parent
LABELS = HERE / "labels"
PHOTOS = HERE / "data" / "iphone"


@dataclass
class Gallery:
    name: str
    crops: np.ndarray       # (n, 384, 384, 3) uint8 RGB, may be a memmap
    sku: np.ndarray         # str, "none" for negatives
    source: np.ndarray      # str: "reference" for renders, "iphone/<photo>" for photos


def _renderer():
    """long's renderer and carton list from ../cctv_dataset, imported without writing caches into that folder."""
    sys.dont_write_bytecode = True
    if str(DATAGENT / "cctv_dataset") not in sys.path:
        sys.path.insert(0, str(DATAGENT / "cctv_dataset"))
    import build_dataset
    import carton_renderer
    return build_dataset, carton_renderer


def reference_poses(per_kind: int = 160, seed: int = 7):
    """The views of carton_recognition/data.reference_views, drawn in the same order from the same seed:
    (kind, yaw, pitch, roll, lying, base, dist, light, ambient) for every carton and view."""
    build_dataset, cr = _renderer()
    rng = np.random.default_rng(seed)
    for kind, _brand, _stem, _front, _weight in build_dataset.CLASSES:
        for i in range(per_kind):
            lying = rng.random() < 0.25
            yaw, pitch = (rng.uniform(-40, 40), rng.uniform(-35, 20)) if lying else (rng.uniform(0, 360), rng.uniform(-20, 70))
            if i < 8:            # always include the plain front, back and sides
                lying, yaw, pitch = False, i * 45.0, 10.0
            roll = 0.0 if i < 8 else (rng.uniform(-180, 180) if rng.random() < 0.4 else rng.normal(0, 15))
            base = (cr.LYING_ON_BACK if rng.random() < 0.6 else cr.LYING_ON_SIDE) if lying else None
            dist = rng.uniform(8, 30)
            light = (rng.uniform(-0.5, 0.5), rng.uniform(0.3, 0.9), rng.uniform(0.6, 1.0))
            yield kind, float(yaw), float(pitch), float(roll), bool(lying), base, dist, light, rng.uniform(0.7, 0.9)


def render_gallery(per_kind: int = 160, seed: int = 7, height: int = 170, size: int = 384) -> Gallery:
    """Renders of the 12 cartons in the views of reference_views(per_kind=160), cut with crop_unit at `size`."""
    build_dataset, cr = _renderer()
    cartons = {kind: cr.Carton(build_dataset.MODELS / (stem + ".glb"), front) for kind, _, stem, front, _ in build_dataset.CLASSES}
    crops = np.empty((per_kind * len(cartons), size, size, 3), np.uint8)
    sku = []
    for j, (kind, yaw, pitch, roll, lying, base, dist, light, ambient) in enumerate(reference_poses(per_kind, seed)):
        bgr, a = cartons[kind].render(cr.rotation(yaw, pitch, roll, base), height, dist=dist, light=light, ambient=ambient)
        canvas = np.full(a.shape + (3,), 124.0, np.float32)
        canvas += (bgr - canvas) * a[..., None]
        ys, xs = np.where(a > 0.5)
        box = (xs.min(), ys.min(), xs.max() + 1 - xs.min(), ys.max() + 1 - ys.min())
        crops[j] = crop_unit(canvas.clip(0, 255).astype(np.uint8), box, size)
        sku.append(KIND_TO_SKU[kind])
    return Gallery("renders", crops, np.array(sku), np.full(len(sku), "reference"))


def _photos(split):
    with open(LABELS / "iphone_photos.csv", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == split]
    with open(LABELS / "iphone_boxes.csv", encoding="utf-8", newline="") as f:
        boxes = {r["photo"]: tuple(json.loads(r["bounding_box"])) for r in csv.DictReader(f)}
    return rows, boxes


def _photo_gallery(name, rows, boxes, size=384):
    crops = np.empty((len(rows), size, size, 3), np.uint8)
    for j, r in enumerate(rows):
        img = cv2.imread(str(PHOTOS / r["photo"]))          # EXIF rotation applied, as in tools/iphone_boxes.py
        if img is None:
            raise FileNotFoundError(PHOTOS / r["photo"])
        crops[j] = np.rot90(crop_unit(img, boxes[r["photo"]], size), int(r["rotate"]) // 90)   # counter-clockwise, to stand it up
    return Gallery(name, crops, np.array([r["sku"] for r in rows]), np.array([f"iphone/{r['photo']}" for r in rows]))


def iphone_gallery(faces: set[str] | None, include_hilo: bool) -> Gallery:
    """The iPhone photos of the 12 products (and of HILO's first carton), cut at their boxes; faces=None keeps all six.
    HILO's second carton (split=query in iphone_photos.csv) never goes into a gallery: see hilo_queries."""
    rows, boxes = _photos("gallery")
    rows = [r for r in rows if (faces is None or r["face"] in faces) and (include_hilo or r["sku"] != HILO)]
    name = "iphone_" + ("all" if faces is None else "_".join(sorted(faces))) + ("+hilo" if include_hilo else "")
    return _photo_gallery(name, rows, boxes)


def hilo_queries() -> Gallery:
    """The six photos of HILO's second carton (IMG_0703-0708), asked against a gallery that holds the first."""
    rows, boxes = _photos("query")
    return _photo_gallery("hilo_queries", rows, boxes)


def save_gallery(g: Gallery, path: Path) -> None:
    """.npz keeps everything in one file; .npy keeps the crops (loaded back as a memmap) and <stem>.meta.npz the rest."""
    path = Path(path)
    if path.suffix == ".npz":
        np.savez(path, name=g.name, crops=g.crops, sku=g.sku, source=g.source)
    elif path.suffix == ".npy":
        np.save(path, g.crops)
        np.savez(path.with_suffix(".meta.npz"), name=g.name, sku=g.sku, source=g.source)
    else:
        raise ValueError(f"{path}: a gallery is saved as .npz or .npy")


def load_gallery(path: Path) -> Gallery:
    path = Path(path)
    if path.suffix == ".npz":
        z = np.load(path)
        return Gallery(str(z["name"]), z["crops"], z["sku"], z["source"])
    meta = np.load(path.with_suffix(".meta.npz"))
    return Gallery(str(meta["name"]), np.load(path, mmap_mode="r"), meta["sku"], meta["source"])
