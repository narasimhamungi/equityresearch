import pytest

from equityresearch.claims import (
    Claim, ClaimError, Register, Tier, gate_thesis, render,
)


def _c(cid="c1", text="J&J FY2021-FY2025 revenue CAGR is 4.58%", tier=Tier.DEMONSTRATED,
       source="Trellis derive_drivers_from_history off SEC XBRL",
       reproduce="python valuationlab_loader.py 200406"):
    return Claim(id=cid, text=text, tier=tier, source=source, reproduce=reproduce)


def test_a_demonstrated_claim_must_carry_a_reproduction_command():
    """'Demonstrated' means a reader can re-run it. Without the command it is a promise."""
    with pytest.raises(ClaimError, match="promise rather than a demonstration"):
        _c(reproduce="")


def test_lower_tiers_need_no_reproduction_command():
    assert Claim("c", "x", Tier.ASSUMED, "analyst judgement").tier is Tier.ASSUMED


def test_a_claim_without_a_source_is_refused_at_every_tier():
    for tier in Tier:
        with pytest.raises(ClaimError, match="no source"):
            Claim("c", "x", tier, "   ", reproduce="cmd")


def test_duplicate_ids_are_refused():
    r = Register()
    r.add(_c())
    with pytest.raises(ClaimError, match="Duplicate claim id"):
        r.add(_c())


def test_weakest_takes_the_lowest_tier_not_an_average():
    """An argument is as good as its weakest link. Averaging would let two demonstrated
    facts launder one assumption into something that reads as established."""
    r = Register()
    r.add(_c("a", tier=Tier.DEMONSTRATED))
    r.add(_c("b", tier=Tier.INFERRED, reproduce=""))
    r.add(_c("c", tier=Tier.ASSUMED, reproduce=""))
    assert r.weakest(("a", "b", "c")) is Tier.ASSUMED
    assert r.weakest(("a", "b")) is Tier.INFERRED
    assert r.weakest(("a",)) is Tier.DEMONSTRATED


def test_weakest_refuses_an_empty_argument():
    with pytest.raises(ClaimError, match="no argument to rank"):
        Register().weakest(())


def test_gate_thesis_blocks_an_unsupported_claim_and_names_it():
    """The live case: ValuationLab's structural-dispersion claim, which dispersion.py
    showed is unestablished by the evidence offered for it."""
    r = Register()
    r.add(_c("cagr"))
    r.add(Claim("dispersion_structural",
                "Pharma peer dispersion is economic, not a small-sample artefact",
                Tier.UNSUPPORTED,
                "evidenced by a min/max spread widening with more peers, which is "
                "monotonic in n and would widen under the null too"))
    with pytest.raises(ClaimError, match="dispersion_structural"):
        gate_thesis(r, ("cagr", "dispersion_structural"))


def test_gate_thesis_allows_assumed_claims_through():
    """A forward-looking report cannot be written without assumptions; what it cannot do
    is present one as measured."""
    r = Register()
    r.add(Claim("stelara", "Stelara erosion is front-loaded", Tier.ASSUMED,
                "analyst judgement pending the LOE calendar"))
    gate_thesis(r, ("stelara",))


def test_gate_thesis_error_states_what_fails_not_just_which_claim():
    r = Register()
    r.add(Claim("x", "some claim", Tier.UNSUPPORTED, "the offered evidence is monotonic"))
    with pytest.raises(ClaimError, match="what fails: the offered evidence is monotonic"):
        gate_thesis(r, ("x",))


def test_render_groups_by_tier_and_flags_the_unsupported_section():
    r = Register()
    r.add(_c("a"))
    r.add(Claim("b", "market implies ~9.0x", Tier.INFERRED, "market_implied.py"))
    r.add(Claim("c", "dispersion is structural", Tier.UNSUPPORTED, "monotonic measure"))
    text = render(r)
    assert "DEMONSTRATED" in text and "INFERRED" in text and "UNSUPPORTED" in text
    assert "declines to" in text
    assert "python valuationlab_loader.py 200406" in text


def test_render_omits_the_unsupported_note_when_there_are_none():
    r = Register()
    r.add(_c("a"))
    assert "declines to" not in render(r)


def test_missing_claim_id_is_refused():
    with pytest.raises(ClaimError, match="No claim 'nope'"):
        Register().get("nope")
