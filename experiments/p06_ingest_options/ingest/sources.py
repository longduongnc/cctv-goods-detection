"""Read inputs/sources.csv: every price and spec the comparison uses, each with where it came from and when it was checked."""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
