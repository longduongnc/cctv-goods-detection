import cv2
import numpy as np
import pytest

from ingest.edge_filter import FrameInfo, configure_threads, overlaps, select_best, sharpness
from ingest.edge_timing import scale_ms, summarize
from ingest.sources import load_sources


def test_blur_lowers_sharpness():
    g = np.random.default_rng(0).integers(0, 256, (200, 200), dtype=np.uint8)
    assert sharpness(cv2.GaussianBlur(g, (0, 0), 3)) < sharpness(g)


def test_overlaps():
    roi = (0, 0, 100, 100)
    assert overlaps((10, 10, 30, 30), roi)
    assert not overlaps((200, 200, 220, 220), roi)
    assert not overlaps((98, 98, 198, 198), roi)       # 4/10.000 diện tích trong vùng kệ, dưới 5%


def test_select_best_skips_occluded_frames():
    assert select_best([FrameInfo(10.0, False), FrameInfo(30.0, True), FrameInfo(20.0, False)]) == 2
    assert select_best([FrameInfo(5.0, True)]) is None


def test_scale_ms():
    assert scale_ms(100.0, st_ref=4000.0, st_target=2000.0) == pytest.approx(200.0)


def test_summarize_scales_medians_by_cpu_score(tmp_path):
    lines = ["key,value,unit,source,checked_on,note"]
    for key, v in (("cpu_long.cpu_st", 3000), ("cpu_cloud.cpu_st", 1000), ("box_rpi5.cpu_st", 750),
                   ("box_n100.cpu_st", 1500), ("box_orin.cpu_st", 600),
                   ("box_rpi5.hevc_hw", 1), ("box_n100.hevc_hw", 1), ("box_orin.hevc_hw", 0)):
        lines.append(f"{key},{v},u,t,2026-10-27,")
    p = tmp_path / "s.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raw = [dict(image="a", step="filter", ms="10"), dict(image="b", step="filter", ms="30"),
           dict(image="c", step="filter", ms="20"), dict(image="a", step="count", ms="100")]
    out = {r["target"]: r for r in summarize(raw, load_sources(p))}
    assert out["box_rpi5"]["filter_ms_frame"] == pytest.approx(80.0)                 # trung vị 20 ms × 3000/750
    assert out["cloud"]["count_ms_image"] == pytest.approx(300.0)                    # 100 ms × 3000/1000
    assert out["box_n100"]["c_s_per_mark"] == pytest.approx(2.4)                     # 60 khung × 40 ms
    assert out["box_n100"]["d_s_per_day"] == pytest.approx(137.2)                    # (56 × 60 × 40 + 14 × 200) ms
    assert out["box_orin"]["hevc_hw"] == 0 and out["cloud"]["hevc_hw"] == ""


@pytest.mark.remote
def test_configure_threads_pins_four():                 # chạy dưới `taskset -c 0-3`
    import torch
    configure_threads(4)
    assert torch.get_num_threads() == 4 and cv2.getNumThreads() == 4
