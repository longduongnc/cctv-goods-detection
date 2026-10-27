"""What the box at the store does around each 15-minute mark in option C: leave out frames where a person covers the
shelf, blur faces, keep the sharpest frame. Timed on long's machine (E2) and used to count covered frames (E4)."""
import os
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FrameInfo:
    sharpness: float
    person_on_shelf: bool


def sharpness(gray: np.ndarray) -> float:
    """Variance of the Laplacian: higher is sharper."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def overlaps(box_xyxy, roi_xywh, min_frac: float = 0.05) -> bool:
    """True when at least min_frac of the person box lies inside the shelf region."""
    x0, y0, x1, y1 = box_xyxy
    rx, ry, rw, rh = roi_xywh
    inter_w = max(0.0, min(x1, rx + rw) - max(x0, rx))
    inter_h = max(0.0, min(y1, ry + rh) - max(y0, ry))
    area = max(x1 - x0, 0) * max(y1 - y0, 0)
    return area > 0 and inter_w * inter_h / area >= min_frac


def select_best(frames: list[FrameInfo]) -> int | None:
    """Index of the sharpest frame with no person on the shelf; None when every frame is covered."""
    clean = [i for i, f in enumerate(frames) if not f.person_on_shelf]
    return max(clean, key=lambda i: frames[i].sharpness) if clean else None


def blur_faces(image_bgr: np.ndarray, detector) -> int:
    """Blur, in place, every face OpenCV's YuNet detector finds; returns how many."""
    h, w = image_bgr.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(image_bgr)
    if faces is None:
        return 0
    for x, y, fw, fh in faces[:, :4].astype(int):
        xa, ya, xb, yb = max(x, 0), max(y, 0), min(x + fw, w), min(y + fh, h)
        if xb - xa > 1 and yb - ya > 1:
            image_bgr[ya:yb, xa:xb] = cv2.GaussianBlur(image_bgr[ya:yb, xa:xb], (0, 0), max((xb - xa) / 6, 3))
    return len(faces)


def configure_threads(n: int) -> None:
    """Hold torch and OpenCV to n threads, and refuse to go on unless the process is pinned to n CPUs, so that the
    timing is for a 4-core box and not for all 48 threads of long's machine."""
    import torch
    torch.set_num_threads(n)
    cv2.setNumThreads(n)
    cpus = len(os.sched_getaffinity(0))
    if cpus != n:
        raise RuntimeError(f"this process may use {cpus} CPUs, not {n}: start it under `taskset -c 0-{n - 1}`")
