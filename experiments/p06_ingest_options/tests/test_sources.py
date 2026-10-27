import pytest

from ingest.sources import load_sources, value

HEADER = "key,value,unit,source,checked_on,note\n"


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
