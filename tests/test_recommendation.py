import pytest

from equityresearch.recommendation import (
    Gate, Rating, Recommendation, RecommendationError, derive, gate_anchor,
    gate_evidence, gate_robustness, gate_solvency, render,
)

OK = Gate("x", True, "fine")


def test_no_fit_method_fails_the_anchor_gate():
    """J&J's actual position: DCF, comps and precedents all disqualified."""
    g = gate_anchor((), ("DCF", "Trading comparables", "Precedent transactions"))
    assert not g.passed
    assert "no defensible estimate of value" in g.detail


def test_a_fit_method_passes_and_names_it():
    g = gate_anchor(("SOTP MedTech leg",), ("DCF", "SOTP MedTech leg"))
    assert g.passed and "SOTP MedTech leg" in g.detail


def test_unsupported_claims_fail_the_evidence_gate():
    g = gate_evidence(("dispersion_structural",))
    assert not g.passed and "dispersion_structural" in g.detail


def test_a_flipping_comparison_fails_the_robustness_gate():
    g = gate_robustness("IM priced above every pharma peer", False,
                        "flips when MedTech is marked above 4.48x")
    assert not g.passed and "4.48x" in g.detail


def test_insolvency_fails_unless_it_is_the_point_being_made():
    assert not gate_solvency(("Bear",)).passed
    intentional = gate_solvency(("Bear",), intentional=True)
    assert intentional.passed and "the finding being reported" in intentional.detail


def test_a_failing_gate_forces_no_call_not_a_softer_rating():
    """A failing gate does not turn a BUY into a HOLD. HOLD is a real view that price is
    near value; using it to mean 'could not tell' makes the two indistinguishable."""
    rec = derive((OK, gate_anchor((), ("DCF",))), Rating.SELL, "reasoning")
    assert rec.rating is Rating.NO_CALL
    assert rec.target_price is None
    assert "anchor" in rec.reasoning


def test_all_gates_passing_issues_the_proposed_rating():
    rec = derive((OK, Gate("y", True, "fine")), Rating.SELL, "priced above peers",
                 target_price=210.0)
    assert rec.rating is Rating.SELL and rec.target_price == 210.0


def test_a_rating_cannot_be_constructed_around_a_failing_gate():
    """Guards the object itself, not only the factory -- a caller building a
    Recommendation directly must hit the same wall."""
    with pytest.raises(RecommendationError, match="restates the uncertainty"):
        Recommendation(Rating.BUY, (Gate("anchor", False, "none fit"),), "because")


def test_no_call_cannot_carry_a_target_price():
    with pytest.raises(RecommendationError, match="verdict they will ignore"):
        Recommendation(Rating.NO_CALL, (OK,), "r", target_price=210.0)


def test_non_positive_target_price_refused():
    with pytest.raises(RecommendationError, match="must be positive"):
        Recommendation(Rating.BUY, (OK,), "r", target_price=0.0)


def test_an_ungated_recommendation_is_refused():
    with pytest.raises(RecommendationError, match="opinion with a rating attached"):
        derive((), Rating.BUY, "r")


def test_render_shows_every_gate_including_the_passing_ones():
    rec = derive((gate_anchor((), ("DCF",)), gate_evidence(())), Rating.SELL, "r")
    text = render(rec)
    assert "NO CALL" in text
    assert "[FAIL] anchor" in text and "[ok  ] evidence" in text
    assert "Target price" not in text


def test_a_fit_method_with_thin_coverage_still_fails_the_anchor_gate():
    """J&J's actual position, and the contradiction that forced this. The SOTP's MedTech
    leg IS structurally fit -- the market-implied analysis rests on it -- so reporting
    'no method is fit' contradicted the report's own central finding. What blocks a
    rating is that the fit leg reaches 36% of revenue."""
    g = gate_anchor(("SOTP MedTech leg",), ("DCF", "SOTP MedTech leg"), coverage=0.36)
    assert not g.passed
    assert "structurally fit but reaches only 36%" in g.detail
    assert "64% of the business by assumption" in g.detail


def test_full_coverage_with_a_fit_method_passes():
    g = gate_anchor(("DCF",), ("DCF",), coverage=1.0)
    assert g.passed and "100% of revenue" in g.detail


def test_coverage_is_irrelevant_when_nothing_is_fit():
    g = gate_anchor((), ("DCF",), coverage=1.0)
    assert not g.passed and "none of 1 methods is fit" in g.detail
