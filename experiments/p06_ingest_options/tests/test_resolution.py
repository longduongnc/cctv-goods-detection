import pytest

from ingest.resolution import carton_px, coverage_width_m, min_carton_cm, passes_g3, px_per_cm


@pytest.mark.parametrize("w,hfov,d,expected", [
    (8000, 67.0, 1.5, 40.3), (8000, 67.0, 2.0, 30.2), (8000, 67.0, 3.0, 20.1),   # OAK 4 S, bảng của P03
    (4056, 69.0, 2.0, 14.8),                                                     # OAK-D CM4 PoE
    (1920, 112.1, 2.0, 3.2),                                                     # 2 MP, ống 2,8 mm
])
def test_px_per_cm_matches_p03(w, hfov, d, expected):
    assert round(px_per_cm(w, hfov, d), 1) == expected


def test_coverage_width():
    assert round(coverage_width_m(67.0, 2.0), 2) == 2.65


def test_min_carton_cm_is_the_shortest_carton_that_still_passes_g3():
    assert min_carton_cm(7.10) == pytest.approx(8.45, abs=0.01)                  # CCTV 4K, ống 2,8 mm, ở 2 m
    assert passes_g3(carton_px(7.10, min_carton_cm(7.10)))


def test_g3_gate():
    assert not passes_g3(carton_px(px_per_cm(1920, 112.1, 2.0), 11.0))    # 35,5 px
    assert passes_g3(carton_px(px_per_cm(8000, 67.0, 2.0), 11.0))          # 332 px
    assert passes_g3(60.0) and not passes_g3(59.9)
