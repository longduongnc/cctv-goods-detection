"""The synthetic crops the acceptance threshold is set on (never the real test units), and the threshold."""
import importlib.util
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from bench.skus import KIND_TO_SKU
from bench.testset import crop_unit

HERE = Path(__file__).resolve().parents[1]          # arch_bench/
DATAGENT = HERE.parent
GREYFIX = DATAGENT / "carton_recognition_greyfix"
DATASET = DATAGENT / "cctv_dataset" / "dataset_hard_types"
CACHE = HERE / "data" / "cache"


def long_data():
    """long's data.py as patched in carton_recognition_greyfix (his sampling, plus memmap crops), imported without
    writing caches into his folders."""
    sys.dont_write_bytecode = True
    if str(GREYFIX) not in sys.path:
        sys.path.insert(0, str(GREYFIX))
    if "greyfix_data" not in sys.modules:
        spec = importlib.util.spec_from_file_location("greyfix_data", GREYFIX / "data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["greyfix_data"] = module
    return sys.modules["greyfix_data"]


def _cut(task):
    path, boxes = task
    img = cv2.imread(path)
    return [crop_unit(img, b) for b in boxes]


def cut_rows(rows: list[dict], path: Path, head: np.ndarray | None = None, workers: int = 12, batch: int = 256) -> np.ndarray:
    """Cut every row's dataset box (x0, y0, x1, y1) with crop_unit into a .npy at `path`, after the crops in `head`;
    returns it as a memmap. Written as a .part file first, so a stopped run never leaves a half-filled cache. Images go
    to the workers `batch` at a time: handing them all at once let finished crops pile up in memory faster than they
    were written (the 43 GB gallery was OOM-killed under a 20 GB limit)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    first = 0 if head is None else len(head)
    part = path.with_name(path.stem + ".part.npy")
    crops = np.lib.format.open_memmap(part, mode="w+", dtype=np.uint8, shape=(first + len(rows), 384, 384, 3))
    if head is not None:
        crops[:first] = head
    by_image = {}
    for i, r in enumerate(rows):
        by_image.setdefault((r["split"], r["image"]), []).append(i)
    images = list(by_image.items())
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as ex:    # no fork of a threaded process
        for start in range(0, len(images), batch):
            part_images = images[start:start + batch]
            tasks = [(str(DATASET / "images" / split / name), [(rows[i]["x0"], rows[i]["y0"], rows[i]["x1"] - rows[i]["x0"],
                                                               rows[i]["y1"] - rows[i]["y0"]) for i in idx])
                     for (split, name), idx in part_images]
            for (_, idx), got in zip(part_images, ex.map(_cut, tasks, chunksize=8)):
                for i, c in zip(idx, got):
                    crops[first + i] = c
    crops.flush()
    del crops
    part.rename(path)
    return np.load(path, mmap_mode="r")


def synthetic_val(per_kind: int = 2000, seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    """(crops, sku): per_kind cartons of every type from the val split of dataset_hard_types, picked as
    `evaluate.py --types` picks them (sample_objects, seed 11, per_kind), cut with crop_unit. The crops are kept in
    data/cache as a .npy and come back as a memmap."""
    data = long_data()
    rows = data.sample_objects(data.load_objects(DATASET), "val", per_kind * len(KIND_TO_SKU), seed=seed, per_kind=True)
    sku = np.array([KIND_TO_SKU[r["kind"]] for r in rows])
    path = CACHE / f"synthetic_val_{per_kind}_{seed}.npy"
    return (np.load(path, mmap_mode="r") if path.exists() else cut_rows(rows, path)), sku


def synthetic_threshold(top1_pos: np.ndarray, keep: float = 0.99) -> float:
    """The similarity that `keep` of the true synthetic cartons reach."""
    return float(np.quantile(top1_pos, 1 - keep))
