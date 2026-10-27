"""Read inputs/sources.csv: every price and spec the comparison uses, each with where it came from and when it was checked."""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_CAMERA = ("h_pixels", "hfov_deg", "price_vnd", "power_w", "sd_slot")
_BOX = ("price_vnd", "power_w", "storage_gb", "cpu_st", "hevc_hw")

# every key the comparison reads; a .cpu_st score is a single-thread benchmark, all five on the same scale
REQUIRED_KEYS = (
    "fx.vnd_per_usd", "power.vnd_per_kwh",
    "plan4g_sd100.price_vnd_month", "plan4g_sd100.gb_per_day", "plan4g_report.price_vnd_month",
    "router4g.price_vnd", "microsd128.price_vnd",
    "cam_2mp.h_pixels", "cam_2mp.hfov_deg", "cam_2mp.power_w", "cam_2mp.sd_slot",
    *(f"{cam}.{field}" for cam in ("cam_4k_28", "cam_4k_40") for field in _CAMERA),
    "oak4s.h_pixels", "oak4s.hfov_deg", "oak4s.price_usd", "oak4s.power_w", "oak4s.storage_gb",
    *(f"{box}.{field}" for box in ("box_rpi5", "box_n100", "box_orin") for field in _BOX),
    "cpu_long.cpu_st", "cpu_cloud.cpu_st",
    "aws.sm_async_cpu_h", "aws.kvs_in_gb", "aws.kvs_store_gbmo", "aws.kvs_getimages_img",
    "vendor.h265_8mp_mbps_low", "vendor.h265_8mp_mbps_high",
)


@dataclass(frozen=True)
class Source:
    key: str
    value: float
    unit: str
    source: str
    checked_on: str
    note: str


def load_sources(path: Path) -> dict[str, Source]:
    """Every row by key. A row without a source, with a date not written YYYY-MM-DD, with a value that is not a
    number, or with a key seen before raises ValueError naming the key."""
    sources = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = row["key"].strip()
            if key in sources:
                raise ValueError(f"{key}: key appears twice")
            if not (row["source"] or "").strip():
                raise ValueError(f"{key}: no source")
            checked = (row["checked_on"] or "").strip()
            if not _DATE.match(checked):
                raise ValueError(f"{key}: checked_on {checked!r} is not YYYY-MM-DD")
            try:
                number = float(row["value"])
            except ValueError:
                raise ValueError(f"{key}: value {row['value']!r} is not a number") from None
            sources[key] = Source(key, number, (row["unit"] or "").strip(), row["source"].strip(), checked,
                                  (row["note"] or "").strip())
    return sources


def value(sources: dict[str, Source], key: str) -> float:
    """The number stored under key; KeyError naming the key when it is missing."""
    try:
        return sources[key].value
    except KeyError:
        raise KeyError(f"{key} is not in sources.csv") from None
