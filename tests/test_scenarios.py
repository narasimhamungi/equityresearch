import dataclasses

import pytest
from trellis.forecast import Drivers

from equityresearch.scenarios import (
    UNSOURCED, Flex, Scenario, ScenarioError, ScenarioYear, build_driver_path,
    provenance_table, run_scenario, tier_mix,
)

BASE_DRIVERS = Drivers(
    revenue_growth=0.04, gross_margin=0.68, sga_pct_revenue=0.24, tax_rate=0.18,
    ar_days=60.0, inventory_days=120.0, ap_days=70.0, capex_pct_revenue=0.04,
    da_pct_revenue=0.05, interest_rate=0.035, debt_repayment=0.0,
    dividend_payout_ratio=0.50, rnd_pct_revenue=0.16, dividend_growth_rate=0.05,
)

PRIOR = {
    "revenue": 94_193.0, "net_income": 14_000.0, "dividends_paid": 12_000.0,
    "long_term_debt": 35_000.0, "ppe_net": 22_000.0, "total_assets": 180_000.0,
    "total_liabilities": 105_000.0, "stockholders_equity": 75_000.0,
    "cash_and_equivalents": 20_000.0, "accounts_receivable": 16_000.0,
    "inventory": 12_000.0, "accounts_payable": 10_000.0, "retained_earnings": 140_000.0,
}
TABLE = {2025: PRIOR}


def _flex(driver="revenue_growth", mode="delta", value=-0.03, kind="judgment",
          basis="test basis"):
    return Flex(driver=driver, mode=mode, value=value, kind=kind, basis=basis)


# --- the core claim: paths, not flat tilts -------------------------------------

def test_driver_path_varies_by_year_and_returns_base_where_unflexed():
    """The whole reason this module exists. A dataclasses.replace scenario gives one
    Drivers for five years; this gives five, and the unflexed years are the base
    object itself, so Base-case runs the identical code path."""
    scen = Scenario(
        name="Bear", thesis="dated erosion",
        years=(
            ScenarioYear(1, (_flex(value=-0.05),), note="LOE year"),
            ScenarioYear(2, (_flex(value=-0.02),), note="trough"),
        ),
    )
    path = build_driver_path(BASE_DRIVERS, scen, horizon=5)
    assert len(path) == 5
    assert path[0].revenue_growth == pytest.approx(-0.01)
    assert path[1].revenue_growth == pytest.approx(0.02)
    assert path[2] is BASE_DRIVERS and path[4] is BASE_DRIVERS


def test_deltas_do_not_compound_across_years():
    """Explicitly guarded because the opposite convention is the intuitive one and
    silently turns '-150bp for three years' into -450bp by year three."""
    scen = Scenario(
        name="Bear", thesis="t",
        years=tuple(ScenarioYear(i, (_flex(value=-0.015),)) for i in (1, 2, 3)),
    )
    path = build_driver_path(BASE_DRIVERS, scen, horizon=3)
    assert all(d.revenue_growth == pytest.approx(0.025) for d in path)


def test_set_mode_ignores_the_base_level():
    scen = Scenario(name="Bull", thesis="t",
                    years=(ScenarioYear(1, (_flex(mode="set", value=0.09),)),))
    assert build_driver_path(BASE_DRIVERS, scen, 1)[0].revenue_growth == pytest.approx(0.09)


def test_empty_scenario_reproduces_the_base_forecast_exactly():
    """Base case must not be a separate implementation, or the three cases aren't
    comparable."""
    from trellis.forecast import run_forecast
    base = run_forecast(TABLE, 2025, BASE_DRIVERS, years=5)
    run = run_scenario(TABLE, 2025, BASE_DRIVERS, Scenario("Base", "unflexed"), 5)
    for year in base:
        assert run.forecast[year]["revenue"] == pytest.approx(base[year]["revenue"])
        assert run.forecast[year]["net_income"] == pytest.approx(base[year]["net_income"])


# --- provenance separation ------------------------------------------------------

def test_scenario_does_not_pollute_trellis_sourced_override_provenance():
    """A forward hypothesis must never land in a field documented as a cited
    historical measurement."""
    base = dataclasses.replace(
        BASE_DRIVERS, overrides_applied=("interest_rate = 0.0350 -- 10-K debt note",),
        assumptions=("other assets carried flat",),
    )
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(),)),))
    path = build_driver_path(base, scen, 1)
    assert path[0].overrides_applied == base.overrides_applied
    assert path[0].assumptions == base.assumptions


def test_tier_mix_exposes_a_judgment_only_downside_case():
    scen = Scenario("Bear", "t", (ScenarioYear(1, (
        _flex(kind="judgment"),
        _flex(driver="gross_margin", kind="judgment"),
    )),))
    assert tier_mix(scen) == {"derived": 0, "sourced": 0, "judgment": 2}


def test_provenance_table_reproduces_every_basis():
    scen = Scenario("Bear", "erosion", (ScenarioYear(
        1, (_flex(kind="sourced", basis="Stelara US biosimilar entry, 10-K item 1A"),),
        note="LOE"),))
    out = provenance_table(scen)
    assert "Stelara US biosimilar entry" in out and "sourced" in out and "LOE" in out


# --- validation: fail loudly, never silently -----------------------------------

def test_typo_in_driver_name_is_rejected_not_ignored():
    """dataclasses.replace would raise, but a dict-merge implementation would not --
    and a silently dropped flex is a scenario that lies about what it modelled."""
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(driver="revenue_grwoth"),)),))
    with pytest.raises(ScenarioError, match="not a flexable driver"):
        build_driver_path(BASE_DRIVERS, scen, 5)


@pytest.mark.parametrize("field", ["dividend_policy", "capital_return_policy",
                                   "assumptions", "overrides_applied", "years_used"])
def test_mechanism_and_provenance_fields_are_not_flexable(field):
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(driver=field),)),))
    with pytest.raises(ScenarioError, match="not a flexable driver"):
        build_driver_path(BASE_DRIVERS, scen, 5)


def test_unsourced_placeholder_blocks_the_run_and_names_what_is_missing():
    scen = Scenario("Bear", "t", (ScenarioYear(1, (
        _flex(basis=f"{UNSOURCED}: talc settlement NPV needs a filing cite"),)),))
    with pytest.raises(ScenarioError) as e:
        build_driver_path(BASE_DRIVERS, scen, 5)
    assert "talc settlement NPV" in str(e.value)


def test_missing_basis_is_rejected():
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(basis="   "),)),))
    with pytest.raises(ScenarioError, match="no basis"):
        build_driver_path(BASE_DRIVERS, scen, 5)


def test_same_driver_flexed_twice_in_one_year_is_ambiguous_and_rejected():
    scen = Scenario("Bear", "t", (ScenarioYear(
        1, (_flex(value=-0.02), _flex(value=-0.01))),))
    with pytest.raises(ScenarioError, match="flexed twice"):
        build_driver_path(BASE_DRIVERS, scen, 5)


def test_year_beyond_horizon_is_rejected_rather_than_dropped():
    scen = Scenario("Bear", "t", (ScenarioYear(7, (_flex(),)),))
    with pytest.raises(ScenarioError, match="outside horizon"):
        build_driver_path(BASE_DRIVERS, scen, 5)


def test_duplicate_year_offsets_rejected():
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(),)),
                                  ScenarioYear(1, (_flex(driver="gross_margin"),))))
    with pytest.raises(ScenarioError, match="duplicate year offset"):
        build_driver_path(BASE_DRIVERS, scen, 5)


def test_scenario_without_a_thesis_is_rejected():
    with pytest.raises(ScenarioError, match="stated thesis"):
        build_driver_path(BASE_DRIVERS, Scenario("Bear", ""), 5)


@pytest.mark.parametrize("bad", [("mode", "ramp"), ("kind", "vibes")])
def test_bad_enum_values_rejected(bad):
    field, value = bad
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(**{field: value}),)),))
    with pytest.raises(ScenarioError):
        build_driver_path(BASE_DRIVERS, scen, 5)


# --- the checks that must survive a varying-driver path ------------------------

def test_reconciliation_holds_when_drivers_change_mid_path():
    """This module introduces a new way to break Trellis's cash-plug invariant --
    changing drivers between years, which run_forecast never does. If the invariant
    only held for constant drivers, it would fail here."""
    scen = Scenario("Bear", "t", years=tuple(
        ScenarioYear(i, (_flex(value=-0.02 * i),
                         _flex(driver="gross_margin", value=-0.01 * i)))
        for i in (1, 2, 3, 4, 5)))
    run = run_scenario(TABLE, 2025, BASE_DRIVERS, scen, 5)
    assert run.reconciliation_failures == ()
    assert run.clean


def test_insolvency_is_surfaced_not_swallowed():
    """A downside path that cannot fund itself is a finding the report must state."""
    strained = dataclasses.replace(
        BASE_DRIVERS, cash_floor_pct_revenue=0.10,
        capital_return_policy="sweep_to_buybacks", revolver_limit=0.0)
    scen = Scenario("Bear", "collapse", (ScenarioYear(
        1, (Flex("gross_margin", "set", 0.05, "judgment", "stress probe"),)),))
    run = run_scenario(TABLE, 2025, strained, scen, 2)
    assert run.insolvent_years, "an unfundable path must be reported"
    assert run.clean, "insolvency is an economic finding, not an arithmetic failure"


# --- the checks must actually be wired in, not merely present ------------------

def test_a_reconciliation_failure_is_reported_rather_than_dropped():
    """Mutation-driven. The 'no failures' test above passes trivially if the check is
    never invoked at all, so this one forces a failure and asserts it surfaces --
    otherwise run_scenario could silently stop checking and nothing would notice."""
    import equityresearch.scenarios as mod
    from trellis.statements import CheckResult

    real = mod.reconcile_forecast_year
    mod.reconcile_forecast_year = lambda year, data, prior_cash, tolerance=1.0: (
        CheckResult("forecast_self_consistency", "hard", False, 99.0,
                    f"forced failure FY{year}")
    )
    try:
        run = run_scenario(TABLE, 2025, BASE_DRIVERS, Scenario("Base", "t"), 3)
    finally:
        mod.reconcile_forecast_year = real

    assert len(run.reconciliation_failures) == 3
    assert "forced failure FY2026" in run.reconciliation_failures[0]
    assert not run.clean


def test_reconciliation_is_given_the_prior_forecast_year_cash_not_the_base_year_cash():
    """Year N must reconcile against year N-1's plugged cash. Passing the base year's
    cash every time would make years 2+ reconcile against a stale balance -- an error
    that widens silently down the path."""
    import equityresearch.scenarios as mod

    seen: list[float] = []
    real = mod.reconcile_forecast_year

    def spy(year, data, prior_cash, tolerance=1.0):
        seen.append(prior_cash)
        return real(year, data, prior_cash, tolerance)

    mod.reconcile_forecast_year = spy
    try:
        run = run_scenario(TABLE, 2025, BASE_DRIVERS, Scenario("Base", "t"), 3)
    finally:
        mod.reconcile_forecast_year = real

    assert seen[0] == PRIOR["cash_and_equivalents"]
    assert seen[1] == run.forecast[2026]["cash_and_equivalents"]
    assert seen[2] == run.forecast[2027]["cash_and_equivalents"]
    assert len(set(seen)) == 3, "each year must reconcile against a different balance"


def test_research_items_dedupe_a_derived_driver_across_its_years():
    """A derived consolidated driver repeats the same segment question in all five
    years. Listing it five times turns a 4-item checklist into a 13-item one, and a
    checklist nobody reads does not block anything."""
    from equityresearch.scenarios import research_items
    from equityresearch.segment_bridge import SegmentPath, to_scenario_years

    segs = (SegmentPath("IM", 60.0, (0.0,) * 5, "10-K", f"{UNSOURCED} -- IM path needed"),
            SegmentPath("MT", 40.0, (0.0,) * 5, "10-K", f"{UNSOURCED} -- MT path needed"))
    scen = Scenario("Bear", "t", to_scenario_years(segs, 5))
    items = research_items(scen)

    assert len(items) == 2, [i.text for i in items]
    texts = sorted(i.text for i in items)
    assert texts == ["IM path needed", "MT path needed"], texts
    assert all(i.years == (1, 2, 3, 4, 5) for i in items)


def test_research_items_is_empty_for_a_fully_sourced_scenario():
    from equityresearch.scenarios import research_items
    scen = Scenario("Bear", "t", (ScenarioYear(1, (_flex(basis="10-K note 21"),)),))
    assert research_items(scen) == ()
