import numpy as np

from bench.skus import NAME_VI, SUA_HAT, TH_PAIR
from bench.testset import Unit
from bench.vlm import candidates_for, parse_answer, prompt, sku_from_ocr, upscale


def _unit(label, yolo_sku):
    return Unit(uid="a", image="PHONE-S01-A_20261012_151910.jpg", capture_id="c", box=(0, 0, 20, 50), store="S01",
                label=label, confidence="khá", yolo_sku=yolo_sku, db_old_sku=None, db_fixed_sku=None)


def test_candidates_come_from_yolo_never_from_the_label():
    assert candidates_for(_unit("TMP-MLK-TH-02", "TMP-MLK-VNM-03")) is None
    assert candidates_for(_unit("TMP-MLK-VNM-03", "TMP-MLK-TH-01")) == TH_PAIR
    assert candidates_for(_unit("TMP-MLK-TH-01", "TMP-MLK-VNM-08")) == SUA_HAT


def test_an_answer_is_matched_to_a_candidate_name_without_case_or_accents():
    assert parse_answer("th true milk sữa tươi tiệt trùng ít đường 180ml", TH_PAIR) == "TMP-MLK-TH-02"
    assert parse_answer("- TH true MILK Sữa Tươi Tiệt Trùng Có Đường 180ml.", TH_PAIR) == "TMP-MLK-TH-01"


def test_not_sure_or_a_name_outside_the_candidates_is_no_answer():
    assert parse_answer("KHÔNG CHẮC", TH_PAIR) is None
    assert parse_answer(NAME_VI["TMP-MLK-VNM-08"], TH_PAIR) is None


def test_ocr_keywords_name_the_sku_in_order():
    assert sku_from_ocr("SỮA HẠT ĐẬU NÀNH MÈ ĐEN", SUA_HAT) == "TMP-MLK-VNM-09"
    assert sku_from_ocr("SỮA ĐẬU NÀNH CAO CANXI", SUA_HAT) == "TMP-MLK-VNM-07"
    assert sku_from_ocr("TH true MILK ÍT ĐƯỜNG", TH_PAIR) == "TMP-MLK-TH-02"
    assert sku_from_ocr("TH true MILK ÍT ĐƯỜNG", SUA_HAT) is None
    assert sku_from_ocr("", TH_PAIR) is None


def test_the_prompt_lists_every_candidate_name_on_its_own_line():
    lines = prompt(TH_PAIR).splitlines()
    assert lines[0].startswith("Đây là ảnh cắt một hộp sữa")
    assert lines[1:] == [NAME_VI[c] for c in TH_PAIR]


def test_crops_are_enlarged_to_448_on_the_short_side():
    img = upscale(np.zeros((90, 40, 3), np.uint8))
    assert min(img.size) == 448
    assert img.size == (448, 1008)


def test_a_unit_left_without_answer_counts_as_wrong():
    from bench.run_vlm import summary
    rows = [dict(label="A", pred="A", ms=10.0), dict(label="B", pred=None, ms=30.0), dict(label="C", pred="B", ms=20.0)]
    s = summary("m", rows)
    assert (s["n"], s["answered"], s["right"]) == (3, 2, 1)
    assert s["acc"] == round(1 / 3, 4)
    assert s["right_of_answered"] == 0.5
    assert s["ms_per_crop"] == 20.0
