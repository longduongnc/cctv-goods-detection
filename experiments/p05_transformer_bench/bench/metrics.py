"""Indicator 1 (units named right) and its groups for one model on the real units, with 95% Wilson intervals."""
from bench.skus import SUA_HAT, TH_PAIR
from bench.stats import height_bin, wilson
from bench.testset import Unit

BINS = ("<40", "40–60", "60–90", "≥90")


def rate(k: int, n: int) -> tuple[int, int, float, float]:
    """(k, n, lo, hi); the interval is nan when there is nothing to count."""
    lo, hi = wilson(k, n) if n else (float("nan"), float("nan"))
    return k, n, lo, hi


def unit_report(units: list[Unit], pred: dict[str, str | None]) -> dict:
    """A unit whose answer is None or missing counts as wrong. Units labelled NEG stay out of the accuracy;
    neg_rejected, present only when there are some, is the share of them left without an answer."""
    pos = [u for u in units if u.label.startswith("TMP-MLK-")]
    neg = [u for u in units if u.label == "NEG"]

    def right(group):
        return rate(sum(pred.get(u.uid) == u.label for u in group), len(group))

    report = dict(acc=right(pos), th_pair=right([u for u in pos if u.label in TH_PAIR]),
                  sua_hat=right([u for u in pos if u.label in SUA_HAT]),
                  by_height={b: right([u for u in pos if height_bin(u.box[3]) == b]) for b in BINS})
    if neg:
        report["neg_rejected"] = rate(sum(pred.get(u.uid) is None for u in neg), len(neg))
    return report
