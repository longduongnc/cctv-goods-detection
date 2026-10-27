"""E3: how sharp a carton is on each camera's picture — pixels per cm of shelf, carton height in pixels, and gate G3.

    python -m ingest.resolution --sources inputs/sources.csv --carton-cm 11 --out results/resolution.csv
"""
import argparse
import csv
import math
from pathlib import Path

from ingest.sources import load_sources, value

G3_MIN_PX = 60          # P06 G3: a 180 ml carton at least 60 px tall at 2 m; below 60 px YOLO finds at most 81.4% of cartons
G3_DISTANCE_M = 2.0
CAMERAS = ("cam_2mp", "cam_4k_28", "cam_4k_40", "oak4s")
DISTANCES_M = (1.5, 2.0, 3.0)


def px_per_cm(h_pixels: int, hfov_deg: float, distance_m: float) -> float:
    """Pixels across one cm of shelf square to the camera, as in P03: h_pixels / (2 × distance × tan(HFOV / 2))."""
    return h_pixels / (2 * distance_m * 100 * math.tan(math.radians(hfov_deg) / 2))


def coverage_width_m(hfov_deg: float, distance_m: float) -> float:
    """Width of shelf one camera sees at that distance."""
    return 2 * distance_m * math.tan(math.radians(hfov_deg) / 2)


def carton_px(px_cm: float, carton_cm: float) -> float:
    return px_cm * carton_cm


def passes_g3(carton_px_at_2m: float) -> bool:
    return carton_px_at_2m >= G3_MIN_PX


def table(sources, carton_cm: float) -> list[dict]:
    """One row per camera and distance; g3 is judged at 2 m and repeated on every row of that camera."""
    rows = []
    for cam in CAMERAS:
        w, hfov = value(sources, f"{cam}.h_pixels"), value(sources, f"{cam}.hfov_deg")
        g3 = passes_g3(carton_px(px_per_cm(w, hfov, G3_DISTANCE_M), carton_cm))
        for d in DISTANCES_M:
            per_cm = px_per_cm(w, hfov, d)
            rows.append(dict(camera=cam, distance_m=d, px_per_cm=round(per_cm, 2),
                             carton_px=round(carton_px(per_cm, carton_cm), 1),
                             coverage_m=round(coverage_width_m(hfov, d), 2), g3=g3, carton_cm=carton_cm))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--carton-cm", type=float, default=11.0, help="height of a 180 ml carton; 11 until one is measured")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = table(load_sources(args.sources), args.carton_cm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
