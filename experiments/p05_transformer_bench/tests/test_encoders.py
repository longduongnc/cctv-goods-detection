import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from bench import licenses
from bench.encoders import NAMES, make_encoder
from bench.testset import crop_unit, load_units, read_frame

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CROPS = np.random.default_rng(0).integers(0, 256, (4, 384, 384, 3), dtype=np.uint8)
HERE = Path(__file__).resolve().parents[1]
DATAGENT = HERE.parent


@pytest.mark.gpu
@pytest.mark.parametrize("name", NAMES)
def test_embed_gives_unit_vectors_that_repeat(name):
    enc = make_encoder(name, DEVICE)
    a, b = enc.embed(CROPS), enc.embed(CROPS)
    assert a.ndim == 2 and a.shape[0] == 4
    assert a.dtype == np.float32
    assert np.abs(np.linalg.norm(a, axis=1) - 1).max() <= 1e-3
    assert np.abs(a - b).max() < 1e-3


@pytest.mark.gpu
def test_long_ft_on_rgb_crops_equals_long_embedder_on_bgr_crops():
    """Bench crops are RGB; long's Embedder takes BGR and flips them itself. The wrapper must not flip again."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("long_embedder_check", DATAGENT / "carton_recognition" / "embedder.py")
    long_embedder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(long_embedder)
    units = load_units([HERE / "labels" / "th_labels_2026-10-24.csv"])[:8]
    sample = DATAGENT / "cv_output_sample"
    bgr = [long_embedder.crop_box(read_frame(sample, u.image), (u.box[0], u.box[1], u.box[0] + u.box[2], u.box[1] + u.box[3]))
           for u in units]
    rgb = np.stack([crop_unit(read_frame(sample, u.image), u.box, size=224) for u in units])
    theirs = long_embedder.Embedder(device=DEVICE, types=True).embed(bgr)
    ours = make_encoder("long_ft", DEVICE).embed(rgb)
    assert np.abs(ours - theirs).max() < 1e-3


def test_license_is_read_from_the_card_and_kept(tmp_path, monkeypatch):
    cache = tmp_path / "licenses.json"
    assert licenses.license_of("google/siglip2-base-patch16-224", cache) == "apache-2.0"

    def offline(*args, **kwargs):
        raise RuntimeError("no network")
    monkeypatch.setattr(licenses, "model_info", offline)
    assert licenses.license_of("google/siglip2-base-patch16-224", cache) == "apache-2.0"
