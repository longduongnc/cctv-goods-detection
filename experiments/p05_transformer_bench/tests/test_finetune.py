import numpy as np
import pytest
import torch

from bench import finetune, gallery
from bench.encoders import make_encoder
from bench.skus import HOLDOUT, KIND_TO_SKU

RNG = np.random.default_rng(0)
FAKE = (RNG.integers(0, 256, (16, 224, 224, 3), dtype=np.uint8), ["vinamilk_banana", "th_true_milk_sweetened"] * 8)


def _unit_vectors(path, device):
    v = make_encoder(f"ft:{path}", device).embed(RNG.integers(0, 256, (3, 384, 384, 3), dtype=np.uint8))
    assert v.shape == (3, 256)
    assert np.abs(np.linalg.norm(v, axis=1) - 1).max() < 1e-3


def test_smoke_train_on_cpu_gives_a_checkpoint_that_embeds(tmp_path):
    path = finetune.train("vit_tiny_patch16_224", (), epochs=1, out_dir=tmp_path, device="cpu", _fake_rows=FAKE)
    state = torch.load(path, map_location="cpu")
    assert state["backbone_kind"] == "timm"
    assert state["epochs"] == 1
    _unit_vectors(path, "cpu")


@pytest.mark.gpu
def test_smoke_train_of_a_hugging_face_backbone(tmp_path):
    path = finetune.train("google/siglip2-base-patch16-224", (), epochs=1, out_dir=tmp_path, device="cuda", _fake_rows=FAKE)
    assert torch.load(path, map_location="cpu")["backbone_kind"] == "hf"
    _unit_vectors(path, "cuda")


def test_training_rows_leave_out_the_holdout_skus():
    rows = [dict(kind=k) for k in list(KIND_TO_SKU) + ["background", "other_carton"]]
    kept = finetune.training_rows(rows, HOLDOUT)
    assert not any(KIND_TO_SKU.get(r["kind"]) in HOLDOUT for r in kept)
    assert len(kept) == len(rows) - len(HOLDOUT)


def test_db_gallery_without_holdout_dataset_crops_keeps_their_references():
    g = gallery.db_gallery(HOLDOUT, crops=48, background=4, others=4, references=2)
    held = np.isin(g.sku, HOLDOUT)
    assert not np.any(held & (g.source == "dataset"))
    assert set(g.sku[held & (g.source == "reference")]) == set(HOLDOUT)
    full = gallery.db_gallery((), crops=48, background=4, others=4, references=2)
    assert np.any(np.isin(full.sku, HOLDOUT) & (full.source == "dataset"))
    assert set(full.sku[np.isin(full.source, ["background", "other_carton"])]) == {"none"}
