"""Decision by P06's rule, and results/summary.md from every CSV in results/.

    python -m ingest.report --results results --out results/summary.md

Rule (P06, fixed before the numbers): rank the combinations that pass G1–G3 by their 12-month total. `done` when the
cheapest C that passes costs at most 110% of the cheapest passing combination; `closed-fail` otherwise.
"""
import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from ingest.resolution import G3_DISTANCE_M, min_carton_cm

MAX_RATIO = 1.10
GATES = ("g1", "g2", "g3")
VARIANT = ("no_wifi_share", "plan4g", "cams_per_store", "processing")
OPTION = {"A": "A · camera tự gửi ảnh", "B": "B · đẩy video lên cloud", "C": "C · hộp lọc, cloud đếm",
          "D": "D · hộp đếm luôn"}
CAMERA = {"cam_2mp": "2 MP có sẵn", "cam_4k_28": "CCTV 4K, ống 2,8 mm", "cam_4k_40": "CCTV 4K, ống 4 mm",
          "oak4s": "OAK 4 S"}
BOX = {"box_rpi5": "Raspberry Pi 5", "box_n100": "mini PC N100", "box_orin": "Jetson Orin Nano Super", "": "—",
       "cloud": "cloud (ml.c5.xlarge)"}
PLAN = {"plan4g_sd100": "100.000 đ", "plan4g_report": "200.000 đ"}


@dataclass(frozen=True)
class Decision:
    status: str
    winner: dict
    best_c: dict | None
    ratio: float | None


def passes(row: dict) -> bool:
    return all(row[g] for g in GATES)


def decide(rows: list[dict]) -> Decision:
    """winner: cheapest base row passing G1–G3; best_c: cheapest such C; ratio: best_c ÷ winner (12-month totals)."""
    ok = sorted((r for r in rows if r["base"] and passes(r)), key=lambda r: r["total_12m_usd"])
    winner = ok[0] if ok else {}
    best_c = next((r for r in ok if r["option"] == "C"), None)
    ratio = best_c["total_12m_usd"] / winner["total_12m_usd"] if best_c else None
    return Decision("done" if best_c and ratio <= MAX_RATIO else "closed-fail", winner, best_c, ratio)


def gate_label(row: dict) -> str:
    failed = [g.upper() for g in GATES if not row[g]]
    return "trượt " + ", ".join(failed) if failed else "qua"


def robustness(rows: list[dict]) -> list[dict]:
    """The decision taken again inside each variant (WiFi share, 4G price, cameras per store, processing)."""
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in VARIANT), []).append(dict(r, base=True))
    out = []
    for key, group in sorted(groups.items(), key=lambda kv: str(kv[0])):
        d = decide(group)
        out.append(dict(zip(VARIANT, key), status=d.status, ratio=d.ratio, winner=d.winner))
    return out


def num(x: float, digits: int = 0) -> str:
    """Vietnamese number format: 12.345,6."""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")


def usd(x: float) -> str:
    return "$" + num(x)


def _cheapest_per_option_camera(rows: list[dict]) -> list[dict]:
    best = {}
    for r in rows:
        if r["base"]:
            key = (r["option"], r["camera"])
            if key not in best or r["total_12m_usd"] < best[key]["total_12m_usd"]:
                best[key] = r
    return sorted(best.values(), key=lambda r: r["total_12m_usd"])


def render_main_table(rows: list[dict]) -> str:
    """One line per option × camera (the cheapest box for C and D), failing combinations included."""
    lines = ["| Phương án | Camera | Hộp | Một lần (30 tiệm) | Mỗi tháng | Sau 12 tuần | Sau 12 tháng | Điều kiện |",
             "|---|---|---|---|---|---|---|---|"]
    for r in _cheapest_per_option_camera(rows):
        lines.append(f"| {OPTION.get(r['option'], r['option'])} | {CAMERA.get(r['camera'], r['camera'])} "
                     f"| {BOX.get(r['box'], r['box'])} | {usd(r.get('one_time_usd', 0))} | {usd(r.get('monthly_usd', 0))} "
                     f"| {usd(r.get('total_12w_usd', 0))} | {usd(r['total_12m_usd'])} | {gate_label(r)} |")
    return "\n".join(lines)


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_cost_rows(path: Path) -> list[dict]:
    rows = []
    for r in _read(path):
        r = dict(r)
        for k in ("cloud_usd", "one_time_usd", "monthly_usd", "total_12w_usd", "total_12m_usd", "no_wifi_share"):
            r[k] = float(r[k])
        r["cams_per_store"] = int(r["cams_per_store"])
        for k in GATES + ("base",):
            r[k] = r[k] == "True"
        rows.append(r)
    return rows


def _label(r: dict) -> str:
    return f"{r['option']}, {CAMERA[r['camera']]}" + (f", {BOX[r['box']]}" if r["box"] else "")


def hevc_cell(r: dict) -> str:
    """'có', 'không' or '—' (the cloud), marked when the source of the claim says it is unverified."""
    cell = {"1": "có", "0": "không", "": "—"}[r["hevc_hw"]]
    return cell + (" *(chưa kiểm chứng)*" if r.get("hevc_unverified") == "1" else "")


def render_decision(d: Decision) -> str:
    """The decision paragraph, worded for each outcome: C within the threshold, C over it, no C past the gates, nothing past them."""
    w, c = d.winner, d.best_c
    if not w:
        return f"**`{d.status}`.** Không tổ hợp nào qua cả G1–G3."
    cheapest = f"Tổ hợp rẻ nhất qua cả ba điều kiện là {_label(w)} với {usd(w['total_12m_usd'])}"
    if not c:
        return f"**`{d.status}`.** Không tổ hợp C nào qua cả G1–G3. {cheapest}."
    verdict = "trong" if d.ratio <= MAX_RATIO else "vượt"
    return (f"**`{d.status}`.** Tổ hợp C rẻ nhất qua cả G1–G3 là {_label(c)}: {usd(c['one_time_usd'])} trả một lần, "
            f"{usd(c['monthly_usd'])} mỗi tháng, {usd(c['total_12m_usd'])} sau 12 tháng "
            f"(mỗi tiệm {usd(c['one_time_usd'] / 30)} một lần và {usd(c['monthly_usd'] / 30)} mỗi tháng). "
            f"{cheapest}; C bằng {num(d.ratio * 100, 1)}% mức đó, {verdict} ngưỡng 110% của P06.")


def render_summary(results: Path) -> str:
    rows = load_cost_rows(results / "cost.csv")
    d = decide(rows)
    out = ["# HOANG-P06 — bảng tổng hợp", "",
           "Sinh tự động bằng `python -m ingest.report`. Tiền tính bằng USD, 30 tiệm. Trường hợp gốc: 1 camera mỗi tiệm, "
           "50% tiệm không có WiFi, 4G 200.000 đ/tháng, cloud đếm bằng CPU. Mọi giá có nguồn ở `inputs/sources.csv`.", "",
           "## 1. Quyết định", "", render_decision(d)]
    out += ["", "Trượt điều kiện: A và B gửi mặt người lên cloud (G2); B vượt gói 4G (G1); camera 2 MP có sẵn cho hộp "
            "dưới 60 px ở 2 m (G3).", "", "## 2. Bảng chính (trường hợp gốc)", "", render_main_table(rows), ""]

    rob = robustness(rows)
    same = sum(r["status"] == d.status for r in rob)
    out += ["## 3. Độ vững", "",
            f"Quyết định giữ nguyên `{d.status}` ở {same}/{len(rob)} biến thể "
            "(tỷ lệ tiệm không WiFi 0/50/100%, 4G 100.000 hoặc 200.000 đ, 1 hoặc 2 camera mỗi tiệm, cloud đếm bằng CPU "
            "hoặc GPU 30 giây/ảnh như P03).", ""]
    for proc, name in (("cpu", "Cloud đếm bằng CPU (đo được, model hiện tại)"), ("gpu_p03", "Cloud đếm bằng GPU 30 giây/ảnh (giả định của P03)")):
        group = [r for r in rob if r["processing"] == proc]
        done = sum(r["status"] == "done" for r in group)
        ratios = [r["ratio"] for r in group if r["ratio"]]
        spread = (f"C bằng {num(min(ratios) * 100, 1)}–{num(max(ratios) * 100, 1)}% tổ hợp rẻ nhất" if ratios
                  else "không tổ hợp C nào qua cả G1–G3")
        out.append(f"- **{name}:** `done` ở {done}/{len(group)} biến thể; {spread}.")
    out += ["", "Khi cloud phải đếm bằng GPU, khoản GPU (khoảng $180/tháng ở P03) làm C đắt hơn D, vì D đếm ngay trên hộp. "
            "Con số đó giả định hộp chỉ có CPU vẫn kịp đếm 14 ảnh mỗi ngày với model nặng như vậy *(chưa kiểm chứng)*. "
            "Với model hiện tại (0,48 giây/ảnh trên CPU, báo cáo 17/10), biến thể CPU mới sát thực tế.", "",
            "| Không WiFi | 4G/tháng | Camera/tiệm | Cloud đếm | Kết quả | C so với rẻ nhất | Rẻ nhất qua G1–G3 |",
            "|---|---|---|---|---|---|---|"]
    for r in rob:
        ratio = f"{num(r['ratio'] * 100, 1)}%" if r["ratio"] else "—"
        win = f"{_label(r['winner'])}: {usd(r['winner']['total_12m_usd'])}" if r["winner"] else "—"
        out.append(f"| {num(r['no_wifi_share'] * 100)}% | {PLAN[r['plan4g']]} | {r['cams_per_store']} "
                   f"| {'CPU' if r['processing'] == 'cpu' else 'GPU (P03)'} | `{r['status']}` | {ratio} | {win} |")

    res = _read(results / "resolution.csv")
    carton = res[0]["carton_cm"]
    out += ["", "## 4. Độ nét (E3) và dung lượng (E1)", "",
            f"Hộp 180 ml cao {num(float(carton), 1)} cm *(chưa kiểm chứng — chưa đo hộp thật)*. G3 xét ở 2 m.", "",
            "| Camera | px/cm ở 2 m | Hộp cao (px) ở 1,5 / 2 / 3 m | Bề ngang kệ phủ được ở 2 m | G3 |", "|---|---|---|---|---|"]
    for cam in CAMERA:
        rr = [r for r in res if r["camera"] == cam]
        two = next(r for r in rr if float(r["distance_m"]) == 2.0)
        heights = " / ".join(num(float(r["carton_px"])) for r in rr)
        out.append(f"| {CAMERA[cam]} | {num(float(two['px_per_cm']), 1)} | {heights} | {num(float(two['coverage_m']), 2)} m "
                   f"| {'qua' if two['g3'] == 'True' else 'trượt'} |")
    out += ["", "| Ảnh JPEG chất lượng 90 | Số ảnh | MB trung vị | MB p90 |", "|---|---|---|---|"]
    for r in _read(results / "bandwidth_jpeg.csv"):
        name = "39 khung ở tiệm" if r["label"] == "frames39" else "84 ảnh iPhone"
        skipped = f" (bỏ {r['n_skipped']} khung nhỏ hơn)" if int(r["n_skipped"]) else ""
        out.append(f"| {name}, {num(float(r['megapixels']))} MP | {r['n_images']}{skipped} | {num(float(r['mb_median']), 2)} "
                   f"| {num(float(r['mb_p90']), 2)} |")
    out += ["", "| Phương án | Camera | GB/ngày/tiệm (thấp–cao) | G1 (≤ 2 GB/ngày) | Căn cứ |", "|---|---|---|---|---|"]
    basis = {"measured": "đo", "vendor": "bitrate tham khảo từ diễn đàn và trang hướng dẫn *(chưa kiểm chứng)*",
             "p03": "giả định 10 MB của P03"}
    for r in _read(results / "bandwidth.csv"):
        low, high = float(r["gb_day_low"]), float(r["gb_day_high"])
        digits = 1 if low >= 1 else 3
        out.append(f"| {r['option']} | {CAMERA[r['camera']]} | {num(low, digits)}–{num(high, digits)} "
                   f"| {'qua' if r['g1'] == 'True' else 'trượt'} | {basis[r['basis']]} |")
    video = {}
    for r in _read(results / "bandwidth_video.csv"):
        video.setdefault((r["label"], r["codec"], r["crf"]), []).append(float(r["mbps"]))
    out += ["", "Video mã hoá lại ở 15 fps để đối chiếu (Mbps trung vị): " + "; ".join(
        f"{'MERL 640×472, camera cố định' if k[0] == 'merl' else 'iPhone 1080p, cầm tay'} {k[1]} CRF {k[2]}: "
        f"{num(sorted(v)[len(v) // 2], 2)}" for k, v in sorted(video.items())) + "."]

    out += ["", "## 5. Sức hộp (E2) — ước tính quy đổi *(chưa kiểm chứng trên hộp thật)*", "",
            "Đo trên 4 luồng CPU của máy long (39 khung), quy đổi theo điểm Geekbench 6 đơn luồng. Hộp tính như chỉ có CPU.", "",
            "| Nơi chạy | Lọc (ms/khung) | Đếm (ms/ảnh) | C: giây cho 60 khung mỗi mốc 15 phút | D: giây máy mỗi ngày "
            "| Giải mã HEVC phần cứng |", "|---|---|---|---|---|---|"]
    for r in _read(results / "edge_timing.csv"):
        out.append(f"| {BOX[r['target']]} | {num(float(r['filter_ms_frame']))} | {num(float(r['count_ms_image']))} "
                   f"| {num(float(r['c_s_per_mark']), 1)} | {num(float(r['d_s_per_day']))} | {hevc_cell(r)} |")

    out += ["", "## 6. Rớt mạng (E6)", "", "| Phương án | Camera | Bộ đệm | Chịu được (giờ mở cửa) |", "|---|---|---|---|"]
    seen = set()
    for r in _read(results / "outage.csv"):
        key = (r["option"], r["camera"])
        if key in seen:
            continue
        seen.add(key)
        hours = float(r["hours_until_full"])
        held = "mất ảnh ngay" if hours == 0 else (f"{num(hours)} giờ" if hours < 1000 else "trên 1.000 giờ")
        if hours and r["option"] in ("A", "B"):
            held += " *(chưa kiểm chứng: camera tự ghi vào thẻ khi rớt mạng và gửi bù khi có mạng lại)*"
        out.append(f"| {r['option']} | {CAMERA[r['camera']]} | {num(float(r['buffer_gb']))} GB | {held} |")

    out += ["", "## 7. Chỉ báo chọn ảnh (E4) — không dùng để quyết", ""]
    fs = _read(results / "frame_selection.csv")
    phone = {}
    for r in fs:
        if r["source"] == "phone":
            phone.setdefault(r["clip"], {"frames": r["frames"]})[r["metric"]] = float(r["value"])
    out += ["| Clip điện thoại | Khung | Hộp trung vị mỗi khung | Một khung ngẫu nhiên lệch (trung bình / p90) |", "|---|---|---|---|"]
    for clip, m in phone.items():
        out.append(f"| {clip[:16]} | {m['frames']} | {num(m['median_units'], 1)} | {num(m['mean'], 1)} / {num(m['p90'], 1)} |")
    merl = {}
    for r in fs:
        if r["source"] == "merl":
            merl.setdefault(r["clip"], {"frames": r["frames"]})[r["metric"]] = float(r["value"])
    out += ["", "| Clip MERL | Khung | Khung có người chồng vùng kệ | Đoạn sạch dài nhất |", "|---|---|---|---|"]
    for clip, m in merl.items():
        out.append(f"| {clip} | {m['frames']} | {num(m['occluded_share'] * 100)}% | {num(m['longest_clean_s'], 1)} giây |")

    wide = next(r for r in res if r["camera"] == "cam_4k_28" and float(r["distance_m"]) == G3_DISTANCE_M)
    out += ["", "## 8. Giới hạn", "",
            f"- Chiều cao hộp {num(float(carton), 1)} cm chưa đo. Camera 4K ống 2,8 mm ({num(float(wide['carton_px']))} px ở 2 m) "
            f"vẫn qua G3 nếu hộp cao từ {num(min_carton_cm(float(wide['px_per_cm'])), 2)} cm trở lên.",
            "- Thời gian trên hộp và trên cloud là quy đổi theo điểm Geekbench 6 đơn luồng, chưa đo trên thiết bị thật.",
            "- Bitrate video của B lấy từ diễn đàn người dùng và trang hướng dẫn, không phải từ hãng; B trượt G1 ở mọi "
            "bitrate trên 0,32 Mbps, nên kết luận về B không phụ thuộc con số này.",
            "- Clip điện thoại quay cầm tay; clip MERL trong repo là bản đã vẽ khung chú thích, độ phân giải 640×472. "
            "Chỉ báo E4 chỉ mang tính tham khảo.",
            "- Giá OAK 4 S theo P03 ($949): trang Luxonis không hiện giá ngày 27/10. Giá mini PC N100 lấy từ Newegg cộng VAT "
            "nhập khẩu 10%, chưa gồm vận chuyển.",
            "- Không tính công lắp đặt, bảo trì, gán nhãn (hoang chốt 27/10).", "",
            "## 9. Giả định", "",
            "Giá, thông số và nguồn: `inputs/sources.csv`. Các giả định của kế hoạch (trường hợp gốc, lấy mức giá cao, quy đổi "
            "CPU, `ml.c5.xlarge`, 12 tuần = 2,8 tháng, bộ đệm khi rớt mạng): mục \"Quyết định của kế hoạch\" trong "
            "`docs/superpowers/plans/2026-10-27-p06-ingest-options.md`. Mô hình cloud là `docs/architecture/cost_model.py` "
            "của P03, nạp nguyên vẹn."]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")                     # the labels are Vietnamese; Windows consoles default to cp1252
    args.out.write_text(render_summary(args.results), encoding="utf-8")
    d = decide(load_cost_rows(args.results / "cost.csv"))
    print(render_decision(d), "| ratio:", round(d.ratio, 4) if d.ratio else None)


if __name__ == "__main__":
    main()
