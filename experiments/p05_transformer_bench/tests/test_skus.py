import ast
from pathlib import Path

import pytest

from bench import skus

CV_OUTPUT = Path.home() / "Desktop" / "Datagent" / "carton_recognition" / "cv_output.py"


def _skus_literal():
    """The SKUS table of long's cv_output.py, read without importing the file."""
    tree = ast.parse(CV_OUTPUT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SKUS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("SKUS not found in cv_output.py")


def test_kind_to_sku_matches_cv_output():
    assert skus.KIND_TO_SKU == {kind: row[0] for kind, row in _skus_literal().items()}


def test_names_match_cv_output():
    assert skus.NAME_VI == {row[0]: row[1] for row in _skus_literal().values()}


def test_sku_codes_in_order():
    assert skus.SKU_CODES == tuple(f"TMP-MLK-VNM-{i:02d}" for i in range(1, 11)) + ("TMP-MLK-TH-01", "TMP-MLK-TH-02")


def test_groups():
    assert skus.TH_PAIR == ("TMP-MLK-TH-01", "TMP-MLK-TH-02")
    assert skus.SUA_HAT == ("TMP-MLK-VNM-07", "TMP-MLK-VNM-08", "TMP-MLK-VNM-09", "TMP-MLK-VNM-10")
    assert skus.HOLDOUT == ("TMP-MLK-TH-02", "TMP-MLK-VNM-09", "TMP-MLK-VNM-05")
    assert skus.HILO == "TMP-MLK-TH-HILO"


@pytest.mark.parametrize("raw, expected", [
    ("CĐ", "TMP-MLK-TH-01"),
    ("ÍĐ", "TMP-MLK-TH-02"),
    ("VNM-09", "TMP-MLK-VNM-09"),
    ("TMP-MLK-VNM-05", "TMP-MLK-VNM-05"),
    ("TH-khác", "NEG"),
    ("khác", "NEG"),
    ("?", "AMBIG"),
    ("x", "SKIP"),
    ("lệch", "SKIP"),
])
def test_normalize_label(raw, expected):
    assert skus.normalize_label(raw) == expected


def test_normalize_label_rejects_unknown_values():
    with pytest.raises(ValueError):
        skus.normalize_label("VNM-11")
