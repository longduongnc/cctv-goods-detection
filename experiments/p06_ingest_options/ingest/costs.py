"""E5: what each option × camera (× box) costs 30 stores — once (hardware) and every month (cloud, 4G, power) — and
the totals after the 12-week pilot and after 12 months, with gates G1–G3 beside them.

    python -m ingest.costs --sources inputs/sources.csv --results results --out results/cost.csv

The cloud bill is P03's model (docs/architecture/cost_model.py, loaded, never edited) with its assumptions overridden
per option: real picture sizes, no pictures dropped at the camera, and the counting on a CPU instead of a GPU.
"""
import argparse
import csv
import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType

from ingest.bandwidth import D_IMAGES_PER_DAY, MARKS_PER_DAY
from ingest.edge_timing import FRAMES_PER_MARK
from ingest.resolution import G3_DISTANCE_M
from ingest.sources import load_sources, value

N_STORES = 30
DAYS = 30
MONTHS_12W = 84 / 30
COLD_START_H_MONTH = 10 / 60 * DAYS       # P03: 10 billed minutes each time the endpoint starts, once a night
KVS_RETENTION_DAYS = 7                    # P02
KVS_LOWRES_MAX_PX = 1920                  # KVS GetImages bills a frame 1080p or smaller at the low-res price
SM_LINE = "SageMaker Async ml.g6.xlarge"   # P03's processing line, replaced for CPU processing and for option D
BOXES = ("box_rpi5", "box_n100", "box_orin")
CAMERAS_AB = ("cam_2mp", "cam_4k_28", "cam_4k_40")


@dataclass(frozen=True)
class Combo:
    option: str
    camera: str
    box: str | None
    no_wifi_share: float
    plan4g: str
    cams_per_store: int
    processing: str


BASE = dict(no_wifi_share=0.5, plan4g="plan4g_report", cams_per_store=1, processing="cpu")


def combos() -> list[Combo]:
    hardware = [(o, c, None) for o in "AB" for c in CAMERAS_AB]
    hardware += [(o, c, b) for o in "CD" for c in CAMERAS_AB for b in BOXES] + [(o, "oak4s", None) for o in "CD"]
    return [Combo(o, c, b, share, plan, cams, proc) for o, c, b in hardware for share in (0.0, 0.5, 1.0)
            for plan in ("plan4g_sd100", "plan4g_report") for cams in (1, 2) for proc in ("cpu", "gpu_p03")]


def load_p03(repo_root: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("p03_cost_model", repo_root / "docs" / "architecture" / "cost_model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def p03_breakdown(p03, cams_per_store: int, overrides: dict) -> dict[str, dict[str, float]]:
    """P03's monthly bill, line by line, for scenario A (counted each night) with some assumptions overridden;
    P03's own assumptions are put back afterwards."""
    scale = next(k for k, (_, cams) in p03.SCALES.items() if cams == cams_per_store)
    saved = p03.A
    p03.A = {**p03.ASSUMPTIONS, **overrides}
    try:
        return p03.estimate(scale, "A")[3]
    finally:
        p03.A = saved


def cloud_monthly_usd(option: str, cams_per_store: int, processing: str, p03, sources, image_mb: float,
                      video_gb_day: float, timing: dict, camera: str) -> float:
    """AWS bill a month. A and C upload 56 pictures a day per camera, D the 14 it counted; B streams video into
    Kinesis Video Streams and takes 60 frames around each mark out of it, priced by the camera's resolution.
    A and B filter frames in the cloud."""
    overrides = dict(still_mb=image_mb, people_drop=0.0)
    if option == "D":
        overrides["capture_every_min"] = 60
    bill = p03_breakdown(p03, cams_per_store, overrides)
    cams = N_STORES * cams_per_store
    if option == "D":
        bill["2 Xử lý"][SM_LINE] = 0.0
    elif processing == "cpu":
        counted = cams * D_IMAGES_PER_DAY * DAYS
        filtered = cams * DAYS * {"A": MARKS_PER_DAY, "B": MARKS_PER_DAY * FRAMES_PER_MARK}.get(option, 0)
        hours = (counted * timing["count_ms_cloud"] + filtered * timing["filter_ms_cloud"]) / 3.6e6 + COLD_START_H_MONTH
        bill["2 Xử lý"][SM_LINE] = hours * value(sources, "aws.sm_async_cpu_h")
    if option == "B":
        bill["1 Thu nhận"]["KVS ghi video"] = cams * video_gb_day * DAYS * value(sources, "aws.kvs_in_gb")
        bill["1 Thu nhận"]["KVS lưu video 7 ngày"] = (cams * video_gb_day * KVS_RETENTION_DAYS
                                                     * value(sources, "aws.kvs_store_gbmo"))
        lowres = value(sources, f"{camera}.h_pixels") <= KVS_LOWRES_MAX_PX
        bill["2 Xử lý"]["KVS lấy khung"] = (cams * MARKS_PER_DAY * FRAMES_PER_MARK * DAYS
                                            * value(sources, "aws.kvs_getimages_img" + ("_lowres" if lowres else "")))
    return p03.total(bill)


def fourg_monthly_usd(n_stores: int, no_wifi_share: float, plan_vnd: float, fx: float) -> float:
    return n_stores * no_wifi_share * plan_vnd / fx


def router_one_time_usd(n_stores: int, no_wifi_share: float, router_vnd: float, fx: float) -> float:
    return n_stores * no_wifi_share * router_vnd / fx


def electricity_monthly_usd(power_w: float, n_devices: int, vnd_per_kwh: float, fx: float) -> float:
    """power_w running 24 hours a day for a month, on each of n_devices."""
    return power_w * 24 * DAYS / 1000 * n_devices * vnd_per_kwh / fx


def one_time_usd(combo: Combo, sources) -> float:
    """Cameras (none for the store's own 2 MP camera) and a 128 GB card for A and B when the camera has a slot, per
    camera; one box and, for stores without WiFi, one 4G router per store."""
    fx = value(sources, "fx.vnd_per_usd")
    if combo.camera == "cam_2mp":
        camera = 0.0
    elif combo.camera == "oak4s":
        camera = value(sources, "oak4s.price_usd")
    else:
        camera = value(sources, f"{combo.camera}.price_vnd") / fx
    card = 0.0
    if combo.option in ("A", "B") and value(sources, f"{combo.camera}.sd_slot"):
        card = value(sources, "microsd128.price_vnd") / fx
    box = value(sources, f"{combo.box}.price_vnd") / fx if combo.box else 0.0
    router = router_one_time_usd(N_STORES, combo.no_wifi_share, value(sources, "router4g.price_vnd"), fx)
    return N_STORES * combo.cams_per_store * (camera + card) + N_STORES * box + router


def monthly_usd(combo: Combo, sources, cloud_usd: float) -> float:
    """Cloud, 4G for the stores without WiFi, and power for new cameras and the box (the store's own 2 MP camera
    already runs, so it adds no power)."""
    fx = value(sources, "fx.vnd_per_usd")
    camera_w = 0.0 if combo.camera == "cam_2mp" else value(sources, f"{combo.camera}.power_w")
    store_w = camera_w * combo.cams_per_store + (value(sources, f"{combo.box}.power_w") if combo.box else 0.0)
    fourg = fourg_monthly_usd(N_STORES, combo.no_wifi_share, value(sources, f"{combo.plan4g}.price_vnd_month"), fx)
    power = electricity_monthly_usd(store_w, N_STORES, value(sources, "power.vnd_per_kwh"), fx)
    return cloud_usd + fourg + power


def totals(one_time: float, monthly: float) -> tuple[float, float]:
    """(after the 12-week pilot, after 12 months)."""
    return one_time + monthly * MONTHS_12W, one_time + monthly * 12


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def table(sources, results: Path, repo_root: Path) -> list[dict]:
    bandwidth = {(r["option"], r["camera"]): r for r in _read(results / "bandwidth.csv")}
    g3 = {r["camera"]: r["g3"] == "True" for r in _read(results / "resolution.csv")
          if float(r["distance_m"]) == G3_DISTANCE_M}
    cloud_cpu = next(r for r in _read(results / "edge_timing.csv") if r["target"] == "cloud")
    timing = dict(filter_ms_cloud=float(cloud_cpu["filter_ms_frame"]), count_ms_cloud=float(cloud_cpu["count_ms_image"]))
    p03 = load_p03(repo_root)
    rows = []
    for c in combos():
        bw = bandwidth[(c.option, c.camera)]
        cloud = cloud_monthly_usd(c.option, c.cams_per_store, c.processing, p03, sources,
                                  float(bw["image_mb_high"]), float(bw["gb_day_high"]), timing, camera=c.camera)
        once, month = one_time_usd(c, sources), monthly_usd(c, sources, cloud)
        t12w, t12m = totals(once, month)
        rows.append(dict(asdict(c), box=c.box or "", cloud_usd=round(cloud, 2), one_time_usd=round(once, 2),
                         monthly_usd=round(month, 2), total_12w_usd=round(t12w, 2), total_12m_usd=round(t12m, 2),
                         g1=bw["g1"] == "True", g2=c.option in ("C", "D"), g3=g3[c.camera],
                         base=all(getattr(c, k) == v for k, v in BASE.items())))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = table(load_sources(args.sources), args.results, Path(__file__).resolve().parents[3])
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
