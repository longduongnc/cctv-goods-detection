import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from bench import gallery
from bench.skus import HILO, SKU_CODES

LABELS = Path(__file__).resolve().parents[1] / "labels"
LONG_CODE = Path.home() / "Desktop" / "Datagent" / "carton_recognition"


def _csv(name):
    with open(LABELS / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _blue_minus_red(crop):
    centre = crop[150:234, 150:234].reshape(-1, 3).astype(float).mean(0)
    return centre[2] - centre[0]


@pytest.fixture
def long_data(monkeypatch):
    """long's carton_recognition/data.py, imported without writing caches there or leaving it in sys.modules."""
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.syspath_prepend(str(LONG_CODE))
    saved = {n: sys.modules.pop(n) for n in ("data", "embedder") if n in sys.modules}
    import data
    yield data
    for n in ("data", "embedder"):
        sys.modules.pop(n, None)
    sys.modules.update(saved)


def test_render_gallery_has_every_sku_at_crop_size():
    g = gallery.render_gallery(per_kind=2)
    assert g.crops.shape == (24, 384, 384, 3)
    assert g.crops.dtype == np.uint8
    assert sorted(set(g.sku)) == sorted(SKU_CODES)
    assert set(g.source) == {"reference"}


def test_render_poses_match_reference_views_of_long(long_data):
    rows, _ = long_data.reference_views(per_kind=10)
    ours = [(kind, round(yaw, 1), round(pitch, 1), round(roll, 1), lying)
            for kind, yaw, pitch, roll, lying, *_ in gallery.reference_poses(per_kind=10)]
    assert ours == [(r["kind"], r["yaw"], r["pitch"], r["roll"], r["lying"]) for r in rows]


def test_render_crops_are_rgb():
    g = gallery.render_gallery(per_kind=1)
    assert _blue_minus_red(g.crops[list(g.sku).index("TMP-MLK-VNM-02")]) > 30


def test_iphone_photo_table():
    rows = _csv("iphone_photos.csv")
    assert len(rows) == 84
    assert len({r["sku"] for r in rows}) == 13
    fronts = Counter(r["sku"] for r in rows if r["face"] == "front" and r["split"] == "gallery")
    assert fronts == Counter(SKU_CODES + (HILO,))
    assert {r["face"] for r in rows} == {"front", "back", "left", "right", "top", "bottom"}
    assert sorted(r["photo"] for r in rows if r["split"] == "query") == [f"IMG_{n:04d}.jpeg" for n in range(703, 709)]


def test_every_photo_has_one_box():
    boxes = _csv("iphone_boxes.csv")
    assert sorted(b["photo"] for b in boxes) == sorted(r["photo"] for r in _csv("iphone_photos.csv"))
    assert {b["method"] for b in boxes} <= {"yolo", "center", "manual"}


def test_iphone_front_gallery():
    assert len(gallery.iphone_gallery({"front"}, include_hilo=False).sku) == 12
    g = gallery.iphone_gallery({"front"}, include_hilo=True)
    assert g.crops.shape == (13, 384, 384, 3)
    assert sorted(g.sku) == sorted(SKU_CODES + (HILO,))
    assert _blue_minus_red(g.crops[list(g.sku).index("TMP-MLK-VNM-02")]) > 30


def test_iphone_side_faces_stand_upright():
    g = gallery.iphone_gallery(None, include_hilo=True)
    faces = {r["photo"]: r["face"] for r in _csv("iphone_photos.csv")}
    for crop, source in zip(g.crops, g.source):
        if faces[source.split("/")[1]] in ("front", "back", "left", "right"):
            rows, cols = np.nonzero((crop != 124).any(axis=2))
            assert np.ptp(rows) > np.ptp(cols), source


def test_iphone_all_faces_and_hilo_queries():
    assert len(gallery.iphone_gallery(None, include_hilo=False).sku) == 72
    g = gallery.iphone_gallery(None, include_hilo=True)
    assert len(g.sku) == 78
    assert not any(s.endswith(f"IMG_{n:04d}.jpeg") for s in g.source for n in range(703, 709))
    q = gallery.hilo_queries()
    assert q.crops.shape == (6, 384, 384, 3)
    assert set(q.sku) == {HILO}


@pytest.mark.parametrize("suffix", [".npz", ".npy"])
def test_save_and_load_keep_everything(tmp_path, suffix):
    crops = (np.arange(2 * 384 * 384 * 3) % 251).astype(np.uint8).reshape(2, 384, 384, 3)
    g = gallery.Gallery("t", crops, np.array(["TMP-MLK-VNM-01", "none"]), np.array(["reference", "background"]))
    gallery.save_gallery(g, tmp_path / f"g{suffix}")
    h = gallery.load_gallery(tmp_path / f"g{suffix}")
    assert h.name == "t"
    np.testing.assert_array_equal(h.crops, crops)
    assert list(h.sku) == ["TMP-MLK-VNM-01", "none"]
    assert list(h.source) == ["reference", "background"]
    if suffix == ".npy":
        assert isinstance(h.crops, np.memmap)
