import math

from bench.metrics import unit_report
from bench.testset import Unit


def _unit(uid, label, h=50):
    return Unit(uid=uid, image="PHONE-S01-A_20261012_151910.jpg", capture_id="c", box=(0, 0, 20, h), store="S01",
                label=label, confidence="khá", yolo_sku="", db_old_sku=None, db_fixed_sku=None)


def test_th_units_count_in_the_th_pair():
    r = unit_report([_unit("a", "TMP-MLK-TH-01"), _unit("b", "TMP-MLK-VNM-01")], {"a": "TMP-MLK-TH-01", "b": "TMP-MLK-VNM-01"})
    assert r["th_pair"][:2] == (1, 1)
    assert r["acc"][:2] == (2, 2)


def test_a_40_px_box_falls_in_40_to_60():
    r = unit_report([_unit("a", "TMP-MLK-VNM-07", h=40)], {"a": "TMP-MLK-VNM-07"})
    assert r["by_height"]["40–60"][:2] == (1, 1)
    assert r["by_height"]["<40"][:2] == (0, 0)
    assert math.isnan(r["by_height"]["<40"][2])
    assert r["sua_hat"][:2] == (1, 1)


def test_no_answer_counts_as_wrong():
    r = unit_report([_unit("a", "TMP-MLK-VNM-01"), _unit("b", "TMP-MLK-VNM-02")], {"a": None})
    assert r["acc"][:2] == (0, 2)


def test_negatives_left_unanswered_count_as_rejected():
    units = [_unit("a", "TMP-MLK-VNM-01"), _unit("n1", "NEG"), _unit("n2", "NEG")]
    r = unit_report(units, {"a": "TMP-MLK-VNM-01", "n1": None, "n2": "TMP-MLK-VNM-03"})
    assert r["neg_rejected"][:2] == (1, 2)
    assert r["acc"][:2] == (1, 1)
    assert "neg_rejected" not in unit_report(units[:1], {"a": "TMP-MLK-VNM-01"})
