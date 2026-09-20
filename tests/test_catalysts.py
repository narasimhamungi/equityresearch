from datetime import date

import pytest

from equityresearch.catalysts import (
    CatalystError, Event, Register, jnj_register, render,
)
from equityresearch.claims import Tier

TODAY = date(2026, 9, 20)


def _e(eid="x", kind="risk", expected="2027", direction="negative",
       tier=Tier.DEMONSTRATED, source="J&J 8-K", resolved=False):
    return Event(eid, kind, "something happens", expected, direction, "material",
                 tier, source, resolved)


# --- staleness: the defect this module exists to make loud ----------------------

def test_a_passed_unresolved_event_is_stale():
    """A catalyst calendar rots silently. Every entry has a date, every date passes, and
    the moment one does the report describes as forthcoming something already past."""
    assert _e(expected="2025").is_stale(TODAY)
    assert not _e(expected="2027").is_stale(TODAY)


def test_a_resolved_event_is_never_stale():
    assert not _e(expected="2020", resolved=True).is_stale(TODAY)


def test_a_bare_year_resolves_to_year_end_not_january():
    """Otherwise every year-level event in the current year reads as overdue from 1
    January, and the warning becomes noise before February."""
    assert Event("y", "risk", "d", "2026", "negative", "m", Tier.ASSUMED,
                 "s").deadline() == date(2026, 12, 31)
    assert not _e(expected="2026").is_stale(TODAY)


def test_an_iso_date_is_honoured_exactly():
    e = _e(expected="2026-07-27")
    assert e.deadline() == date(2026, 7, 27)
    assert e.is_stale(TODAY)


def test_register_lists_only_stale_events():
    r = Register()
    r.add(_e("past", expected="2024"))
    r.add(_e("future", expected="2029"))
    r.add(_e("done", expected="2024", resolved=True))
    assert [e.id for e in r.stale(TODAY)] == ["past"]


def test_render_puts_stale_events_above_the_register_not_below():
    r = Register()
    r.add(_e("past", expected="2024"))
    text = render(r, TODAY)
    assert "PAST THEIR DATE" in text
    assert text.index("PAST THEIR DATE") < text.index("-- RISKS")


def test_render_says_nothing_about_staleness_when_there_is_none():
    r = Register()
    r.add(_e("future", expected="2029"))
    assert "PAST THEIR DATE" not in render(r, TODAY)


# --- binary events must not be averaged ------------------------------------------

def test_binary_events_are_flagged_with_a_warning_against_averaging():
    """The Darzalex question is not a magnitude anyone chose. Its two branches differ by
    billions a year, so the midpoint corresponds to no state of the world."""
    r = Register()
    r.add(_e("d", direction="binary", expected="2029"))
    text = render(r, TODAY)
    assert "BINARY EVENTS" in text and "do not average" in text
    assert "no state of the world" in text


def test_no_binary_warning_when_nothing_is_binary():
    r = Register()
    r.add(_e("a", direction="negative", expected="2029"))
    assert "BINARY EVENTS" not in render(r, TODAY)


# --- construction guards ----------------------------------------------------------

def test_a_sourceless_event_is_refused():
    with pytest.raises(CatalystError, match="guess with a calendar entry"):
        _e(source="  ")


@pytest.mark.parametrize("bad", [("kind", "opportunity"), ("direction", "maybe")])
def test_bad_enum_values_refused(bad):
    field, value = bad
    with pytest.raises(CatalystError):
        _e(**{field: value})


def test_an_unparseable_date_is_refused_at_construction():
    """Validated when the event is written, not when the report renders -- otherwise a
    typo surfaces in front of a reader."""
    with pytest.raises(CatalystError, match="neither an ISO date nor"):
        _e(expected="next year")


def test_duplicate_ids_refused():
    r = Register()
    r.add(_e("a"))
    with pytest.raises(CatalystError, match="Duplicate event id"):
        r.add(_e("a"))


# --- the J&J register itself ------------------------------------------------------

def test_jnj_register_is_current_as_of_the_report_date():
    """Guards the report against shipping with a rotted calendar. If this fails, an
    event has passed and needs resolving or re-dating -- that is the point."""
    stale = jnj_register().stale(TODAY)
    assert stale == (), [f"{e.id} due {e.expected}" for e in stale]


def test_the_darzalex_event_is_binary_and_says_the_bull_premise_is_weak():
    """Two separate constraints arrive in 2029: the IRA question, which is genuinely
    binary, and a reported patent expiry, which is not. A Bull case premised on the IRA
    branch going J&J's way does not clear the patent constraint."""
    d = jnj_register().events
    darzalex = next(e for e in d if e.id == "darzalex_2029")
    assert darzalex.direction == "binary"
    assert "patent" in darzalex.magnitude.lower()
    assert "WEAKER THAN IT LOOKS" in darzalex.magnitude


def test_the_pfa_risk_is_registered_against_the_only_fit_valuation_leg():
    """The sharpest adversarial finding: MedTech is the one structurally fit leg, and
    electrophysiology -- a named FY2025 growth driver -- is being displaced by a
    technology where J&J holds a small share."""
    pfa = next(e for e in jnj_register().events if e.id == "pfa_share")
    assert pfa.kind == "risk"
    assert "ONLY structurally fit valuation leg" in pfa.magnitude


def test_management_guidance_is_tiered_assumed_not_demonstrated():
    """A company's target for its own future is a forecast by an interested party,
    however confidently stated."""
    reg = jnj_register()
    for eid in ("double_digit_growth", "icotrokinra", "pfa_response"):
        assert next(e for e in reg.events if e.id == eid).tier is Tier.ASSUMED


def test_talc_is_registered_as_outside_the_numbers():
    talc = next(e for e in jnj_register().events if e.id == "talc_2027")
    assert "NOT IN THE NUMBERS" in talc.magnitude
    assert talc.tier is Tier.DEMONSTRATED
