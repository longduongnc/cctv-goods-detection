from pathlib import Path

import pytest

from ingest.costs import (Combo, cloud_monthly_usd, cloud_timing, electricity_monthly_usd, fourg_monthly_usd, load_p03,
                          monthly_usd, one_time_usd, p03_breakdown, router_one_time_usd, totals)
from ingest.sources import load_sources

REPO = Path(__file__).resolve().parents[3]


def sources_from(tmp_path, pairs):
    p = tmp_path / "s.csv"
    p.write_text("key,value,unit,source,checked_on,note\n"
                 + "".join(f"{k},{v},{'VND' if k.endswith('.price_vnd') else 'u'},t,2026-10-27,\n" for k, v in pairs),
                 encoding="utf-8")
    return load_sources(p)


@pytest.fixture
def p03():
    return load_p03(REPO)


@pytest.fixture
def aws(tmp_path):
    return sources_from(tmp_path, [("aws.sm_async_cpu_h", 0.2), ("aws.kvs_in_gb", 0.010965),
                                   ("aws.kvs_store_gbmo", 0.025), ("aws.kvs_getimages_img", 0.000018),
                                   ("aws.kvs_getimages_img_lowres", 0.00001),
                                   ("cam_2mp.h_pixels", 1920), ("cam_4k_28.h_pixels", 3840)])


@pytest.fixture
def shop(tmp_path):
    return sources_from(tmp_path, [
        ("fx.vnd_per_usd", 25_000), ("power.vnd_per_kwh", 3_000), ("plan4g_report.price_vnd_month", 200_000),
        ("router4g.price_vnd", 1_000_000), ("microsd128.price_vnd", 250_000), ("poe_injector.price_vnd", 500_000),
        ("cam_2mp.sd_slot", 0), ("cam_2mp.power_w", 6.5),
        ("cam_4k_28.price_vnd", 2_500_000), ("cam_4k_28.sd_slot", 1), ("cam_4k_28.power_w", 7.2),
        ("oak4s.price_usd", 949), ("oak4s.power_w", 25),
        ("box_n100.price_vnd", 5_000_000), ("box_n100.power_w", 25), ("box_rpi5.price_vnd", 7_500_000),
        ("box_rpi5.power_w", 8.8)])


def test_totals():
    assert totals(1000.0, 100.0) == pytest.approx((1280.0, 2200.0))


def test_4g_and_router_only_for_stores_without_wifi():
    assert fourg_monthly_usd(30, 0.5, 200_000, 25_000) == pytest.approx(120.0)
    assert fourg_monthly_usd(30, 0.0, 200_000, 25_000) == 0.0
    assert router_one_time_usd(30, 0.5, 990_000, 25_000) == pytest.approx(594.0)


def test_electricity():
    assert electricity_monthly_usd(10.0, 30, 3_000, 25_000) == pytest.approx(25.92)


def test_p03_baseline_is_reproduced(p03):
    assert p03.total(p03_breakdown(p03, 1, {})) == pytest.approx(443.96, abs=0.01)
    assert p03.total(p03_breakdown(p03, 2, {})) == pytest.approx(651.04, abs=0.01)
    assert p03.A == p03.ASSUMPTIONS                       # trả lại giả định của P03 sau khi tính


def test_cloud_order_by_option(p03, aws):
    t = {"filter_ms_cloud": 200.0, "count_ms_cloud": 1000.0}
    cost = lambda o, video: cloud_monthly_usd(o, 1, "cpu", p03, aws, image_mb=1.5, video_gb_day=video, timing=t,
                                              camera="cam_4k_28")
    assert cost("D", 0.0) < cost("C", 0.0) < cost("B", 12.6)


def test_b_takes_frames_at_the_price_for_the_cameras_resolution(p03, aws):
    t = {"filter_ms_cloud": 200.0, "count_ms_cloud": 1000.0}
    cost = lambda cam: cloud_monthly_usd("B", 1, "cpu", p03, aws, image_mb=1.5, video_gb_day=12.6, timing=t, camera=cam)
    assert cost("cam_4k_28") - cost("cam_2mp") == pytest.approx(30 * 56 * 60 * 30 * (0.000018 - 0.00001))   # trên / tới 1080p


def test_one_time_counts_cameras_per_store_and_one_box_per_store(shop):
    c = Combo("C", "cam_4k_28", "box_n100", 0.5, "plan4g_report", 2, "cpu")
    assert one_time_usd(c, shop) == pytest.approx(30 * 2 * (100 + 20) + 30 * 200 + 15 * 40)   # camera + PoE, hộp, router
    a = Combo("A", "cam_4k_28", None, 0.0, "plan4g_report", 1, "cpu")
    assert one_time_usd(a, shop) == pytest.approx(30 * (100 + 20 + 10))                      # camera + PoE + thẻ 128 GB
    d = Combo("D", "oak4s", None, 1.0, "plan4g_report", 1, "cpu")
    assert one_time_usd(d, shop) == pytest.approx(30 * (949 + 20) + 30 * 40)


def test_the_stores_own_2mp_camera_needs_no_new_power_supply(shop):
    c = Combo("C", "cam_2mp", "box_rpi5", 0.0, "plan4g_report", 1, "cpu")
    assert one_time_usd(c, shop) == pytest.approx(30 * 300)                                  # chỉ có hộp


def test_monthly_adds_4g_and_power_but_not_an_existing_cameras_power(shop):
    c = Combo("C", "cam_4k_28", "box_n100", 0.5, "plan4g_report", 1, "cpu")
    assert monthly_usd(c, shop, cloud_usd=100.0) == pytest.approx(100 + 120 + electricity_monthly_usd(32.2, 30, 3_000, 25_000))
    old = Combo("C", "cam_2mp", "box_rpi5", 0.0, "plan4g_report", 1, "cpu")                 # camera 2 MP đã chạy sẵn
    assert monthly_usd(old, shop, cloud_usd=0.0) == pytest.approx(electricity_monthly_usd(8.8, 30, 3_000, 25_000))


def test_cloud_timing_follows_the_cameras_frame_size():
    rows = [dict(megapixels="2.0736", target="cloud", filter_ms_frame="100", count_ms_image="1000"),
            dict(megapixels="8.2944", target="cloud", filter_ms_frame="400", count_ms_image="1100"),
            dict(megapixels="8.2944", target="box_rpi5", filter_ms_frame="900", count_ms_image="3000")]
    assert cloud_timing(rows, "cam_2mp") == dict(filter_ms_cloud=100.0, count_ms_cloud=1000.0)
    assert cloud_timing(rows, "cam_4k_28") == cloud_timing(rows, "oak4s") == dict(filter_ms_cloud=400.0, count_ms_cloud=1100.0)
