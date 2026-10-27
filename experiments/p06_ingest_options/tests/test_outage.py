import pytest

from ingest.outage import buffer_gb, hours_until_full
from ingest.sources import load_sources


def test_hours_until_full():
    assert hours_until_full(128, 0.084) == pytest.approx(21333.33, rel=1e-4)
    assert hours_until_full(128, 12.6) == pytest.approx(142.22, rel=1e-4)
    assert hours_until_full(0, 0.084) == 0.0


def test_buffer_follows_decision_8(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("key,value,unit,source,checked_on,note\n"
                 "cam_2mp.sd_slot,0,u,t,2026-10-27,\n"
                 "cam_4k_28.sd_slot,1,u,t,2026-10-27,\n"
                 "box_n100.storage_gb,500,GB,t,2026-10-27,\n"
                 "oak4s.storage_gb,128,GB,t,2026-10-27,\n", encoding="utf-8")
    s = load_sources(p)
    assert buffer_gb("A", "cam_2mp", None, s) == 0.0          # camera không có khe thẻ
    assert buffer_gb("B", "cam_4k_28", None, s) == 128.0      # thẻ microSD 128 GB trong camera
    assert buffer_gb("C", "cam_4k_28", "box_n100", s) == 500.0
    assert buffer_gb("D", "oak4s", None, s) == 128.0
