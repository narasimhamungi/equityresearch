"""
What does the market implicitly pay for the segment nobody can value?

THE ARGUMENT THIS MODULE MAKES COMPUTABLE
------------------------------------------
ValuationLab's finding is a negative one: J&J's MedTech segment values cleanly against
its own peer group, Innovative Medicine does not clear the same dispersion bar against
pharma peers, and therefore no single peer set values the company. That is a statement
about method fitness. It stops short of saying anything about price.

This module takes the one step that turns it into an investment argument. If exactly one
leg is structurally fit, its enterprise value is the only defensible number in the whole
exercise -- so subtract it from what the market is actually paying and the remainder is
what the market implicitly assigns to the unfit leg. Divide by that segment's revenue
and you have a multiple the market is paying, which can be placed against the peer
multiples directly.

The result is an argument the prior projects could not make, because it inverts the
direction of the inference. ValuationLab asks "what is this segment worth?" and answers
"the peer set cannot tell you." This asks "what is the market already paying?" and
answers with a number, because the market price is observed rather than estimated. The
dispersion that disqualified the peer set from VALUING the segment does not prevent the
peer set from LOCATING the market's implied multiple within the distribution of what
comparable companies trade at. Those are different claims and only the second one is
available here.

WHAT THIS IS NOT
-----------------
It is not a valuation of the unfit segment, and the output strings say so on every run.
If the peer set is too dispersed for its median to value a segment -- which is precisely
why that leg was disqualified -- then it is also too dispersed to support "the segment is
worth X and the market pays Y, therefore mispriced by Y-X." What survives is weaker and
still useful: where the market's implied multiple sits relative to the range of multiples
comparable companies actually trade at. A market implying a multiple above every peer in
the set is a fact about the distribution, not a valuation, and it has to be reported as
the former.

Three structural guards, all fatal rather than advisory:

  1. The fit leg must actually be fit. The entire inversion rests on its EV being
     defensible. If its own peer spread trips the disqualification threshold, there is
     no anchor and the residual is meaningless -- so this refuses rather than producing
     a number that looks the same either way.

  2. Exactly one leg may be unfit -- enforced by guard 1 plus the two-leg signature,
     not separately checked. With two unfit legs the residual would be a single number
     split between them in unknown proportion, and any allocation would be an
     assumption wearing an arithmetic disguise. Extending this to three or more
     segments would require that check explicitly.

  3. Segment revenues must reconcile to consolidated revenue. A missing segment silently
     shifts its entire value into the residual and inflates the implied multiple by
     exactly the amount that is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

#: ValuationLab disqualifies a peer set whose multiples span more than this from
#: cheapest to richest. Mirrored rather than imported so this module states the bar it
#: is applying; if the two ever diverge, `assert_matches_upstream` is how you find out.
DISQUALIFYING_SPREAD = 2.0


class ImpliedError(ValueError):
    """Raised when the inversion is not available. Never downgraded to a warning: every
    failure here produces a number that looks exactly like a valid one."""


@dataclass(frozen=True)
class Leg:
    """One reportable segment, with the peer evidence behind it."""
    name: str
    revenue: float
    peer_group: str
    peer_multiple_low: float
    peer_multiple_high: float
    peer_multiple_median: float

    @property
    def spread(self) -> float:
        return self.peer_multiple_high / self.peer_multiple_low

    @property
    def fit(self) -> bool:
        return self.spread <= DISQUALIFYING_SPREAD

    def ev_range(self) -> tuple[float, float]:
        return (self.revenue * self.peer_multiple_low,
                self.revenue * self.peer_multiple_high)


@dataclass(frozen=True)
class ImpliedPoint:
    """The residual at one point of the fit leg's EV range."""
    fit_ev: float
    fit_label: str          # "low" | "mid" | "high"
    residual_ev: float
    residual_multiple: float

    def position(self, leg: Leg) -> str:
        if self.residual_multiple > leg.peer_multiple_high:
            return "above peer max"
        if self.residual_multiple < leg.peer_multiple_low:
            return "below peer min"
        if self.residual_multiple > leg.peer_multiple_median:
            return "above peer median, within range"
        return "at or below peer median, within range"


@dataclass(frozen=True)
class ImpliedResult:
    fit_leg: Leg
    residual_leg: Leg
    market_cap: float
    net_debt: float
    enterprise_value: float
    points: tuple[ImpliedPoint, ...]

    @property
    def robust(self) -> bool:
        """True when the residual lands in the SAME position relative to the peer range
        at every point of the fit leg's EV span. A conclusion that flips between the
        low and high ends of that span is a conclusion about which end you picked --
        and picking one would be the analyst choosing the answer."""
        return len({p.position(self.residual_leg) for p in self.points}) == 1

    @property
    def multiple_span(self) -> tuple[float, float]:
        ms = [p.residual_multiple for p in self.points]
        return (min(ms), max(ms))


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ImpliedError(message)


def implied_residual(market_cap: float, net_debt: float, fit_leg: Leg,
                     residual_leg: Leg, consolidated_revenue: float,
                     revenue_tolerance: float = 1.0) -> ImpliedResult:
    """Back the fit leg's EV out of enterprise value; the remainder is the residual.

    `net_debt` is added to market cap to reach EV, so it is positive for a net borrower
    and negative for a net-cash company -- the same sign convention ValuationLab uses
    when it bridges its SOTP total back to an implied price.
    """
    _check(fit_leg.fit,
           f"{fit_leg.name} is not structurally fit: peer multiples span "
           f"{fit_leg.spread:.1f}x against a {DISQUALIFYING_SPREAD:.1f}x threshold. The "
           f"inversion subtracts this leg's EV from the market's, so an indefensible "
           f"anchor makes the residual indefensible too -- and it would look identical "
           f"to a valid one.")

    _check(fit_leg.name != residual_leg.name,
           "The fit leg and the residual leg are the same segment.")

    total = fit_leg.revenue + residual_leg.revenue
    _check(abs(total - consolidated_revenue) <= revenue_tolerance,
           f"Segment revenues sum to {total:,.0f} against consolidated "
           f"{consolidated_revenue:,.0f} (gap {total - consolidated_revenue:,.0f}). A "
           f"segment missing from this pair has its entire value pushed into the "
           f"residual, inflating the implied multiple by exactly that amount.")

    _check(residual_leg.revenue > 0,
           f"{residual_leg.name} has non-positive revenue; no multiple is defined.")

    enterprise_value = market_cap + net_debt
    low, high = fit_leg.ev_range()
    mid = fit_leg.revenue * fit_leg.peer_multiple_median

    points: list[ImpliedPoint] = []
    for label, fit_ev in (("low", low), ("mid", mid), ("high", high)):
        residual_ev = enterprise_value - fit_ev
        _check(residual_ev > 0,
               f"At the {label} end of {fit_leg.name}'s range ({fit_ev:,.0f}) the fit "
               f"leg alone exceeds the company's entire enterprise value "
               f"({enterprise_value:,.0f}). The residual is negative, which is not a "
               f"cheap segment -- it means the fit leg's range or the market figures "
               f"are wrong.")
        points.append(ImpliedPoint(
            fit_ev=fit_ev, fit_label=label, residual_ev=residual_ev,
            residual_multiple=residual_ev / residual_leg.revenue))

    return ImpliedResult(
        fit_leg=fit_leg, residual_leg=residual_leg, market_cap=market_cap,
        net_debt=net_debt, enterprise_value=enterprise_value, points=tuple(points))


@dataclass(frozen=True)
class Crossover:
    """Where the conclusion flips, expressed as a mark on the fit leg.

    `robust` is a yes/no, and on its own it understates what the analysis knows. A
    conclusion that survives until the fit leg is marked at the 84th percentile of its
    own peer range is in a very different position from one that flips at the median,
    yet both report as "not robust". This states the flip point, so a reader can judge
    the assumption that breaks the argument instead of taking the binary on trust.
    """
    benchmark: float          # the residual multiple being crossed
    benchmark_label: str
    fit_ev: float             # fit-leg EV at which the residual equals `benchmark`
    fit_multiple: float       # ...expressed as a multiple of the fit leg's revenue
    fit_peer_low: float
    fit_peer_high: float

    @property
    def within_fit_peer_range(self) -> bool:
        return self.fit_peer_low <= self.fit_multiple <= self.fit_peer_high

    @property
    def percentile_of_fit_range(self) -> float:
        """Where the flip point sits between the fit leg's cheapest and richest peer.
        Values outside 0-1 mean the flip requires a mark no peer supports."""
        span = self.fit_peer_high - self.fit_peer_low
        return (self.fit_multiple - self.fit_peer_low) / span if span else float("nan")

    def describe(self, fit_name: str, residual_name: str) -> str:
        pct = self.percentile_of_fit_range
        if not self.within_fit_peer_range:
            side = "richer" if self.fit_multiple > self.fit_peer_high else "cheaper"
            return (f"{residual_name} stays above {self.benchmark_label} unless "
                    f"{fit_name} is marked {side} than every peer in its own set "
                    f"({self.fit_multiple:.2f}x against a peer range of "
                    f"{self.fit_peer_low:.2f}x-{self.fit_peer_high:.2f}x). No mark the "
                    f"peer evidence supports breaks the conclusion.")
        return (f"{residual_name} is priced above {self.benchmark_label} unless "
                f"{fit_name} is worth more than {self.fit_multiple:.2f}x revenue "
                f"({self.fit_ev:,.0f}) -- the {pct:.0%} mark of {fit_name}'s own peer "
                f"range of {self.fit_peer_low:.2f}x-{self.fit_peer_high:.2f}x. The "
                f"conclusion holds below that mark and fails above it, so it rests on "
                f"{fit_name} not deserving a top-of-set multiple.")


def crossover(result: "ImpliedResult", benchmark: float | None = None,
              benchmark_label: str | None = None) -> Crossover:
    """The fit-leg mark at which the residual multiple equals `benchmark`.

    Defaults to the residual's richest peer multiple, which is the benchmark the
    headline claim ("priced above every peer") turns on. Solved directly rather than
    searched: residual_multiple = (EV - fit_ev) / residual_revenue, so the fit_ev that
    makes it equal the benchmark is EV - benchmark x residual_revenue.
    """
    r, f = result.residual_leg, result.fit_leg
    if benchmark is None:
        benchmark, benchmark_label = r.peer_multiple_high, "every peer in its set"
    fit_ev = result.enterprise_value - benchmark * r.revenue
    _check(f.revenue > 0, f"{f.name} has non-positive revenue; no crossover multiple.")
    return Crossover(
        benchmark=benchmark, benchmark_label=benchmark_label or f"{benchmark:.2f}x",
        fit_ev=fit_ev, fit_multiple=fit_ev / f.revenue,
        fit_peer_low=f.peer_multiple_low, fit_peer_high=f.peer_multiple_high)


def report(result: ImpliedResult) -> str:
    """The block the report reproduces. Every line that states a position against the
    peer range also states what that peer range is fit to support, because the whole
    risk in this argument is a reader treating a located multiple as a valuation."""
    r, f = result.residual_leg, result.fit_leg
    lo, hi = result.multiple_span
    out = [
        f"MARKET-IMPLIED MULTIPLE -- {r.name}",
        "",
        f"  Market cap          {result.market_cap:>20,.0f}",
        f"  Plus net debt       {result.net_debt:>20,.0f}",
        f"  = Enterprise value  {result.enterprise_value:>20,.0f}",
        "",
        f"  {f.name} is the only structurally fit leg (peer spread {f.spread:.1f}x "
        f"against a {DISQUALIFYING_SPREAD:.1f}x bar, peers: {f.peer_group}).",
        f"  Its EV range is subtracted from the above; the remainder is what the market "
        f"implicitly assigns to {r.name}.",
        "",
    ]
    for p in result.points:
        out.append(
            f"    {f.name} at {p.fit_label:<4} {p.fit_ev:>18,.0f}  ->  {r.name} "
            f"{p.residual_ev:>18,.0f}  =  {p.residual_multiple:.1f}x revenue  "
            f"({p.position(r)})")

    out += ["", f"  {r.name} peer multiples ({r.peer_group}): "
                f"{r.peer_multiple_low:.1f}x - {r.peer_multiple_high:.1f}x "
                f"(median {r.peer_multiple_median:.1f}x, spread {r.spread:.1f}x)"]

    positions = {p.position(r) for p in result.points}
    if result.robust:
        out.append(f"  The market's implied multiple sits {positions.pop()} at every "
                   f"point of {f.name}'s range ({lo:.1f}x - {hi:.1f}x). The conclusion "
                   f"does not depend on where in that range the fit leg is marked.")
    else:
        out.append(f"  NOT ROBUST: the implied multiple changes position across "
                   f"{f.name}'s range ({lo:.1f}x - {hi:.1f}x) -- {', '.join(sorted(positions))}. "
                   f"The conclusion is a function of where the fit leg is marked, so "
                   f"there is no finding here, only a choice.")

    x = crossover(result)
    out += ["", f"  FLIP POINT: {x.describe(f.name, r.name)}"]

    if not r.fit:
        out += [
            "",
            f"  WHAT THIS IS NOT: {r.name}'s peer set is disqualified from valuing the "
            f"segment (spread {r.spread:.1f}x exceeds {DISQUALIFYING_SPREAD:.1f}x), and "
            f"nothing here repairs that. This does NOT say {r.name} is worth some other "
            f"number and the market is wrong by the difference -- that claim would need "
            f"the peer median this project has already rejected. It says only where the "
            f"market's implied multiple falls within the range of multiples comparable "
            f"companies actually trade at. A location in a distribution, not a "
            f"valuation.",
        ]
    return "\n".join(out)


def assert_matches_upstream(valuationlab_threshold: float) -> None:
    """Fail loudly if ValuationLab's disqualification bar has moved away from the one
    mirrored here. A silent divergence would let this module call a leg fit that
    ValuationLab disqualifies, and the report would cite both."""
    if abs(valuationlab_threshold - DISQUALIFYING_SPREAD) > 1e-9:
        raise ImpliedError(
            f"ValuationLab disqualifies at {valuationlab_threshold}x; this module "
            f"mirrors {DISQUALIFYING_SPREAD}x. Reconcile them before publishing -- the "
            f"report cites both and they must agree on which legs are fit.")
