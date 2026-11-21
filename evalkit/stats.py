import math, random

def bootstrap_mean_ci(xs, iters=10000, seed=7, alpha=0.05):
    """Mean and percentile bootstrap CI. Applied to paired per-question differences."""
    n = len(xs)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return sum(xs) / n, means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters) - 1]

def sign_test_p(wins, losses):
    """Exact two-sided binomial sign test (ties dropped)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

def mcnemar_exact_p(b, c):
    """Two-sided exact McNemar on discordant pairs: b = new-only failures, c = current-only failures."""
    return sign_test_p(b, c)
