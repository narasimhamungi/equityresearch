import dataclasses

import pytest

from equityresearch.market_implied import (
    DISQUALIFYING_SPREAD, ImpliedError, Leg, assert_matches_upstream,
    implied_residual, report,
)

# Live figures from ValuationLab's SOTP run (snapshots a34baff, market 2026-09-15).
CONSOLIDATED = 94_193e6
NET_DEBT = 19_729e6
PRICE, BASIC_SHARES = 267.20, 2_409_898_597

MEDTECH = Leg(name="MedTech", revenue=33_792e6, peer_group="MDT, BDX, SYK, BSX",
              peer_multiple_low=3.096, peer_multiple_median=3.794,
              peer_multiple_high=4.730)
INNOVATIVE = Leg(name="Innovative Medicine", revenue=60_401e6,
                 peer_group="PFE, MRK, ABBV, BMY", peer_multiple_low=3.379,
                 peer_multiple_median=4.714, peer_multiple_high=8.570)


def _run(market_cap=PRICE * BASIC_SHARES, net_debt=NET_DEBT,
         fit=MEDTECH, residual=INNOVATIVE):
    return implied_residual(market_cap, net_debt, fit, residual, CONSOLIDATED)


# --- fitness classification mirrors ValuationLab's own verdicts -----------------

def test_the_two_legs_classify_the_way_valuationlab_classified_them():
    assert MEDTECH.fit and MEDTECH.spread == pytest.approx(1.53, abs=0.02)
    assert not INNOVATIVE.fit and INNOVATIVE.spread == pytest.approx(2.54, abs=0.02)


def test_threshold_mismatch_with_upstream_is_fatal():
    assert_matches_upstream(2.0)
    with pytest.raises(ImpliedError, match="Reconcile them"):
        assert_matches_upstream(2.5)


# --- the headline finding, and the boundary that qualifies it ------------------

def test_market_implies_a_multiple_above_the_pharma_peer_median_at_every_mark():
    """The part of the finding that does hold everywhere."""
    result = _run()
    assert all(p.residual_multiple > INNOVATIVE.peer_multiple_median
               for p in result.points)


def test_the_finding_is_NOT_robust_across_the_fit_leg_range():
    """The correction this module was built to catch.

    Eyeballed, the claim was 'the market prices Innovative Medicine above every pharma
    peer.' It holds at MedTech's low and median marks (9.3x and 8.9x against a peer max
    of 8.6x) and fails at MedTech's high mark, where the implied multiple falls to 8.3x
    -- inside the peer range. A conclusion that depends on where the fit leg is marked
    is a conclusion about that choice, so the report must state the boundary rather
    than the headline."""
    result = _run()
    assert not result.robust
    by_label = {p.fit_label: p for p in result.points}
    assert by_label["low"].position(INNOVATIVE) == "above peer max"
    assert by_label["mid"].position(INNOVATIVE) == "above peer max"
    assert by_label["high"].position(INNOVATIVE) == "above peer median, within range"
    lo, hi = result.multiple_span
    assert (lo, hi) == pytest.approx((8.34, 9.26), abs=0.02)


def test_report_says_not_robust_rather_than_stating_the_headline():
    text = report(_run())
    assert "NOT ROBUST" in text
    assert "only a choice" in text


def test_report_carries_the_what_this_is_not_disclaimer_for_an_unfit_residual():
    """The risk in this whole argument is a reader treating a located multiple as a
    valuation. If the residual's peer set is disqualified, the output must say so."""
    text = report(_run())
    assert "WHAT THIS IS NOT" in text
    assert "not a valuation" in text.lower()
    assert "2.5x" in text or "2.54x" in text


def test_a_fit_residual_gets_no_disclaimer():
    tight = dataclasses.replace(INNOVATIVE, peer_multiple_low=4.0,
                                peer_multiple_median=5.0, peer_multiple_high=7.0)
    assert "WHAT THIS IS NOT" not in report(_run(residual=tight))


# --- robustness detection ------------------------------------------------------

def test_robust_when_the_position_holds_at_every_mark():
    """A market cap high enough to put the residual above peer max even at the fit
    leg's richest mark -- then the conclusion no longer depends on the choice."""
    result = _run(market_cap=750e9)
    assert result.robust
    assert all(p.position(INNOVATIVE) == "above peer max" for p in result.points)
    text = report(result)
    assert "does not depend on where in that range" in text


def test_multiple_span_is_ordered_low_to_high():
    lo, hi = _run().multiple_span
    assert lo < hi


def test_a_richer_fit_leg_leaves_less_for_the_residual():
    """Direction check: the inversion is a subtraction, so marking the fit leg up must
    move the residual down. A sign error here would invert the entire argument."""
    points = {p.fit_label: p.residual_multiple for p in _run().points}
    assert points["low"] > points["mid"] > points["high"]


# --- the three structural guards ------------------------------------------------

def test_an_unfit_anchor_is_refused():
    """The inversion subtracts this leg's EV; an indefensible anchor makes the residual
    indefensible, and the output would look identical to a valid one."""
    with pytest.raises(ImpliedError, match="not structurally fit"):
        _run(fit=INNOVATIVE, residual=MEDTECH)


def test_a_missing_segment_is_refused_not_absorbed():
    """Drop a segment and its whole value silently lands in the residual, inflating the
    implied multiple by exactly the amount that went missing."""
    with pytest.raises(ImpliedError, match="pushed into the\n *residual|pushed into the"):
        implied_residual(PRICE * BASIC_SHARES, NET_DEBT, MEDTECH, INNOVATIVE,
                         consolidated_revenue=110_000e6)


def test_same_segment_twice_is_refused():
    with pytest.raises(ImpliedError, match="same segment"):
        implied_residual(PRICE * BASIC_SHARES, NET_DEBT, MEDTECH, MEDTECH,
                         consolidated_revenue=MEDTECH.revenue * 2)


def test_a_negative_residual_is_refused_not_reported_as_cheap():
    """If the fit leg alone exceeds the company's EV, the residual goes negative. That
    is not a cheap segment -- it means the inputs are wrong, and reporting a negative
    multiple would look like a finding."""
    with pytest.raises(ImpliedError, match="not a cheap segment"):
        _run(market_cap=50e9)


def test_zero_revenue_residual_is_refused():
    empty = dataclasses.replace(INNOVATIVE, revenue=0.0)
    with pytest.raises(ImpliedError, match="non-positive revenue"):
        implied_residual(PRICE * BASIC_SHARES, NET_DEBT, MEDTECH, empty,
                         consolidated_revenue=MEDTECH.revenue)


# --- net debt sign convention ---------------------------------------------------

def test_net_debt_is_added_to_market_cap_to_reach_enterprise_value():
    """Same convention ValuationLab uses bridging its SOTP total back to a price. A
    sign flip here moves EV by twice net debt and the implied multiple with it."""
    result = _run()
    assert result.enterprise_value == pytest.approx(PRICE * BASIC_SHARES + NET_DEBT)


def test_a_net_cash_company_has_enterprise_value_below_market_cap():
    result = _run(net_debt=-15e9)
    assert result.enterprise_value < result.market_cap


# --- crossover: how far the conclusion is from flipping -------------------------

def test_crossover_locates_the_flip_point_on_the_fit_leg():
    """`robust` is a binary and on its own it understates what is known. A conclusion
    surviving until MedTech is marked at the 84th percentile of its own peer range is
    in a very different position from one flipping at the median -- both report as
    'not robust'."""
    from equityresearch.market_implied import crossover
    result = _run(market_cap=PRICE * 2_429_400_000)   # diluted
    x = crossover(result)

    assert x.benchmark == INNOVATIVE.peer_multiple_high
    assert x.fit_multiple == pytest.approx(4.475, abs=0.01)
    assert x.within_fit_peer_range
    assert x.percentile_of_fit_range == pytest.approx(0.844, abs=0.01)


def test_crossover_solves_the_same_point_the_scan_brackets():
    """Cross-check: the solved flip point must sit between the marks where the scan
    shows the position changing -- above MedTech's median, at or below its high."""
    from equityresearch.market_implied import crossover
    result = _run(market_cap=PRICE * 2_429_400_000)
    x = crossover(result)
    assert MEDTECH.peer_multiple_median < x.fit_multiple <= MEDTECH.peer_multiple_high


def test_crossover_outside_the_fit_peer_range_means_no_supported_mark_breaks_it():
    """When the flip requires a mark richer than every peer in the fit leg's own set,
    the peer evidence does not contain an assumption that breaks the conclusion --
    which is the robust case, reached from the other direction."""
    from equityresearch.market_implied import crossover
    result = _run(market_cap=750e9)
    x = crossover(result)
    assert result.robust
    assert not x.within_fit_peer_range
    assert x.percentile_of_fit_range > 1.0
    text = x.describe("MedTech", "Innovative Medicine")
    assert "richer than every peer" in text and "No mark the peer evidence supports" in text


def test_crossover_accepts_an_explicit_benchmark():
    """The median is the other benchmark worth testing -- it is the claim that survived
    when the peer-max one did not."""
    from equityresearch.market_implied import crossover
    result = _run(market_cap=PRICE * 2_429_400_000)
    x = crossover(result, benchmark=INNOVATIVE.peer_multiple_median,
                  benchmark_label="the pharma peer median")
    assert x.fit_multiple > MEDTECH.peer_multiple_high, (
        "flipping the median claim would need MedTech richer than any peer")
    assert not x.within_fit_peer_range


def test_report_states_the_flip_point():
    text = report(_run(market_cap=PRICE * 2_429_400_000))
    assert "FLIP POINT" in text
    assert "4.48x" in text and "84%" in text
