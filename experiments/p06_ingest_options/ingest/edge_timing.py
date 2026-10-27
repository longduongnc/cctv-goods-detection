"""E2: scale the milliseconds measured on long's machine (4 threads) to each candidate box and to the cloud CPU by
single-thread benchmark score (one scale for all five CPUs, see inputs/sources.csv). These are estimates, not
measurements on the boxes.

    python -m ingest.edge_timing --raw results/edge_timing_raw.csv --sources inputs/sources.csv --out results/edge_timing.csv
"""
import argparse
import csv
from pathlib import Path
from statistics import median

from ingest.bandwidth import D_IMAGES_PER_DAY, MARKS_PER_DAY
from ingest.sources import load_sources, value

TARGETS = ("box_rpi5", "box_n100", "box_orin", "cloud")
FRAMES_PER_MARK = 60          # option C: one frame a second for 60 seconds around each 15-minute mark


def scale_ms(ms_ref: float, st_ref: float, st_target: float) -> float:
    return ms_ref * st_ref / st_target


def summarize(raw_rows: list[dict], sources) -> list[dict]:
    """Median ms of the filter and count steps, scaled to each target; seconds of work per mark (C) and per day (D)."""
    med = {step: median(float(r["ms"]) for r in raw_rows if r["step"] == step) for step in ("filter", "count")}
    st_ref = value(sources, "cpu_long.cpu_st")
    rows = []
    for target in TARGETS:
        st = value(sources, f"{'cpu_cloud' if target == 'cloud' else target}.cpu_st")
        filt, count = scale_ms(med["filter"], st_ref, st), scale_ms(med["count"], st_ref, st)
        rows.append(dict(target=target, filter_ms_frame=round(filt, 1), count_ms_image=round(count, 1),
                         c_s_per_mark=round(FRAMES_PER_MARK * filt / 1000, 2),
                         d_s_per_day=round((MARKS_PER_DAY * FRAMES_PER_MARK * filt + D_IMAGES_PER_DAY * count) / 1000, 1),
                         hevc_hw="" if target == "cloud" else int(value(sources, f"{target}.hevc_hw")),
                         hevc_unverified="" if target == "cloud" else int(sources[f"{target}.hevc_hw"].unverified)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with open(args.raw, encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    rows = summarize(raw, load_sources(args.sources))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
