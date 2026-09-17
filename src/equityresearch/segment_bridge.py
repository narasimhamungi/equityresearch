"""
Segment revenue paths -> the consolidated revenue_growth driver.

WHY THIS IS THE ANALYTICALLY IMPORTANT PIECE
---------------------------------------------
ValuationLab's finding is that J&J does not value as one company: MedTech prices
cleanly against its own peer group, Innovative Medicine does not clear the same
dispersion bars against pharma peers. That is a statement about VALUATION METHOD.

This report's thesis has to be a statement about the BUSINESS, and it has to be its own
argument rather than a restatement of that method finding. The connection is here: if
the two segments are genuinely different businesses for valuation purposes, they are
different businesses for forecasting purposes too, and a single consolidated
`revenue_growth` driver applied to the whole company quietly assumes they move
together. They do not. A patent cliff hits Innovative Medicine; it does not touch
MedTech. An Abiomed synergy ramp lands in MedTech; it does not touch Innovative
Medicine.

So the analyst states a growth path per SEGMENT -- which is where the evidence
actually is, and where every catalyst and risk in the report is actually located --
and the consolidated driver Trellis needs is COMPUTED from those paths, not guessed at
the consolidated level. The consequence worth stating plainly: the consolidated growth
rate is then a derived output of the thesis rather than an input to it, and mix shift
falls out for free. If IM shrinks while MedTech compounds, consolidated growth
decelerates *and* the revenue mix moves toward MedTech automatically, because the
weights are recomputed from the projected segment revenues each year rather than held
at the base-year split.

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
It does not produce a segment margin effect. J&J discloses segment income before tax
but not segment gross margin or segment D&A (see ValuationLab's `segments.py`, which
refuses to build a segment EBITDA for the same reason). Only Innovative Medicine's
FY2025 segment pretax margin is available in this project's sources at all; MedTech's
is not. Deriving a consolidated gross-margin path from a mix shift would therefore
require inventing a segment gross margin, so `gross_margin` stays a separately stated,
separately evidenced flex -- not something this module silently implies.
"""

from __future__ import annotations

from dataclasses import dataclass

from .scenarios import Flex, ScenarioYear


class SegmentBridgeError(ValueError):
    pass


@dataclass(frozen=True)
class SegmentPath:
    """One segment's base-year revenue and its assumed growth for each forecast year."""
    name: str
    base_revenue: float
    growth: tuple[float, ...]
    source: str      # where base_revenue came from (a filing)
    rationale: str   # why this growth path -- the segment-level thesis, per year


def revenue_path(seg: SegmentPath) -> tuple[float, ...]:
    out, prior = [], seg.base_revenue
    for g in seg.growth:
        prior = prior * (1 + g)
        out.append(prior)
    return tuple(out)


def check_reconciles(segments: tuple[SegmentPath, ...], consolidated_revenue: float,
                     tolerance: float = 1.0) -> None:
    """Segment base revenues must sum to the consolidated base-year revenue Trellis
    pulled. A mis-keyed segment figure would otherwise produce a consolidated growth
    path that looks plausible and is wrong by the size of the error -- and nothing
    downstream would catch it, because the output is a growth RATE, which hides the
    level it came from."""
    total = sum(s.base_revenue for s in segments)
    if abs(total - consolidated_revenue) > tolerance:
        raise SegmentBridgeError(
            f"Segment revenues sum to {total:,.0f} against consolidated "
            f"{consolidated_revenue:,.0f} (diff {total - consolidated_revenue:,.0f}). "
            f"Either a segment is missing or a figure is mis-keyed; the consolidated "
            f"growth path derived from these would be wrong by that amount."
        )


def consolidated_growth_path(segments: tuple[SegmentPath, ...],
                             horizon: int) -> tuple[float, ...]:
    """Year-over-year consolidated growth implied by the segment paths.

    Weights are recomputed each year from projected segment revenue, not held at the
    base-year split -- which is the entire point. Holding base-year weights fixed would
    make a five-year divergence between two segments understate itself progressively,
    because the shrinking segment would keep its original weight the whole way.
    """
    if not segments:
        raise SegmentBridgeError("No segments supplied.")
    for s in segments:
        if len(s.growth) < horizon:
            raise SegmentBridgeError(
                f"Segment '{s.name}' has {len(s.growth)} growth years for a "
                f"{horizon}-year horizon. A segment silently held flat for the tail "
                f"is an assumption, so it must be stated explicitly, not defaulted."
            )
        if s.base_revenue <= 0:
            raise SegmentBridgeError(f"Segment '{s.name}' has non-positive revenue.")

    paths = {s.name: revenue_path(s) for s in segments}
    prior_total = sum(s.base_revenue for s in segments)
    out: list[float] = []
    for i in range(horizon):
        total = sum(paths[s.name][i] for s in segments)
        out.append(total / prior_total - 1.0)
        prior_total = total
    return tuple(out)


def mix_path(segments: tuple[SegmentPath, ...], horizon: int) -> tuple[dict[str, float], ...]:
    """Revenue weight per segment per year -- reported alongside the growth path
    because the mix shift is itself part of the thesis, not a side effect. A reader
    who accepts the growth path has implicitly accepted this mix, and should see it."""
    paths = {s.name: revenue_path(s) for s in segments}
    out = []
    for i in range(horizon):
        total = sum(paths[s.name][i] for s in segments)
        out.append({s.name: paths[s.name][i] / total for s in segments})
    return tuple(out)


def to_scenario_years(segments: tuple[SegmentPath, ...], horizon: int,
                      extra: dict[int, tuple[Flex, ...]] | None = None
                      ) -> tuple[ScenarioYear, ...]:
    """Build the per-year `revenue_growth` flexes, tagged `derived` because the
    consolidated number is computed rather than asserted -- the JUDGMENT lives in the
    segment paths, and each year's basis quotes the segment rationales that produced
    it, so the evidence tier is not laundered by the arithmetic.

    `extra` attaches other flexes (margin, R&D, debt) to the same years.
    """
    extra = extra or {}
    growth = consolidated_growth_path(segments, horizon)
    mix = mix_path(segments, horizon)
    years: list[ScenarioYear] = []
    for i in range(horizon):
        mix_str = ", ".join(f"{n} {w:.1%}" for n, w in sorted(mix[i].items()))
        rationales = "; ".join(
            f"{s.name} {s.growth[i]:+.1%} ({s.rationale})" for s in segments
        )
        basis = (f"Derived from segment paths: {rationales}. "
                 f"Implied revenue mix: {mix_str}. "
                 f"Base-year segment revenue: "
                 + " | ".join(f"{s.name} {s.source}" for s in segments))
        flexes = (Flex("revenue_growth", "set", growth[i], "derived", basis),
                  *extra.get(i + 1, ()))
        years.append(ScenarioYear(offset=i + 1, flexes=flexes,
                                  note=f"consolidated {growth[i]:+.2%}; mix {mix_str}"))
    return tuple(years)
