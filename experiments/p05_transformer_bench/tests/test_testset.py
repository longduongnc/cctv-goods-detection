from pathlib import Path

import numpy as np

from bench.skus import TH_PAIR
from bench.testset import crop_unit, load_units, negatives, read_frame, scored

LABELS = Path(__file__).resolve().parents[1] / "labels"
TH = LABELS / "th_labels_2026-10-24.csv"
SAMPLE = Path.home() / "Desktop" / "Datagent" / "cv_output_sample"
BLUE_BGR, GREEN_BGR = (255, 0, 0), (0, 255, 0)


def test_th_labels_load_as_164_units():
    assert len(load_units([TH])) == 164


def test_store_comes_from_the_image_name():
    assert {u.store for u in load_units([TH])} == {"S01", "S02"}


def test_scored_keeps_the_37_confident_th_units():
    units = scored(load_units([TH]))
    assert len(units) == 37
    assert {u.label for u in units} <= set(TH_PAIR)


def test_negatives_are_the_16_units_that_are_not_th_180ml():
    assert len(negatives(load_units([TH]))) == 16


def test_read_frame_reads_a_sample_frame_as_bgr():
    frame = read_frame(SAMPLE, "PHONE-S01-A_20261012_151803.jpg")
    assert frame.shape == (1920, 1080, 3)


def _box_image():
    img = np.zeros((100, 200, 3), np.uint8)
    img[20:60, 10:30] = BLUE_BGR      # the box at x=10, y=20, w=20, h=40
    img[50:60, 10:30] = GREEN_BGR     # its bottom 10 rows
    return img


def test_crop_unit_returns_rgb_with_grey_bars():
    out = crop_unit(_box_image(), (10, 20, 20, 40), size=64)
    assert out.shape == (64, 64, 3)
    assert out[32, 32].tolist() == [0, 0, 255]
    assert out[32, 2].tolist() == [124, 124, 124]


def test_crop_unit_reads_the_box_as_x_y_w_h():
    out = crop_unit(_box_image(), (10, 20, 20, 40), size=64).astype(int)
    green = (out[..., 1] > 200) & (out[..., 0] < 60) & (out[..., 2] < 60)
    assert green.sum() > 0      # read as x0, y0, x1, y1 the crop would stop at row 40 and miss the green rows
