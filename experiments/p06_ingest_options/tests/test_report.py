import pytest

from ingest.report import decide, gate_label, render_main_table, robustness


def row(option, total, g1=True, g2=True, g3=True, camera="cam_4k_28", box="box_n100", **variant):
    return dict(option=option, camera=camera, box=box, total_12m_usd=total, g1=g1, g2=g2, g3=g3, base=True, **variant)


def test_c_cheapest_is_done():
    d = decide([row("C", 1000), row("D", 1100), row("A", 800, g2=False)])
    assert d.status == "done" and d.winner["option"] == "C" and d.ratio == pytest.approx(1.0)


def test_c_within_ten_percent_is_done():
    d = decide([row("C", 1050), row("D", 1000)])
    assert d.status == "done" and d.winner["option"] == "D" and d.ratio == pytest.approx(1.05)


def test_c_too_expensive_is_closed_fail():
    d = decide([row("C", 1200), row("D", 1000)])
    assert d.status == "closed-fail" and d.winner["option"] == "D"


def test_c_failing_a_gate_is_closed_fail():
    d = decide([row("C", 900, g3=False), row("D", 1000)])
    assert d.status == "closed-fail" and d.best_c is None


def test_gate_label_and_failing_rows_stay_in_the_table():
    assert gate_label(row("B", 1, g1=False, g2=False)) == "trượt G1, G2"
    assert gate_label(row("C", 1)) == "qua"
    assert "trượt G2" in render_main_table([row("A", 800, g2=False), row("C", 1000)])


def test_robustness_decides_each_variant_on_its_own_rows():
    v1 = dict(no_wifi_share=0.0, plan4g="plan4g_sd100", cams_per_store=1, processing="cpu")
    v2 = dict(no_wifi_share=1.0, plan4g="plan4g_sd100", cams_per_store=1, processing="cpu")
    rows = [row("C", 1000, **v1), row("D", 1100, **v1), row("C", 1300, **v2), row("D", 1000, **v2)]
    for r in rows:
        r["base"] = False                                   # biến thể không phải trường hợp gốc vẫn được xét
    status = {r["no_wifi_share"]: r["status"] for r in robustness(rows)}
    assert status == {0.0: "done", 1.0: "closed-fail"}
