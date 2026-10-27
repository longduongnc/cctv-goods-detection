"""E6: how many opening hours without network each option rides out before its buffer is full and pictures are lost.

    python -m ingest.outage --sources inputs/sources.csv --bandwidth results/bandwidth.csv --out results/outage.csv

Buffers (plan decision 8): A and B keep pictures or video on a 128 GB microSD card in the camera, if the camera has a
slot, and lose them otherwise; C and D keep them on the box; the OAK 4 S on its own 128 GB.
"""
import argparse
import csv
from pathlib import Path

from ingest.bandwidth import OPEN_HOURS
from ingest.sources import load_sources, value

SD_CARD_GB = 128
BOXES = ("box_rpi5", "box_n100", "box_orin")


def hours_until_full(buffer_gb: float, gb_per_day: float, open_hours: float = OPEN_HOURS) -> float:
    """Opening hours of data the buffer holds, at the day's upload rate spread over the opening hours."""
    return buffer_gb / (gb_per_day / open_hours) if buffer_gb else 0.0


def buffer_gb(option: str, camera: str, box: str | None, sources) -> float:
    if option in ("A", "B"):
        return float(SD_CARD_GB) if value(sources, f"{camera}.sd_slot") else 0.0
    if camera == "oak4s":
        return value(sources, "oak4s.storage_gb")
    return value(sources, f"{box}.storage_gb")


def table(sources, bandwidth_rows: list[dict]) -> list[dict]:
    rows = []
    for b in bandwidth_rows:
        option, camera, gb_day = b["option"], b["camera"], float(b["gb_day_high"])
        boxes = BOXES if option in ("C", "D") and camera != "oak4s" else (None,)
        for box in boxes:
            buf = buffer_gb(option, camera, box, sources)
            rows.append(dict(option=option, camera=camera, box=box or "", buffer_gb=buf, gb_day_high=gb_day,
                             hours_until_full=round(hours_until_full(buf, gb_day), 1)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--bandwidth", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with open(args.bandwidth, encoding="utf-8") as f:
        rows = table(load_sources(args.sources), list(csv.DictReader(f)))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
