from pathlib import Path

import pytest

from ingest.sources import REQUIRED_KEYS, load_sources, value

HEADER = "key,value,unit,source,checked_on,note\n"
SOURCES = Path(__file__).parents[1] / "inputs" / "sources.csv"


def write(tmp_path, body):
    p = tmp_path / "s.csv"
    p.write_text(HEADER + body, encoding="utf-8")
    return p


def test_loads_a_valid_row(tmp_path):
    s = load_sources(write(tmp_path, "fx.vnd_per_usd,26350,VND/USD,https://vietcombank.com.vn,2026-10-27,giá bán\n"))
    assert value(s, "fx.vnd_per_usd") == 26350.0
    assert s["fx.vnd_per_usd"].checked_on == "2026-10-27"


@pytest.mark.parametrize("row", [
    "a.b,1,u,,2026-10-27,\n",             # thiếu nguồn
    "a.b,1,u,https://x,27/10/2026,\n",    # ngày sai dạng
    "a.b,abc,u,https://x,2026-10-27,\n",  # giá trị không phải số
])
def test_rejects_bad_rows(tmp_path, row):
    with pytest.raises(ValueError):
        load_sources(write(tmp_path, row))


def test_rejects_duplicate_keys(tmp_path):
    row = "a.b,1,u,https://x,2026-10-27,\n"
    with pytest.raises(ValueError, match="a.b"):
        load_sources(write(tmp_path, row + row))


def test_missing_key_names_the_key(tmp_path):
    s = load_sources(write(tmp_path, "a.b,1,u,https://x,2026-10-27,\n"))
    with pytest.raises(KeyError, match="c.d"):
        value(s, "c.d")


def test_every_required_key_has_a_sourced_value():
    s = load_sources(SOURCES)
    assert not [k for k in REQUIRED_KEYS if k not in s]


def test_cpu_scores_share_one_scale():
    s = load_sources(SOURCES)
    assert len({s[k].unit for k in REQUIRED_KEYS if k.endswith(".cpu_st")}) == 1


def test_currencies_are_labelled():
    s = load_sources(SOURCES)
    assert all(s[k].unit == "VND" for k in REQUIRED_KEYS if k.endswith(".price_vnd"))
