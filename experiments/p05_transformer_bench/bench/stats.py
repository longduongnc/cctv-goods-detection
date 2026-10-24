"""Confidence intervals, paired tests and size groups for the P05 tables."""
import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for k successes out of n."""
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar test on the discordant pairs: b right only in A, c right only in B."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def height_bin(h: int) -> str:
    """Size group of a box by its height in pixels."""
    if h < 40:
        return "<40"
    if h < 60:
        return "40–60"
    if h < 90:
        return "60–90"
    return "≥90"
