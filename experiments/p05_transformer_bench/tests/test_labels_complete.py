import csv
from pathlib import Path

LABELS = Path(__file__).resolve().parents[1] / "labels"
SAMPLE_UNITS = Path.home() / "Desktop" / "Datagent" / "cv_output_sample" / "cv_output_units.csv"
RAW = {f"VNM-{i:02d}" for i in range(1, 11)} | {"CĐ", "ÍĐ", "TH-khác", "khác", "?", "x", "lệch"}
CONFIDENCE = {"chắc", "khá", "thấp", ""}


def _sample_keys(prefix):
    with open(SAMPLE_UNITS, encoding="utf-8-sig", newline="") as f:
        return sorted((u["capture_id"], u["bounding_box"]) for u in csv.DictReader(f) if u["detector_sku_id"].startswith(prefix))


def _rows(pattern):
    rows = []
    for path in sorted(LABELS.glob(pattern)):
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    return rows


def test_every_vinamilk_unit_has_exactly_one_label():
    keys = sorted((r["capture_id"], r["bounding_box"]) for r in _rows("vnm_labels_*.csv"))
    assert len(keys) == 331
    assert keys == _sample_keys("TMP-MLK-VNM")


def test_every_th_unit_has_exactly_one_label():
    keys = sorted((r["capture_id"], r["bounding_box"]) for r in _rows("th_labels_*.csv"))
    assert keys == _sample_keys("TMP-MLK-TH")


def test_vinamilk_labels_use_the_allowed_values():
    rows = _rows("vnm_labels_*.csv")
    assert rows
    assert {r["label"] for r in rows} <= RAW
    assert {r["confidence"] for r in rows} <= CONFIDENCE


def test_recheck_covers_at_least_33_units():
    assert len(_rows("vnm_recheck_*.csv")) >= 33
