"""
Is peer dispersion structural, or is it what four draws from one distribution look like?

THE PREMISE THIS REPORT INHERITS, AND WHY IT CANNOT BE TESTED AS MEASURED
--------------------------------------------------------------------------
ValuationLab's SOTP rests on a claim that dispersion among large-cap pharma peers is
economic rather than a small-sample artefact, evidenced by adding two more peers and
observing the spread WIDEN. If dispersion were just sampling noise, the argument runs,
more peers should tighten the estimate, not loosen it.

That argument is invalid, and the invalidity is in the statistic rather than the
reasoning. `summarize` reports dispersion as min/max -- the richest peer divided by the
cheapest. A min/max range is MONOTONIC IN SAMPLE SIZE: the minimum can only fall and the
maximum can only rise as peers are added, so the spread can never narrow no matter what
is added. Drawing repeatedly from a single tight lognormal, mean min/max spread runs
about 1.7x at four peers, 1.9x at six and 2.2x at ten -- with no change whatsoever in
the underlying distribution. Observing a wider spread at six peers than four is
therefore consistent with the structural claim and equally consistent with its exact
opposite, which makes it evidence for neither.

The same monotonicity bears on the 2.0x disqualification threshold itself. At four
peers, a set drawn from one tight distribution trips 2.0x roughly a fifth of the time;
at ten peers, roughly two thirds. The bar is not scale-free, so "spread exceeds 2.0x" is
a statement about peer count as much as about comparability.

WHAT THIS MODULE PROVIDES INSTEAD
----------------------------------
Two scale-free measures that CAN move in either direction when peers are added, so the
premise becomes falsifiable:

  coefficient of variation   standard deviation over mean. Uses every peer rather than
                             only the two extremes, so an added peer near the centre
                             pulls it DOWN. This is the measure the structural claim
                             actually needs.

  IQR over median            robust alternative. At four to six peers the quartiles are
                             interpolated from very little, so it is reported as
                             corroboration and never on its own.

And a null model: given an observed CV, what min/max spread would pure sampling produce
at this peer count? That converts a bare "2.5x spread" into "2.5x spread, where four
draws from a single distribution of this shape average 1.9x and exceed 2.0x a third of
the time" -- which is the sentence that makes the number mean something.

IMPORTANT LIMIT, STATED RATHER THAN BURIED
-------------------------------------------
None of this rescues the SOTP's own fitness verdicts, and it does not need to. Those
compare MedTech at four peers against Innovative Medicine at four peers -- equal n, so
the monotonicity cancels and 1.5x against 2.5x is a fair comparison between two sets of
the same size. What is contaminated is the separate six-peer argument that dispersion is
structural. The fitness verdicts stand; the evidence offered for WHY they differ does not.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass

#: ValuationLab's disqualification bar, mirrored so the null model can report how often
#: pure sampling would trip it at a given peer count.
DISQUALIFYING_SPREAD = 2.0


class DispersionError(ValueError):
    pass


@dataclass(frozen=True)
class Dispersion:
    n: int
    min_max_spread: float
    coefficient_of_variation: float
    iqr_over_median: float
    median: float

    def describe(self) -> str:
        return (f"n={self.n}  min/max {self.min_max_spread:.2f}x  "
                f"CV {self.coefficient_of_variation:.3f}  "
                f"IQR/median {self.iqr_over_median:.3f}")


def dispersion(values: list[float]) -> Dispersion:
    if len(values) < 3:
        raise DispersionError(
            f"{len(values)} peers is too few for any dispersion statistic to mean "
            f"anything. Refusing rather than returning a number that would be quoted.")
    if any(v <= 0 for v in values):
        raise DispersionError("Non-positive multiples: ratios are undefined.")

    mean = statistics.fmean(values)
    median = statistics.median(values)
    ordered = sorted(values)
    # Quantiles with n=4 interpolate from almost nothing; reported as corroboration only.
    q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    return Dispersion(
        n=len(values),
        min_max_spread=max(values) / min(values),
        coefficient_of_variation=statistics.stdev(values) / mean,
        iqr_over_median=(q3 - q1) / median,
        median=median)


def expected_spread_under_noise(n: int, cv: float, trials: int = 20_000,
                                threshold: float = DISQUALIFYING_SPREAD,
                                seed: int = 0) -> tuple[float, float]:
    """(mean min/max spread, P(spread > threshold)) for `n` draws from a single
    lognormal with coefficient of variation `cv`.

    Parametric by necessity: with four to six peers there is nothing to resample. The
    lognormal is an assumption -- multiples are positive and right-skewed, which it
    fits, but it is an assumption and the number below inherits it. It is used for one
    narrow purpose: showing that a spread of a given size at a given n is or is not
    surprising under the null of a single distribution.
    """
    if n < 2:
        raise DispersionError("Need at least 2 draws.")
    if cv <= 0:
        raise DispersionError("CV must be positive.")
    sigma = math.sqrt(math.log(1 + cv * cv))
    rng = random.Random(seed)
    spreads = []
    for _ in range(trials):
        draws = [rng.lognormvariate(0.0, sigma) for _ in range(n)]
        spreads.append(max(draws) / min(draws))
    return (statistics.fmean(spreads),
            sum(s > threshold for s in spreads) / trials)


@dataclass(frozen=True)
class PremiseTest:
    small: Dispersion
    large: Dispersion
    added: tuple[str, ...]

    @property
    def spread_widened(self) -> bool:
        """The measure ValuationLab used. Kept only to show what it does."""
        return self.large.min_max_spread > self.small.min_max_spread

    @property
    def cv_widened(self) -> bool:
        """The measure that can actually fall when peers are added."""
        return (self.large.coefficient_of_variation
                > self.small.coefficient_of_variation)

    @property
    def iqr_widened(self) -> bool:
        return self.large.iqr_over_median > self.small.iqr_over_median

    @property
    def measures_disagree(self) -> bool:
        """CV and IQR/median pointing opposite ways is the signature of ONE extreme
        observation: the CV squares deviations so a single outlier dominates it, while
        the interquartile range steps over that peer entirely. When they disagree the
        answer depends on which peer you are willing to call representative, and no
        verdict should be issued without saying so."""
        return self.cv_widened != self.iqr_widened

    @property
    def supports_structural_claim(self) -> bool:
        """Both scale-free measures must agree. Requiring only the CV -- which is what
        this class did first -- let a single peer at three times the next richest carry
        a verdict about the whole set."""
        return self.cv_widened and self.iqr_widened

    def verdict(self) -> str:
        head = (f"  {self.small.n} peers: {self.small.describe()}\n"
                f"  {self.large.n} peers: {self.large.describe()}   "
                f"(added {', '.join(self.added)})")
        note = ("\n  NOTE: min/max can only rise as peers are added, so its movement "
                "here carries no information either way. The CV comparison is the test.")
        if self.measures_disagree:
            direction = ("CV rose while IQR/median fell" if self.cv_widened
                         else "CV fell while IQR/median rose")
            return (f"{head}{note}\n\n  INCONCLUSIVE -- the two scale-free measures "
                    f"disagree: {direction} "
                    f"(CV {self.small.coefficient_of_variation:.3f} -> "
                    f"{self.large.coefficient_of_variation:.3f}; IQR/median "
                    f"{self.small.iqr_over_median:.3f} -> "
                    f"{self.large.iqr_over_median:.3f}). That pattern is what ONE "
                    f"extreme peer produces: the CV squares deviations so a single "
                    f"outlier dominates it, while the interquartile range steps over "
                    f"that peer entirely. Run the leave-one-out below before drawing "
                    f"any conclusion -- if the verdict rests on one company, the claim "
                    f"is about that company, not about the peer set.")
        if self.cv_widened:
            return (f"{head}{note}\n\n  PREMISE SUPPORTED. Coefficient of variation "
                    f"rose from {self.small.coefficient_of_variation:.3f} to "
                    f"{self.large.coefficient_of_variation:.3f} -- the added peers sit "
                    f"away from the centre, not near it, which is what an economically "
                    f"heterogeneous peer set looks like and is not what sampling noise "
                    f"would produce.")
        return (f"{head}{note}\n\n  PREMISE NOT SUPPORTED. Coefficient of variation FELL "
                f"from {self.small.coefficient_of_variation:.3f} to "
                f"{self.large.coefficient_of_variation:.3f}: the added peers pulled the "
                f"set toward its centre, which is what a larger sample from ONE "
                f"distribution does. The min/max spread still widened, but it was always "
                f"going to. The claim that dispersion is structural rather than a "
                f"small-sample artefact is not supported by this evidence, and the "
                f"report must not cite it as though it were.")


def compare_peer_sets(small_values: list[float], large_values: list[float],
                 added: tuple[str, ...]) -> PremiseTest:
    if len(large_values) <= len(small_values):
        raise DispersionError(
            "The larger set must actually be larger -- this test is about what happens "
            "when peers are ADDED.")
    return PremiseTest(dispersion(small_values), dispersion(large_values), added)

@dataclass(frozen=True)
class LeaveOneOut:
    """Which single added peer, if any, is carrying the verdict."""
    baseline_cv: float
    per_peer: tuple[tuple[str, float, bool], ...]   # (ticker, cv with it added, widened)

    @property
    def carried_by_one(self) -> bool:
        return sum(1 for _, _, widened in self.per_peer if widened) == 1

    def describe(self) -> str:
        lines = [f"  Baseline CV over the original set: {self.baseline_cv:.3f}"]
        for ticker, cv, widened in self.per_peer:
            arrow = "widens" if widened else "TIGHTENS"
            lines.append(f"    + {ticker:<6} alone -> CV {cv:.3f}  ({arrow})")
        widening = [t for t, _, w in self.per_peer if w]
        if self.carried_by_one:
            lines.append(
                f"\n  The result rests entirely on {widening[0]}. Every other added peer "
                f"pulls the set TOWARD its centre, which is what a larger sample from "
                f"one distribution does. So the honest claim is not 'pharma peers are "
                f"economically heterogeneous' but '{widening[0]} trades far away from "
                f"the rest' -- a statement about one company. The report must make the "
                f"narrower claim, and name the company.")
        elif not widening:
            lines.append("\n  No added peer widens the set on its own. The structural "
                         "claim has no support here.")
        else:
            lines.append(f"\n  {len(widening)} of {len(self.per_peer)} added peers widen "
                         f"the set independently, so the result does not rest on a "
                         f"single company.")
        return "\n".join(lines)


def leave_one_out(baseline: list[float],
                  added: dict[str, float]) -> LeaveOneOut:
    """Add each candidate peer ALONE and see which ones actually widen the set.

    A combined CV that rose tells you the group of added peers widened dispersion on
    net; it does not tell you whether one of them did all the work while the others
    tightened it. Those are different claims and only this separates them.
    """
    if not added:
        raise DispersionError("No candidate peers to test.")
    base_cv = dispersion(baseline).coefficient_of_variation
    rows = []
    for ticker, value in added.items():
        cv = dispersion(baseline + [value]).coefficient_of_variation
        rows.append((ticker, cv, cv > base_cv))
    return LeaveOneOut(baseline_cv=base_cv, per_peer=tuple(rows))
