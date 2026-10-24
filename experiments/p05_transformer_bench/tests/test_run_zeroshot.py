import csv

import numpy as np

from bench.run_zeroshot import answers, baseline_pred, pending_pairs
from bench.testset import Unit


def test_pairs_already_written_are_skipped(tmp_path):
    out = tmp_path / "zeroshot.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["encoder", "gallery", "acc"])
        w.writerow(["dinov2_s", "renders", "0.5"])
    assert pending_pairs(["dinov2_s"], ["renders", "iphone_all"], out) == [("dinov2_s", "iphone_all")]
    assert pending_pairs(["dinov2_s"], ["renders"], tmp_path / "missing.csv") == [("dinov2_s", "renders")]


def test_below_the_threshold_is_no_answer():
    a = answers(["u1", "u2", "u3"], np.array(["A", "B", None], object), np.array([0.9, 0.5, 0.95]), threshold=0.6)
    assert a == {"u1": "A", "u2": None, "u3": None}


def test_baselines_come_from_the_label_columns():
    u = Unit(uid="a", image="PHONE-S01-A_20261012_151910.jpg", capture_id="c", box=(0, 0, 20, 50), store="S01",
             label="TMP-MLK-TH-01", confidence="khá", yolo_sku="TMP-MLK-TH-02", db_old_sku=None, db_fixed_sku="TMP-MLK-TH-01")
    assert baseline_pred([u], "yolo") == {"a": "TMP-MLK-TH-02"}
    assert baseline_pred([u], "db_long") == {"a": None}
    assert baseline_pred([u], "db_greyfix") == {"a": "TMP-MLK-TH-01"}


def test_file_names_of_fine_tuned_encoders_are_plain():
    from bench.run_zeroshot import file_name
    assert file_name("ft:dinov2_s_holdout") == "ft_dinov2_s_holdout"
    assert file_name("dinov2_s") == "dinov2_s"


def test_synthetic_answers_are_counted_by_sku():
    from bench.run_zeroshot import by_sku
    counts = by_sku(np.array(["A", "A", "B"]), {0: "A", 1: None, 2: "A"})
    assert counts == {"A": (1, 2), "B": (0, 1)}


def test_retiming_rewrites_only_the_timing_of_that_encoder(tmp_path):
    from bench.run_zeroshot import COLUMNS, retime
    out = tmp_path / "zeroshot.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        w.writeheader()
        w.writerow(dict(encoder="ft:dinov2_s", gallery="renders", acc=0.9, ms_gpu=4.866, ms_cpu=28.6))
        w.writerow(dict(encoder="ft:dinov2_s", gallery="db", acc=0.8, ms_gpu=4.866, ms_cpu=28.6))
        w.writerow(dict(encoder="dinov2_s", gallery="renders", acc=0.2, ms_gpu=1.71, ms_cpu=28.4))
    retime(out, "ft:dinov2_s", 1.9, 27.0)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [(r["encoder"], r["gallery"], r["acc"], r["ms_gpu"], r["ms_cpu"]) for r in rows] == [
        ("ft:dinov2_s", "renders", "0.9", "1.9", "27.0"),
        ("ft:dinov2_s", "db", "0.8", "1.9", "27.0"),
        ("dinov2_s", "renders", "0.2", "1.71", "28.4")]
    assert list(rows[0]) == COLUMNS
