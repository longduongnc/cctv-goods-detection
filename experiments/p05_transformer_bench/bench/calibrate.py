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


def synthetic_val(per_kind: int = 2000, seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    """(crops, sku): per_kind cartons of every type from the val split of dataset_hard_types, picked as
    `evaluate.py --types` picks them (sample_objects, seed 11, per_kind), cut with crop_unit. The crops are kept in
    data/cache as a .npy and come back as a memmap."""
    data = long_data()
    rows = data.sample_objects(data.load_objects(DATASET), "val", per_kind * len(KIND_TO_SKU), seed=seed, per_kind=True)
    sku = np.array([KIND_TO_SKU[r["kind"]] for r in rows])
    path = CACHE / f"synthetic_val_{per_kind}_{seed}.npy"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.stem + ".part.npy")
        crops = np.lib.format.open_memmap(part, mode="w+", dtype=np.uint8, shape=(len(rows), 384, 384, 3))
        by_image = {}
        for i, r in enumerate(rows):
            by_image.setdefault(r["image"], []).append(i)
        tasks = [(str(DATASET / "images" / "val" / name), [(rows[i]["x0"], rows[i]["y0"], rows[i]["x1"] - rows[i]["x0"],
                                                           rows[i]["y1"] - rows[i]["y0"]) for i in idx])
                 for name, idx in by_image.items()]
        with ProcessPoolExecutor(12, mp_context=multiprocessing.get_context("spawn")) as ex:    # no fork of a threaded process
            for idx, got in zip(by_image.values(), ex.map(_cut, tasks, chunksize=8)):
                for i, c in zip(idx, got):
                    crops[i] = c
        crops.flush()
        del crops
        part.rename(path)
    return np.load(path, mmap_mode="r"), sku


def synthetic_threshold(top1_pos: np.ndarray, keep: float = 0.99) -> float:
    """The similarity that `keep` of the true synthetic cartons reach."""
    return float(np.quantile(top1_pos, 1 - keep))
