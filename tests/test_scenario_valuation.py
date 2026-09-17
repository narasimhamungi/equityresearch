import dataclasses
from dataclasses import dataclass

import pytest

from equityresearch.scenario_valuation import (
    TERMINAL_DOMINANCE_THRESHOLD, ScenarioValuationError, decompose, report,
    value_scenario,
)


@dataclass(frozen=True)
class FakeDCF:
    """Stands in for ValuationLab's DCFResult. Only the five fields this module reads
    are present, which is the point of the Protocol -- the bridge must not quietly
    depend on the rest of that class."""
    pv_explicit_fcf: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    implied_share_price: float


DILUTED, BASIC = 2_429_400_000.0, 2_407_400_000.0


def _dcf(explicit, terminal, net_debt=19_729e6):
    ev = explicit + terminal
    eq = ev - net_debt
    return FakeDCF(explicit, terminal, ev, net_debt, eq, eq / BASIC)


def _value(name, explicit, terminal, insolvent=()):
    return value_scenario(name, _dcf(explicit, terminal), DILUTED, BASIC, insolvent)


# J&J's actual shape: terminal value 82% of EV.
BASE = _value("Base", 110e9, 500e9)


def test_terminal_share_and_disqualification_match_valuationlabs_bar():
    assert BASE.terminal_share == pytest.approx(0.8197, abs=0.001)
    assert BASE.disqualified
    fine = _value("Base", 400e9, 300e9)
    assert fine.terminal_share < TERMINAL_DOMINANCE_THRESHOLD
    assert not fine.disqualified


def test_per_share_is_recomputed_on_diluted_not_taken_from_the_dcf():
    """DCFResult divides by the provider's BASIC count. Taking that figure through
    would apply the wrong denominator to every per-share number in the report."""
    v = BASE
    assert v.per_share_diluted == pytest.approx(v.equity_value / DILUTED)
    assert v.per_share_basic == pytest.approx(v.equity_value / BASIC)
    assert v.per_share_diluted < v.per_share_basic, "more shares, less per share"


def test_decomposition_is_an_identity_not_an_estimate():
    """EV is exactly explicit + terminal, so the two deltas must sum to the EV delta.
    If they ever do not, the DCF's own arithmetic is broken, not this split."""
    bull = _value("Bull", 118e9, 545e9)
    d = decompose(BASE, bull)
    assert d.explicit_delta + d.terminal_delta == pytest.approx(d.ev_delta)


def test_a_terminal_dominated_spread_is_flagged_as_a_decorative_path():
    """The finding this module was built to surface. If a scenario's whole difference
    from Base arrives through terminal value -- which Gordon growth reads off the final
    year alone -- then the dated five-year path is not what moved the number."""
    bull = _value("Bull", 111e9, 560e9)          # +1bn explicit, +60bn terminal
    d = decompose(BASE, bull)
    assert d.terminal_channel_share == pytest.approx(60 / 61, abs=0.01)
    assert d.path_is_decorative


def test_a_spread_the_explicit_period_actually_drives_is_not_flagged():
    bull = _value("Bull", 150e9, 510e9)          # +40bn explicit, +10bn terminal
    d = decompose(BASE, bull)
    assert d.terminal_channel_share == pytest.approx(0.2, abs=0.01)
    assert not d.path_is_decorative


def test_offsetting_channels_produce_a_share_outside_zero_to_one():
    """Explicit and terminal can pull opposite ways. A share above 1 or below 0 is
    informative rather than an error -- it means one channel is cancelling the other."""
    odd = _value("Bear", 95e9, 520e9)            # -15bn explicit, +20bn terminal
    d = decompose(BASE, odd)
    assert d.ev_delta == pytest.approx(5e9)
    assert d.terminal_channel_share == pytest.approx(4.0, abs=0.01)
    assert d.path_is_decorative


def test_zero_ev_delta_gives_nan_not_a_division_error():
    same = _value("Bull", 120e9, 490e9)          # +10bn explicit, -10bn terminal
    d = decompose(BASE, same)
    assert d.ev_delta == pytest.approx(0.0)
    share = d.terminal_channel_share
    assert share != share, "expected NaN"
    assert not d.path_is_decorative, "NaN must not be read as decorative"


# --- report content -------------------------------------------------------------

def test_report_refuses_to_call_any_figure_a_target_price():
    text = report(BASE, (_value("Bull", 111e9, 560e9), _value("Bear", 100e9, 440e9)))
    assert "not target prices" in text
    assert "none of them is a target price" in text
    assert "DISQUALIFIED" in text


def test_report_states_the_path_is_decorative_when_it_is():
    text = report(BASE, (_value("Bull", 111e9, 560e9),))
    assert "not what moves these numbers" in text
    assert "case for the BUSINESS" in text


def test_report_credits_the_path_when_the_explicit_period_drives_the_spread():
    text = report(BASE, (_value("Bull", 150e9, 510e9),))
    assert "doing real work" in text
    assert "not what moves these numbers" not in text


def test_report_surfaces_an_insolvent_scenario():
    """A downside path that cannot fund itself is an economic finding, and the equity
    value shown does not price it."""
    text = report(BASE, (_value("Bear", 100e9, 440e9, insolvent=(2027, 2028)),))
    assert "cannot fund itself in (2027, 2028)" in text
    assert "does not price it" in text


def test_report_omits_the_disqualification_when_no_case_trips_it():
    ok = _value("Base", 400e9, 300e9)
    text = report(ok, (_value("Bull", 420e9, 310e9),))
    assert "DISQUALIFIED" not in text
    assert "terminal-dominance bar" not in text


# --- guards ----------------------------------------------------------------------

def test_non_positive_enterprise_value_is_refused():
    with pytest.raises(ScenarioValuationError, match="meaningless, not merely low"):
        value_scenario("Bear", _dcf(-50e9, 10e9), DILUTED, BASIC)


@pytest.mark.parametrize("d,b", [(0, BASIC), (DILUTED, 0), (-1, BASIC)])
def test_non_positive_share_counts_refused(d, b):
    with pytest.raises(ScenarioValuationError, match="must be positive"):
        value_scenario("Base", _dcf(110e9, 500e9), d, b)


def test_decomposing_a_scenario_against_itself_is_refused():
    with pytest.raises(ScenarioValuationError, match="against itself"):
        decompose(BASE, dataclasses.replace(BASE))
