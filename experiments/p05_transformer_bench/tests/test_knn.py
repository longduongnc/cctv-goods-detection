import numpy as np
import pytest

from bench.knn import knn_predict

E1 = np.array([1.0, 0.0], np.float32)
E2 = np.array([0.0, 1.0], np.float32)
GALLERY = np.stack([E1, E2, E2])
SKU = np.array(["A", "B", "B"])


def test_query_on_a_stored_vector_gets_its_sku():
    pred, top1 = knn_predict(E2[None], GALLERY, SKU)
    assert pred[0] == "B"
    assert top1[0] == pytest.approx(1.0)


def test_votes_add_up_by_similarity():
    pred, _ = knn_predict(((E1 + E2) / np.sqrt(2))[None].astype(np.float32), GALLERY, SKU, k=3)
    assert pred[0] == "B"


def test_none_votes_reject_the_query():
    far = np.array([0.6, 0.8], np.float32)                   # cosine 0.6 with E1
    pred, top1 = knn_predict(E1[None], np.stack([E1, E1, far]), np.array(["none", "none", "A"]))
    assert pred[0] is None
    assert top1[0] == pytest.approx(0.6)


def test_many_queries_in_chunks_match_one_by_one():
    rng = np.random.default_rng(0)
    g = rng.normal(size=(50, 8)).astype(np.float32)
    g /= np.linalg.norm(g, axis=1, keepdims=True)
    q = rng.normal(size=(30, 8)).astype(np.float32)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    sku = np.array(["none", "A", "B", "C", "D"] * 10)
    pred, top1 = knn_predict(q, g, sku, chunk=7)
    for i in range(len(q)):
        p, t = knn_predict(q[i:i + 1], g, sku)
        assert pred[i] == p[0]
        assert top1[i] == pytest.approx(t[0])
