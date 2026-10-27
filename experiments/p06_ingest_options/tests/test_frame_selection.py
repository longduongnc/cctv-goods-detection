from collections import Counter

import pytest

import json

from ingest.frame_selection import (clip_files, counts_per_frame, deviation, median_counts, occlusion_stats,
                                    random_frame_deviation)


def unit(t):
    return {"yolo_type": t}


def test_counts_and_deviation():
    frames = {"0": [unit("a")] * 2, "10": [unit("a")] * 5, "2": [unit("a")] * 2 + [unit("b")]}
    counts = counts_per_frame(frames)
    assert counts == [Counter(a=2), Counter(a=2, b=1), Counter(a=5)]      # khung 0, 2, 10
    med = median_counts(counts)
    assert med == {"a": 2.0, "b": 0.0}
    assert [deviation(c, med) for c in counts] == [0.0, 1.0, 3.0]


def test_random_frame_deviation():
    counts = [Counter(a=2), Counter(a=2), Counter(a=5)]                   # độ lệch 0, 0, 3
    s = random_frame_deviation(counts, n=3000, seed=0)
    assert s["mean"] == pytest.approx(1.0, abs=0.15)
    assert (s["p50"], s["p90"]) == (0.0, 3.0)


def test_clip_files_skip_the_summary_list(tmp_path):
    (tmp_path / "IMG_0798.json").write_text(json.dumps({"summary": {}, "frames": {"0": []}}), encoding="utf-8")
    (tmp_path / "summary.json").write_text(json.dumps([{"video": "IMG_0798.MOV"}]), encoding="utf-8")
    assert [p.name for p in clip_files(tmp_path)] == ["IMG_0798.json"]


def test_occlusion_stats():
    s = occlusion_stats([False, False, True, True, False, False, False], fps=1.0)
    assert (s["frames"], s["occluded"]) == (7, 2)
    assert s["longest_clean_s"] == pytest.approx(3.0)
