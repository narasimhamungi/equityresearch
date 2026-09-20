import pytest

from equityresearch.share_path import (
    ShareCountError, build_share_path, circularity_warning, render,
)

OPENING = 2_429_400_000.0
PRICE = 267.20


def _fc(*buybacks, start=2026):
    return {start + i: {"buybacks": b, "net_income": 22_000e6}
            for i, b in enumerate(buybacks)}


def test_share_count_falls_as_buybacks_accumulate():
    """The defect: the runner divided every year by a FIXED FY2025 count while the
    model was sweeping cash into repurchases, understating EPS progressively."""
    path = build_share_path(_fc(5e9, 5e9, 5e9), OPENING, PRICE)
    ends = [p.shares_end for p in path.points]
    assert ends[0] > ends[1] > ends[2]
    assert path.points[0].shares_retired == pytest.approx(5e9 / PRICE)
    assert path.total_reduction == pytest.approx(3 * 5e9 / PRICE / OPENING, rel=1e-6)


def test_weighted_average_sits_between_opening_and_closing():
    """Repurchases happen through the year. Using the closing count would overstate the
    reduction and flatter EPS by about half a year of buybacks, every year."""
    path = build_share_path(_fc(5e9, 5e9), OPENING, PRICE)
    wa = path.shares_for(2026)
    assert path.points[0].shares_end < wa < OPENING
    assert wa == pytest.approx((OPENING + path.points[0].shares_end) / 2)


def test_weighted_average_of_a_later_year_uses_the_prior_years_close():
    path = build_share_path(_fc(5e9, 5e9), OPENING, PRICE)
    expected = (path.points[0].shares_end + path.points[1].shares_end) / 2
    assert path.shares_for(2027) == pytest.approx(expected)


def test_eps_understatement_is_material_by_the_final_year():
    """Quantifies what the fixed-count EPS line was getting wrong. At $6bn of buybacks a
    year against J&J's ~$26.5bn FY2030 net income, the fixed count understates final-year
    EPS by 4.3% -- about $0.47 a share on $10.91. Not enormous, and not nothing: it is
    larger than the gap between the Base and Bull cases in several years, so it would
    distort the comparison a reader actually cares about.

    The figure is asserted rather than bounded loosely, so a change in the arithmetic
    shows up here instead of passing under a generous threshold."""
    path = build_share_path(_fc(*[6e9] * 5), OPENING, PRICE)
    ni = 26_500e6
    fixed, actual = ni / OPENING, ni / path.shares_for(2030)
    assert actual > fixed
    assert (actual / fixed - 1) == pytest.approx(0.0434, abs=0.001)
    assert path.total_reduction == pytest.approx(0.0462, abs=0.001)


def test_no_buybacks_leaves_the_count_flat():
    path = build_share_path(_fc(0.0, 0.0), OPENING, PRICE)
    assert path.total_reduction == 0.0
    assert path.shares_for(2026) == OPENING


def test_negative_buybacks_are_floored_not_treated_as_issuance():
    """A negative sweep is not share issuance -- modelling it as such would invent
    dilution the forecast never expressed."""
    path = build_share_path(_fc(-2e9, 3e9), OPENING, PRICE)
    assert path.points[0].shares_retired == 0.0


def test_a_missing_repurchase_price_is_refused():
    """There is no filed answer, so it must be stated rather than defaulted behind the
    reader's back."""
    with pytest.raises(ShareCountError, match="repurchase price is required"):
        build_share_path(_fc(5e9), OPENING, 0.0)


def test_buybacks_exceeding_the_share_base_are_refused():
    with pytest.raises(ShareCountError, match="forecast or the price is wrong"):
        build_share_path(_fc(900e9), OPENING, PRICE)


def test_non_positive_opening_count_refused():
    with pytest.raises(ShareCountError, match="must be positive"):
        build_share_path(_fc(5e9), 0.0, PRICE)


# --- the circularity this report cannot avoid ------------------------------------

def test_repurchasing_at_the_disputed_price_is_flagged():
    """If the thesis says the stock is expensive, crediting the case with buybacks at
    that price flatters exactly the scenario that says the price is wrong."""
    path = build_share_path(_fc(5e9), OPENING, PRICE)
    warning = circularity_warning(path, market_price=PRICE, thesis_says_expensive=True)
    assert "CIRCULARITY" in warning
    assert "destroy value per share" in warning


def test_repurchasing_below_the_disputed_price_is_not_flagged():
    path = build_share_path(_fc(5e9), OPENING, 200.0)
    assert circularity_warning(path, PRICE, thesis_says_expensive=True) == ""


def test_no_warning_when_the_thesis_makes_no_claim_about_price():
    path = build_share_path(_fc(5e9), OPENING, PRICE)
    assert circularity_warning(path, PRICE, thesis_says_expensive=False) == ""


def test_render_discloses_the_unmodelled_equity_compensation_offset():
    text = render(build_share_path(_fc(5e9, 5e9), OPENING, PRICE), "Bull")
    assert "Equity compensation issuance is NOT modelled" in text
    assert "optimistic" in text
    assert "267.20" in text


# --- the sweep assumes no acquisitions -------------------------------------------

def test_a_buyback_pace_far_above_actual_is_flagged():
    """J&J's real position: FY2025 buybacks $6.0bn against a modelled $11-15bn a year,
    because sweep_to_buybacks has no acquisition line and J&J is a serial acquirer
    (Abiomed ~$17bn, Shockwave ~$13bn)."""
    from equityresearch.share_path import acquisition_blind_warning
    path = build_share_path(_fc(17.3e9, 12.1e9, 13.0e9, 13.8e9, 14.7e9), OPENING, PRICE)
    warning = acquisition_blind_warning(path, last_actual_buybacks=6.0e9)
    assert "ACQUISITION-BLIND" in warning
    assert "OVERSTATES" in warning and "UNDERSTATES" in warning
    assert "no acquisition rate is invented" in warning.replace("\n", " ")


def test_the_first_year_drawdown_is_excluded_from_the_pace():
    """Year one sweeps the cash balance down to the floor as well as that year's flow,
    so it is a one-off. Including it would overstate the ongoing pace and make the
    warning fire on companies whose steady-state repurchases are fine."""
    from equityresearch.share_path import acquisition_blind_warning
    path = build_share_path(_fc(30e9, 6e9, 6e9), OPENING, PRICE)
    assert acquisition_blind_warning(path, last_actual_buybacks=6.0e9) == ""


def test_a_pace_in_line_with_actual_is_not_flagged():
    from equityresearch.share_path import acquisition_blind_warning
    path = build_share_path(_fc(6e9, 6.5e9, 7e9), OPENING, PRICE)
    assert acquisition_blind_warning(path, last_actual_buybacks=6.0e9) == ""


def test_no_warning_without_a_historical_figure_to_compare_against():
    from equityresearch.share_path import acquisition_blind_warning
    path = build_share_path(_fc(20e9, 20e9), OPENING, PRICE)
    assert acquisition_blind_warning(path, last_actual_buybacks=0.0) == ""
