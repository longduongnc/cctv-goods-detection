from collections import Counter

import numpy as np
import pytest

from bench.calibrate import synthetic_threshold, synthetic_val
from bench.skus import SKU_CODES


def test_threshold_keeps_99_percent_of_true_cartons():
    assert synthetic_threshold(np.linspace(0, 1, 101)) == pytest.approx(0.01)


def test_synthetic_val_takes_the_same_number_of_every_type():
    crops, sku = synthetic_val(per_kind=2)
    assert crops.shape == (24, 384, 384, 3)
    assert crops.dtype == np.uint8
    assert Counter(sku) == Counter({code: 2 for code in SKU_CODES})
