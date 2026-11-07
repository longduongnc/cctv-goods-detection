"""Chi phí AWS giai đoạn đầu (HOANG-P07): vài tiệm, CCTV 4K, hộp lọc tại tiệm, cloud đếm bằng CPU.

Tính lại từ mô hình của P03 (docs/architecture/cost_model.py) và số đo của P06 (experiments/p06_ingest_options),
chỉ đọc, không sửa hai nguồn đó. Giá giữ nguyên theo hai nguồn đó; giả định riêng của giai đoạn đầu nằm trong PHASE1.
Đây là ước tính, chưa đo trên AWS.

Chạy: python docs/architecture/cost_phase1.py --stores 4 [--budget USD]
Repo public nên số ngân sách không ghi ở đây: truyền bằng --budget lúc chạy.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
P06 = REPO / "experiments" / "p06_ingest_options"
sys.path.insert(0, str(P06))

from ingest import costs  # noqa: E402
from ingest.sources import load_sources, value  # noqa: E402

CAMERA = "cam_4k_28"
BOX = "box_n100"
DATA_GROUPS = ("1 Thu nhận", "2 Xử lý", "3 Kết quả", "4 Lưu trữ")
HOANG_CUT = ("GuardDuty (log)", "Security Hub (5 tài khoản)", "Config")  # bản draw.io hoang sửa ngày 24/10 đã bỏ ba dịch vụ này

# Giả định riêng của giai đoạn đầu (chưa kiểm chứng; đổi ở đây rồi chạy lại).
PHASE1 = {
    "cvat_hours": 40,       # CVAT chỉ bật khi có ảnh cần gán nhãn (P03: 176 giờ/tháng)
    "train_gpu_hours": 20,  # như P03: 2 lần × 10 giờ, chưa đo
    "web_users": 10,        # P03: 30
    "web_requests": 20_000,  # P03: 200.000
    "egress_gb": 5,         # P03: 50
    "waf_rules": 5,         # như P03
    "kms_keys": 6,          # 3 khoá + 3 bản sao Osaka (P03: 12)
    "kms_requests": 200_000,  # P03: 1.000.000
    "secrets": 2,           # P03: 3
    "cw_log_gb": 5,         # P03: 20
    "cw_metrics": 30,       # P03: 100
    "cw_alarms": 10,        # P03: 20
}


@dataclass
class Context:
    costs: ModuleType
    p03: ModuleType
    sources: dict
    bandwidth: dict
    timing: dict


def load_context() -> Context:
    results = P06 / "results"
    return Context(costs=costs, p03=costs.load_p03(REPO), sources=load_sources(P06 / "inputs" / "sources.csv"),
                   bandwidth={(r["option"], r["camera"]): r for r in costs._read(results / "bandwidth.csv")},
                   timing=costs.cloud_timing(costs._read(results / "edge_timing.csv"), CAMERA))


def path_bill(ctx: Context, option: str, stores: int, cams_per_store: int = 1, processing: str = "cpu",
              gb_key: str = "gb_day_high") -> dict[str, dict[str, float]]:
    """Hoá đơn đủ dịch vụ như P03/P06, từng dòng, cho một đường dữ liệu (A, B, C, D) và một số tiệm."""
    saved_n, saved_scales, saved_total = ctx.costs.N_STORES, ctx.p03.SCALES, ctx.p03.total
    captured: dict[str, dict[str, float]] = {}

    def spy(lines):
        captured.update({group: dict(items) for group, items in lines.items()})
        return saved_total(lines)

    ctx.costs.N_STORES, ctx.p03.SCALES, ctx.p03.total = stores, {"scale": (stores, cams_per_store)}, spy
    try:
        row = ctx.bandwidth[(option, CAMERA)]
        ctx.costs.cloud_monthly_usd(option, cams_per_store, processing, ctx.p03, ctx.sources, float(row["image_mb_high"]),
                                    float(row[gb_key]), ctx.timing, camera=CAMERA)
    finally:
        ctx.costs.N_STORES, ctx.p03.SCALES, ctx.p03.total = saved_n, saved_scales, saved_total
    if processing == "cpu":  # P06 giữ tên dòng của P03 dù tiền đã tính theo máy CPU; đổi nhãn để khỏi đọc nhầm
        captured["2 Xử lý"]["SageMaker Async ml.c5.xlarge (CPU)"] = captured["2 Xử lý"].pop(ctx.costs.SM_LINE)
    return captured


def hoang_cut(bill: dict) -> dict:
    """Bản hoang sửa tay ngày 24/10: bỏ GuardDuty, Security Hub, Config; Organizations và Control Tower không có dòng tiền."""
    out = {group: dict(items) for group, items in bill.items()}
    for line in HOANG_CUT:
        out["8 Bảo mật"].pop(line)
    return out


def essentials(bill: dict) -> dict:
    """Chỉ thu nhận, xử lý, kết quả, lưu trữ. Đây là cận dưới để so, không phải thiết kế."""
    return {group: dict(bill[group]) for group in DATA_GROUPS}


def phase1_bill(ctx: Context, stores: int, cams_per_store: int = 1, cloud_training: bool = True,
                processing: str = "cpu", option: str = "C", gb_key: str = "gb_day_high") -> dict:
    """Thiết kế đề xuất: giữ nguyên đường dữ liệu và sao lưu, thu gọn nhóm train, website và bảo mật theo PHASE1."""
    p, a = ctx.p03.P, PHASE1
    bill = path_bill(ctx, option, stores, cams_per_store, processing, gb_key)
    bill["6 Train"] = {f"CVAT trên EC2 m7i.xlarge {a['cvat_hours']} h": a["cvat_hours"] * p["m7i.xlarge_h"]}
    if cloud_training:
        bill["6 Train"][f"SageMaker ml.g6.xlarge {a['train_gpu_hours']} h"] = a["train_gpu_hours"] * p["sm_train_g6_h"]
    bill["7 Website"] = {
        "Amplify + API Gateway": a["web_requests"] * (p["amplify_req"] + 0.5 * p["amplify_gbs"] + p["apigw_http_req"]),
        "WAF": p["waf_acl_mo"] + a["waf_rules"] * p["waf_rule_mo"] + a["web_requests"] * p["waf_req"],
        "Cognito": a["web_users"] * p["cognito_mau"],
        "Dữ liệu ra internet": a["egress_gb"] * p["dt_out_gb"],
    }
    bill["8 Bảo mật"] = {
        "KMS + Secrets": a["kms_keys"] * p["kms_key_mo"] + a["kms_requests"] * p["kms_req"] + a["secrets"] * p["secret_mo"],
        "CloudWatch": a["cw_log_gb"] * p["cw_log_gb"] + a["cw_metrics"] * p["cw_metric_mo"] + a["cw_alarms"] * p["cw_alarm_mo"],
    }
    return bill


def outside_aws(ctx: Context, stores: int, no_wifi_share: float, cams_per_store: int = 1) -> dict:
    """Tiền ngoài AWS, USD. Camera do Datagent mua nên ghi riêng để tham khảo, không cộng vào phần của team."""
    src, fx = ctx.sources, value(ctx.sources, "fx.vnd_per_usd")
    no_wifi = stores * no_wifi_share
    return {
        "hộp": stores * value(src, f"{BOX}.price_vnd") / fx,
        "router 4G": no_wifi * value(src, "router4g.price_vnd") / fx,
        "4G/tháng, thấp": no_wifi * value(src, "plan4g_sd100.price_vnd_month") / fx,
        "4G/tháng, cao": no_wifi * value(src, "plan4g_report.price_vnd_month") / fx,
        "điện/tháng, cận trên": ctx.costs.electricity_monthly_usd(
            value(src, f"{BOX}.power_w") + cams_per_store * value(src, f"{CAMERA}.power_w"), stores,
            value(src, "power.vnd_per_kwh"), fx),
        "camera (Datagent mua)": stores * cams_per_store * (value(src, f"{CAMERA}.price_vnd") + value(src, "poe_injector.price_vnd")) / fx,
    }


def total(bill: dict) -> float:
    return sum(sum(group.values()) for group in bill.values())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stores", type=int, default=4)
    ap.add_argument("--budget", type=float, default=None, help="USD; có thì in số tháng dùng được")
    args = ap.parse_args()
    ctx, n = load_context(), args.stores
    full = path_bill(ctx, "C", n)
    months = (lambda usd: f"{args.budget / usd:5.1f} tháng") if args.budget else (lambda usd: "")

    print(f"Kiểm đối chiếu P06, 30 tiệm: C {total(path_bill(ctx, 'C', 30)):.2f} · B {total(path_bill(ctx, 'B', 30)):.2f}\n")
    print(f"BA MỨC DỊCH VỤ, {n} tiệm × 1 camera, gửi ảnh qua hộp, đếm bằng CPU (USD/tháng)")
    stacks = {"Đủ dịch vụ như P03/P06": full, "Bản hoang sửa 24/10": hoang_cut(full), "Giai đoạn đầu (đề xuất)": phase1_bill(ctx, n),
              "Chỉ đường dữ liệu (cận dưới)": essentials(full)}
    for name, bill in stacks.items():
        print(f"  {name:32} {total(bill):8.2f}  {months(total(bill))}")

    print("\nTỪNG NHÓM")
    print(f"  {'nhóm':18}" + "".join(f"{name[:22]:>24}" for name in stacks))
    for group in full:
        print(f"  {group:18}" + "".join(f"{sum(bill.get(group, {}).values()):24.2f}" for bill in stacks.values()))

    print("\nCHI TIẾT GIAI ĐOẠN ĐẦU")
    for group, items in stacks["Giai đoạn đầu (đề xuất)"].items():
        print(f"  {group:18} {sum(items.values()):8.2f}")
        for line, usd in items.items():
            print(f"      {line:48} {usd:8.2f}")

    print("\nBIẾN THỂ CỦA GIAI ĐOẠN ĐẦU")
    variants = {
        "Gốc": phase1_bill(ctx, n),
        "2 camera mỗi tiệm": phase1_bill(ctx, n, cams_per_store=2),
        "Train không chạy trên AWS": phase1_bill(ctx, n, cloud_training=False),
        "Đếm bằng GPU 30 giây/ảnh như P03": phase1_bill(ctx, n, processing="gpu_p03"),
        "10 tiệm": phase1_bill(ctx, 10),
        "30 tiệm": phase1_bill(ctx, 30),
    }
    for name, bill in variants.items():
        print(f"  {name:36} {total(bill):8.2f}  {months(total(bill))}")

    print(f"\nĐƯỜNG DỮ LIỆU, {n} tiệm (USD/tháng)")
    for name, opt, key in (("C · gửi ảnh qua hộp", "C", "gb_day_high"), ("A · camera tự gửi ảnh", "A", "gb_day_high"),
                           ("B · video 4K liên tục, bitrate cao", "B", "gb_day_high"),
                           ("B · video 4K liên tục, bitrate thấp", "B", "gb_day_low")):
        full_path, lean = path_bill(ctx, opt, n, gb_key=key), phase1_bill(ctx, n, option=opt, gb_key=key)
        print(f"  {name:36} đủ dịch vụ {total(full_path):8.2f}  {months(total(full_path))}"
              f" · giai đoạn đầu {total(lean):8.2f}  {months(total(lean))}")

    print(f"\nNGOÀI AWS, {n} tiệm, 50% không có WiFi (USD)")
    for name, usd in outside_aws(ctx, n, 0.5).items():
        print(f"  {name:28} {usd:9.2f}")


if __name__ == "__main__":
    main()
