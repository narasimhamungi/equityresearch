import pytest

from equityresearch.dispersion import (
    DISQUALIFYING_SPREAD, DispersionError, compare_peer_sets, dispersion,
    expected_spread_under_noise,
)

# ValuationLab's four large-cap pharma peers, EV/Revenue, measured against snapshots
# a34baff (market 2026-09-15): PFE 3.476, MRK 5.952, ABBV 8.569, BMY 3.378.
PHARMA_4 = [3.476, 5.952, 8.569, 3.378]

# MedTech's four: only the extremes are recorded in ValuationLab's printed SOTP
# (3.096x-4.730x). The interior two are RECONSTRUCTED to sit plausibly between them --
# enough to exercise the arithmetic, not enough to quote. Any test asserting a CV value
# for this set would be asserting against invented data, so none does; the one test
# that uses it compares DIRECTION against PHARMA_4, which the extremes alone settle.
MEDTECH_4_RECONSTRUCTED = [3.096, 3.500, 4.088, 4.730]


def test_min_max_spread_reproduces_valuationlabs_own_figures():
    assert dispersion(PHARMA_4).min_max_spread == pytest.approx(2.54, abs=0.01)
    assert dispersion(MEDTECH_4_RECONSTRUCTED).min_max_spread == pytest.approx(1.53, abs=0.01)


def test_the_fitness_comparison_is_between_equal_sized_sets_so_it_stays_valid():
    """What this module does NOT undermine. Monotonicity in n cancels when both sets
    have four peers, so 2.5x against 1.5x is a fair comparison and the SOTP's fitness
    verdicts stand. Only the separate six-peer argument is contaminated."""
    a, b = dispersion(PHARMA_4), dispersion(MEDTECH_4_RECONSTRUCTED)
    assert a.n == b.n == 4
    assert a.min_max_spread > b.min_max_spread
    assert a.coefficient_of_variation > b.coefficient_of_variation, (
        "the scale-free measure must agree, or the verdict rests on the extremes alone")


# --- the monotonicity that makes the premise untestable as measured -------------

@pytest.mark.parametrize("extra", [5.0, 0.1, 100.0, 4.2])
def test_min_max_spread_never_falls_when_a_peer_is_added(extra):
    """Whatever you add -- central, cheap or absurd -- the spread cannot narrow. A
    statistic that can only move one way cannot be evidence for the direction it moves."""
    before = dispersion(PHARMA_4).min_max_spread
    after = dispersion(PHARMA_4 + [extra]).min_max_spread
    assert after >= before


def test_coefficient_of_variation_falls_when_a_central_peer_is_added():
    """The property the CV has and min/max does not: adding a peer near the centre
    tightens it, which is exactly what a larger draw from ONE distribution produces."""
    before = dispersion(PHARMA_4).coefficient_of_variation
    after = dispersion(PHARMA_4 + [5.0]).coefficient_of_variation   # near the mean
    assert after < before


def test_coefficient_of_variation_rises_when_an_outlying_peer_is_added():
    before = dispersion(PHARMA_4).coefficient_of_variation
    after = dispersion(PHARMA_4 + [20.0]).coefficient_of_variation
    assert after > before


# --- null model ------------------------------------------------------------------

def test_pure_sampling_noise_trips_the_disqualification_bar_often_at_small_n():
    """The threshold is not scale-free. If a four-peer draw from a single distribution
    trips 2.0x this often, 'spread exceeds 2.0x' is partly a statement about n."""
    mean4, p4 = expected_spread_under_noise(n=4, cv=0.40)
    mean10, p10 = expected_spread_under_noise(n=10, cv=0.40)
    assert mean10 > mean4, "mean spread must grow with n at fixed dispersion"
    assert p10 > p4 > 0.05
    assert DISQUALIFYING_SPREAD == 2.0


def test_null_model_is_deterministic_for_a_given_seed():
    assert expected_spread_under_noise(4, 0.4, trials=2000, seed=11) == \
           expected_spread_under_noise(4, 0.4, trials=2000, seed=11)


def test_higher_cv_produces_wider_expected_spreads():
    tight, _ = expected_spread_under_noise(n=5, cv=0.15)
    loose, _ = expected_spread_under_noise(n=5, cv=0.60)
    assert loose > tight


# --- the premise test itself ------------------------------------------------------

def test_premise_not_supported_when_min_max_widens_but_cv_falls():
    """The exact case the report must be able to detect, and the reason this module
    exists. Adding 3.0 and 5.1 widens min/max from 2.54x to 2.86x -- which reads as
    support for the structural claim -- while the CV FALLS from 0.430 to 0.410, the
    signature of a larger sample from one distribution. Anyone reading only the spread
    would conclude the opposite of what the data says."""
    result = compare_peer_sets(PHARMA_4, PHARMA_4 + [3.0, 5.1], ("LLY", "AMGN"))
    assert result.spread_widened, "min/max must widen, or this is not the hard case"
    assert not result.cv_widened
    assert not result.supports_structural_claim
    text = result.verdict()
    assert "PREMISE NOT SUPPORTED" in text
    assert "was always going to" in text


def test_interior_peers_leave_min_max_untouched_while_cv_falls():
    """The easy case, for contrast: peers added inside the existing range move min/max
    not at all, so it reports no change where the CV records a real tightening."""
    result = compare_peer_sets(PHARMA_4, PHARMA_4 + [5.0, 5.2], ("LLY", "AMGN"))
    assert not result.spread_widened
    assert not result.cv_widened


def test_premise_supported_when_added_peers_sit_away_from_the_centre():
    result = compare_peer_sets(PHARMA_4, PHARMA_4 + [14.0, 1.2], ("LLY", "AMGN"))
    assert result.cv_widened and result.supports_structural_claim
    assert "PREMISE SUPPORTED" in result.verdict()


def test_verdict_always_warns_that_min_max_movement_carries_no_information():
    for large in (PHARMA_4 + [5.0, 5.2], PHARMA_4 + [14.0, 1.2]):
        assert "carries no information" in compare_peer_sets(
            PHARMA_4, large, ("LLY", "AMGN")).verdict()


# --- guards -------------------------------------------------------------------------

def test_two_peers_is_refused():
    with pytest.raises(DispersionError, match="too few"):
        dispersion([3.0, 5.0])


def test_non_positive_multiples_refused():
    with pytest.raises(DispersionError, match="undefined"):
        dispersion([3.0, 0.0, 5.0])


def test_a_larger_set_that_is_not_larger_is_refused():
    with pytest.raises(DispersionError, match="must actually be larger"):
        compare_peer_sets(PHARMA_4, PHARMA_4[:3], ("LLY",))


# --- one outlier must not carry a verdict about a whole peer set ----------------

# Live EV/Revenue, all six priced 2026-09-17.
PHARMA_4_LIVE = [3.468, 5.994, 8.554, 3.373]
ADDED_LIVE = {"LLY": 16.082, "AMGN": 6.649}


def test_the_real_six_peer_run_is_inconclusive_not_supported():
    """The case that exposed the defect. CV rises 0.460 -> 0.641 while IQR/median FALLS
    0.674 -> 0.629. Judging on CV alone reported PREMISE SUPPORTED; the measures
    disagree, which is what one extreme observation produces."""
    result = compare_peer_sets(
        PHARMA_4_LIVE, PHARMA_4_LIVE + list(ADDED_LIVE.values()), ("LLY", "AMGN"))
    assert result.cv_widened
    assert not result.iqr_widened
    assert result.measures_disagree
    assert not result.supports_structural_claim
    text = result.verdict()
    assert "INCONCLUSIVE" in text
    assert "CV rose while IQR/median fell" in text
    assert "leave-one-out" in text


def test_leave_one_out_names_the_single_peer_carrying_the_result():
    from equityresearch.dispersion import leave_one_out
    loo = leave_one_out(PHARMA_4_LIVE, ADDED_LIVE)

    by_ticker = {t: (cv, w) for t, cv, w in loo.per_peer}
    assert by_ticker["LLY"][1] is True, "LLY alone must widen the set"
    assert by_ticker["AMGN"][1] is False, "AMGN alone must tighten it"
    assert by_ticker["AMGN"][0] < loo.baseline_cv

    assert loo.carried_by_one
    text = loo.describe()
    assert "rests entirely on LLY" in text
    assert "TIGHTENS" in text
    assert "a statement about one company" in text


def test_leave_one_out_reports_no_support_when_nothing_widens():
    from equityresearch.dispersion import leave_one_out
    loo = leave_one_out(PHARMA_4_LIVE, {"A": 5.4, "B": 5.6})
    assert not loo.carried_by_one
    assert "no support here" in loo.describe()


def test_leave_one_out_reports_independent_support_when_several_widen():
    from equityresearch.dispersion import leave_one_out
    loo = leave_one_out(PHARMA_4_LIVE, {"A": 18.0, "B": 0.6})
    assert not loo.carried_by_one
    assert "do not rest on a single company" in loo.describe().replace(
        "does not rest", "do not rest")


def test_leave_one_out_refuses_an_empty_candidate_set():
    from equityresearch.dispersion import leave_one_out
    with pytest.raises(DispersionError, match="No candidate peers"):
        leave_one_out(PHARMA_4_LIVE, {})


def test_support_now_requires_both_measures_to_agree():
    """Previously the CV alone carried the verdict."""
    result = compare_peer_sets(PHARMA_4_LIVE, PHARMA_4_LIVE + [18.0, 0.55],
                               ("A", "B"))
    assert result.cv_widened and result.iqr_widened
    assert result.supports_structural_claim
    assert "PREMISE SUPPORTED" in result.verdict()
