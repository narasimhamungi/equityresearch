import pytest

from equityresearch.scenarios import Flex, Scenario, build_driver_path
from equityresearch.segment_bridge import (
    SegmentBridgeError, SegmentPath, check_reconciles, consolidated_growth_path,
    mix_path, revenue_path, to_scenario_years,
)
from tests.test_scenarios import BASE_DRIVERS

# FY2025 figures as cited in ValuationLab's segments.py.
IM_REV, MT_REV, CONSOLIDATED = 60_401e6, 33_792e6, 94_193e6


def _segs(im_growth, mt_growth):
    return (
        SegmentPath("Innovative Medicine", IM_REV, im_growth,
                    "J&J FY2025 10-K segment sales table", "LOE erosion"),
        SegmentPath("MedTech", MT_REV, mt_growth,
                    "J&J FY2025 10-K, consolidated less IM", "Abiomed ramp"),
    )


def test_weights_are_recomputed_each_year_not_held_at_the_base_split():
    """The core claim. With base-year weights held fixed, a constant per-segment growth
    pair gives a constant consolidated rate. Recomputing weights makes consolidated
    growth drift toward the faster segment -- which is the mix shift the thesis is
    about."""
    segs = _segs((-0.06,) * 5, (0.07,) * 5)
    path = consolidated_growth_path(segs, 5)
    static = IM_REV / CONSOLIDATED * -0.06 + MT_REV / CONSOLIDATED * 0.07
    assert path[0] == pytest.approx(static, abs=1e-12)
    assert path[4] > path[0], "consolidated growth must drift toward the grower"
    assert len(set(round(g, 8) for g in path)) == 5, "no year may repeat"


def test_mix_shifts_toward_the_growing_segment():
    mix = mix_path(_segs((-0.06,) * 5, (0.07,) * 5), 5)
    base_weight = MT_REV / CONSOLIDATED
    assert mix[0]["MedTech"] > base_weight, "year 1 is already post-growth"
    assert mix[4]["MedTech"] > mix[0]["MedTech"]
    assert mix[4]["MedTech"] - base_weight > 0.05, (
        "a 13pt annual growth gap over five years must move the mix materially, "
        "or the weights are not actually being recomputed")
    assert all(abs(sum(m.values()) - 1.0) < 1e-12 for m in mix)


def test_flat_segments_reproduce_their_own_growth_rate():
    """Degenerate check: identical segment growth must give exactly that consolidated
    rate in every year, with no mix artefact."""
    path = consolidated_growth_path(_segs((0.03,) * 5, (0.03,) * 5), 5)
    assert all(g == pytest.approx(0.03) for g in path)


def test_revenue_path_compounds():
    seg = SegmentPath("X", 100.0, (0.10, 0.10), "s", "r")
    assert revenue_path(seg) == pytest.approx((110.0, 121.0))


def test_segments_must_reconcile_to_consolidated_revenue():
    check_reconciles(_segs((0.0,) * 5, (0.0,) * 5), CONSOLIDATED, tolerance=1.0)
    with pytest.raises(SegmentBridgeError, match="mis-keyed"):
        check_reconciles(_segs((0.0,) * 5, (0.0,) * 5), 90_000e6)


def test_short_growth_tuple_is_rejected_rather_than_held_flat():
    """A segment silently extended flat is an unstated assumption."""
    with pytest.raises(SegmentBridgeError, match="stated explicitly"):
        consolidated_growth_path(_segs((-0.06,) * 3, (0.07,) * 5), 5)


def test_derived_flexes_carry_the_segment_rationales_and_the_implied_mix():
    """The evidence tier must not be laundered: the consolidated number is `derived`,
    but its basis has to expose the segment judgments underneath it."""
    years = to_scenario_years(_segs((-0.06,) * 5, (0.07,) * 5), 5)
    basis = years[0].flexes[0].basis
    assert "Innovative Medicine -6.0% (LOE erosion)" in basis
    assert "MedTech +7.0% (Abiomed ramp)" in basis
    assert "Implied revenue mix" in basis and "10-K" in basis
    assert years[0].flexes[0].kind == "derived"


def test_extra_flexes_attach_to_the_right_year():
    extra = {2: (Flex("rnd_pct_revenue", "delta", 0.01, "judgment", "pipeline defence"),)}
    years = to_scenario_years(_segs((-0.06,) * 5, (0.07,) * 5), 5, extra=extra)
    assert len(years[1].flexes) == 2
    assert years[1].flexes[1].driver == "rnd_pct_revenue"
    assert len(years[0].flexes) == 1


def test_output_feeds_the_scenario_engine_end_to_end():
    scen = Scenario("Bear", "IM erodes, MedTech compounds",
                    to_scenario_years(_segs((-0.06,) * 5, (0.07,) * 5), 5))
    path = build_driver_path(BASE_DRIVERS, scen, 5)
    assert path[0].revenue_growth != path[4].revenue_growth
    assert all(d.gross_margin == BASE_DRIVERS.gross_margin for d in path)


def test_non_positive_segment_revenue_rejected():
    with pytest.raises(SegmentBridgeError, match="non-positive"):
        consolidated_growth_path(
            (SegmentPath("X", 0.0, (0.0,) * 5, "s", "r"),), 5)
