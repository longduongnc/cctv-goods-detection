import csv
import shutil
from pathlib import Path

import pytest

from ingest.report import decide, gate_label, hevc_cell, render_main_table, render_summary, robustness

RESULTS = Path(__file__).resolve().parents[1] / "results"


def row(option, total, g1=True, g2=True, g3=True, camera="cam_4k_28", box="box_n100", **variant):
    return dict(option=option, camera=camera, box=box, total_12m_usd=total, g1=g1, g2=g2, g3=g3, base=True, **variant)


def summary_with(tmp_path, change=lambda r: r):
    """render_summary trên bản chép của results/, mỗi dòng cost.csv đã qua change(dòng)."""
    for f in RESULTS.glob("*.csv"):
        shutil.copy(f, tmp_path / f.name)
    with open(RESULTS / "cost.csv", encoding="utf-8") as f:
        rows = [change(r) for r in csv.DictReader(f)]
    with open(tmp_path / "cost.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return render_summary(tmp_path)


def section(text, title):
    """Phần chữ dưới một tiêu đề '## '."""
    return text.split(f"## {title}")[1].split("\n## ")[0]


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


def test_summary_says_c_is_over_the_threshold_when_it_is(tmp_path):
    dearer = lambda r: dict(r, total_12m_usd=str(float(r["total_12m_usd"]) * 1.5)) if r["option"] == "C" else r
    decision = section(summary_with(tmp_path, dearer), "1. Quyết định")
    assert "`closed-fail`" in decision and "vượt ngưỡng 110%" in decision and "trong ngưỡng" not in decision


def test_summary_when_no_c_passes_the_gates(tmp_path):
    text = summary_with(tmp_path, lambda r: dict(r, g3="False") if r["option"] == "C" else r)
    assert "`closed-fail`" in section(text, "1. Quyết định")
    assert "Không tổ hợp C nào qua cả G1–G3" in section(text, "1. Quyết định")
    assert "không tổ hợp C nào qua cả G1–G3" in section(text, "3. Độ vững")


def test_summary_when_no_combination_passes(tmp_path):
    text = summary_with(tmp_path, lambda r: dict(r, g2="False"))
    assert "Không tổ hợp nào qua cả G1–G3" in section(text, "1. Quyết định")


def test_hevc_cell_carries_the_unverified_mark():
    assert hevc_cell(dict(hevc_hw="1", hevc_unverified="1")) == "có *(chưa kiểm chứng)*"
    assert hevc_cell(dict(hevc_hw="1", hevc_unverified="0")) == "có"
    assert hevc_cell(dict(hevc_hw="", hevc_unverified="")) == "—"                    # cloud


def test_summary_marks_camera_buffering_unverified():
    outage = section(render_summary(RESULTS), "6. Rớt mạng")
    assert "chưa kiểm chứng" in outage


def test_summary_does_not_call_forum_bitrates_the_makers():
    assert "nhà sản xuất" not in render_summary(RESULTS)
