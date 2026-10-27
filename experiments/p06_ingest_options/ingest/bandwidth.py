"""E1: gigabytes sent to the cloud per store per day for each option and camera, and gate G1.

    python -m ingest.bandwidth --sources inputs/sources.csv --jpeg results/bandwidth_jpeg.csv --out results/bandwidth.csv

A, C send one picture per 15-minute mark (56 a day), B a video stream all opening hours, D the 14 pictures it
counted plus the CV Output rows. Low uses the median picture size, high the 90th percentile; G1 is judged at high.
"""
import argparse
import csv
from pathlib import Path

from ingest.sources import load_sources, value

G1_LIMIT_GB = 2.0             # Viettel SD100: 2 GB a day
OPEN_HOURS = 14.0
MARKS_PER_DAY = 56            # 14 hours × 4 marks
D_IMAGES_PER_DAY = 14         # one counted picture an hour, as in P03
ROWS_PER_IMAGE, ROW_KB = 30, 0.5          # CV Output rows per picture and their size, as in P03
P03_STILL_MB = 10.0           # P03's assumption for one 48 MP OAK 4 S picture (not measured)
BITRATE_KEY = {"cam_2mp": "vendor.h265_2mp_mbps"}         # B: the 2 MP camera streams 1080p; every other camera 8 MP
OPTION_CAMERAS = {
    "A": ("cam_2mp", "cam_4k_28", "cam_4k_40"),
    "B": ("cam_2mp", "cam_4k_28", "cam_4k_40"),
    "C": ("cam_2mp", "cam_4k_28", "cam_4k_40", "oak4s"),
    "D": ("cam_2mp", "cam_4k_28", "cam_4k_40", "oak4s"),
}


def video_gb_per_day(mbps: float, hours: float = OPEN_HOURS) -> float:
    return mbps * 1e6 / 8 * hours * 3600 / 1e9


def images_gb_per_day(n_images: int, mb_each: float) -> float:
    return n_images * mb_each / 1000


def option_gb_per_day(option: str, image_mb: float, video_mbps: float) -> float:
    if option in ("A", "C"):
        return images_gb_per_day(MARKS_PER_DAY, image_mb)
    if option == "B":
        return video_gb_per_day(video_mbps)
    if option == "D":
        return images_gb_per_day(D_IMAGES_PER_DAY, image_mb) + D_IMAGES_PER_DAY * ROWS_PER_IMAGE * ROW_KB / 1e6
    raise ValueError(f"unknown option {option!r}")


def passes_g1(gb_day: float) -> bool:
    return gb_day <= G1_LIMIT_GB


def image_mb_by_camera(jpeg_rows: list[dict]) -> dict[str, tuple[float, float]]:
    """(median, 90th percentile) MB of one picture per camera: the 2 MP camera from the 39 store frames at 2 MP,
    the 4K cameras from the iPhone photos shrunk to 8 MP, the OAK 4 S from P03's 10 MB."""
    def pick(label, mp):
        for r in jpeg_rows:
            if r["label"] == label and float(r["megapixels"]) == mp:
                return float(r["mb_median"]), float(r["mb_p90"])
        raise KeyError(f"no {label} row at {mp} MP in the JPEG measurements")
    four_k = pick("iphone", 8.0)
    return {"cam_2mp": pick("frames39", 2.0), "cam_4k_28": four_k, "cam_4k_40": four_k,
            "oak4s": (P03_STILL_MB, P03_STILL_MB)}


def table(sources, jpeg_rows: list[dict]) -> list[dict]:
    mb = image_mb_by_camera(jpeg_rows)
    rows = []
    for option, cameras in OPTION_CAMERAS.items():
        for cam in cameras:
            key = BITRATE_KEY.get(cam, "vendor.h265_8mp_mbps")
            mbps = (value(sources, f"{key}_low"), value(sources, f"{key}_high"))
            low, high = (option_gb_per_day(option, image_mb=m, video_mbps=v) for m, v in zip(mb[cam], mbps))
            basis = "vendor" if option == "B" else ("p03" if cam == "oak4s" else "measured")
            rows.append(dict(option=option, camera=cam, image_mb_low=mb[cam][0], image_mb_high=mb[cam][1],
                             gb_day_low=round(low, 4), gb_day_high=round(high, 4), g1=passes_g1(high), basis=basis))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--jpeg", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with open(args.jpeg, encoding="utf-8") as f:
        jpeg = list(csv.DictReader(f))
    rows = table(load_sources(args.sources), jpeg)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
