import pytest

from ingest.bandwidth import (image_mb_by_camera, images_gb_per_day, option_gb_per_day, passes_g1, table,
                              video_gb_per_day)
from ingest.sources import load_sources


def test_units():
    assert video_gb_per_day(2.0, 14.0) == pytest.approx(12.6)        # 2 Mbps × 14 giờ
    assert images_gb_per_day(56, 1.5) == pytest.approx(0.084)


def test_options():
    kw = dict(image_mb=1.5, video_mbps=2.0)
    assert option_gb_per_day("A", **kw) == pytest.approx(0.084)
    assert option_gb_per_day("B", **kw) == pytest.approx(12.6)
    assert option_gb_per_day("C", **kw) == pytest.approx(0.084)
    assert option_gb_per_day("D", **kw) == pytest.approx(0.02121)    # 14 ảnh + 14 × 30 dòng × 0,5 KB
    with pytest.raises(ValueError):
        option_gb_per_day("E", **kw)


def test_g1():
    assert passes_g1(2.0) and not passes_g1(2.01)


def test_image_mb_by_camera():
    rows = [dict(label="frames39", megapixels="2.0", mb_median="0.5", mb_p90="0.7"),
            dict(label="iphone", megapixels="8.0", mb_median="1.8", mb_p90="2.6"),
            dict(label="iphone", megapixels="24.0", mb_median="5.0", mb_p90="7.0")]
    mb = image_mb_by_camera(rows)
    assert mb["cam_2mp"] == (0.5, 0.7)
    assert mb["cam_4k_28"] == mb["cam_4k_40"] == (1.8, 2.6)
    assert mb["oak4s"] == (10.0, 10.0)                                  # giả định 10 MB của P03


def test_b_streams_at_the_bitrate_of_the_cameras_resolution(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("key,value,unit,source,checked_on,note\n"
                 + "".join(f"vendor.h265_{mp}_mbps_{end},{v},Mbps,t,2026-10-27,\n"
                           for mp, end, v in (("2mp", "low", 1), ("2mp", "high", 2), ("8mp", "low", 5), ("8mp", "high", 8))),
                 encoding="utf-8")
    jpeg = [dict(label="frames39", megapixels="2.0", mb_median="0.3", mb_p90="0.4"),
            dict(label="iphone", megapixels="8.0", mb_median="1.2", mb_p90="1.5")]
    b = {r["camera"]: r for r in table(load_sources(p), jpeg) if r["option"] == "B"}
    assert b["cam_2mp"]["gb_day_low"] == pytest.approx(video_gb_per_day(1.0), abs=1e-4)
    assert b["cam_2mp"]["gb_day_high"] == pytest.approx(video_gb_per_day(2.0), abs=1e-4)
    assert b["cam_4k_28"]["gb_day_high"] == pytest.approx(video_gb_per_day(8.0), abs=1e-4)
