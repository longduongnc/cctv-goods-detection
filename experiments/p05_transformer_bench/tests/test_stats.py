from bench.stats import height_bin, mcnemar_exact, wilson


def test_wilson_matches_the_th_agreement_interval():
    lo, hi = wilson(114, 164)
    assert (round(lo, 3), round(hi, 3)) == (0.621, 0.760)


def test_wilson_lower_bound_is_zero_without_successes():
    assert wilson(0, 10)[0] == 0.0


def test_mcnemar_exact_matches_the_greyfix_ab():
    assert round(mcnemar_exact(14, 6), 3) == 0.115


def test_mcnemar_exact_without_discordant_pairs():
    assert mcnemar_exact(0, 0) == 1.0


def test_height_bins_edges():
    assert [height_bin(h) for h in (39, 40, 59, 60, 89, 90)] == ["<40", "40–60", "40–60", "60–90", "60–90", "≥90"]
