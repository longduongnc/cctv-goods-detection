"""Naming a unit by its nearest gallery images, with the vote of carton_recognition/recognize.lookup."""
import numpy as np


def knn_predict(q: np.ndarray, g: np.ndarray, g_sku: np.ndarray, k: int = 10, chunk: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """(pred, top1) for unit vectors q against gallery g. Each of the k nearest votes for its SKU with its similarity
    (cut at 0); pred is the SKU with most votes, or None when the "none" votes are at least as many. top1 is the
    highest similarity to a gallery image that is not "none" among the k (-1 when there is none)."""
    k = min(k, len(g))
    pred, top1 = np.empty(len(q), object), np.full(len(q), -1.0)
    for start in range(0, len(q), chunk):
        sims = q[start:start + chunk] @ g.T
        near = np.argpartition(-sims, k - 1, axis=1)[:, :k]
        for row, (s, idx) in enumerate(zip(sims, near)):
            idx = idx[np.argsort(-s[idx], kind="stable")]           # nearest first, as lookup reads them
            votes = {}
            for sim, sku in zip(s[idx], g_sku[idx]):
                votes[sku] = votes.get(sku, 0.0) + max(float(sim), 0.0)
                if sku != "none":
                    top1[start + row] = max(top1[start + row], float(sim))
            cartons = {sku: v for sku, v in votes.items() if sku != "none"}
            best = max(cartons, key=cartons.get) if cartons else None
            pred[start + row] = best if best is not None and votes.get("none", 0.0) < cartons[best] else None
    return pred, top1
