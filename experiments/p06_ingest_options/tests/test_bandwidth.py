import pytest

from ingest.bandwidth import image_mb_by_camera, images_gb_per_day, option_gb_per_day, passes_g1, video_gb_per_day


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
