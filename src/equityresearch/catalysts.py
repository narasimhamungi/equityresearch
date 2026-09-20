"""
Catalysts and risks, as dated data rather than prose.

WHY THIS IS A MODULE AND NOT A PARAGRAPH
------------------------------------------
This project's recurring failure has not been wrong arithmetic. It has been accurate
arithmetic with a stale description attached: a talc flex whose basis cited an 8-K while
moving no number, a Bear thesis claiming talc cash was modelled after it was removed, a
README claiming magnitudes were unsourced after they were sourced, a Bull thesis claiming
MedTech ran at its reported rate after it was set to organic. Four of them, each
surviving a passing test suite, because the guards check behaviour and nothing checks
prose.

A catalyst calendar is the single most rot-prone artifact in an equity research report.
Every entry has a date, every date passes, and the moment one does the report is making a
claim about the future that is now a claim about the past. Written as prose it rots
silently and reads as current. Written as data with a date and a resolution flag, a
report can be made to say so itself.

So `stale()` returns every event whose expected date has passed without being marked
resolved, and the renderer prints that list above the register rather than below it.
That does not stop the analyst forgetting to update — nothing does — but it moves the
failure from invisible to loud.

DIRECTION IS DECLARED, NOT INFERRED
-------------------------------------
Each event states whether it helps or hurts, and binary events say so explicitly. The
Darzalex question is the reason: it is not a magnitude anyone chose, it is an unresolved
policy and patent question whose two branches differ by billions a year. Recording it as
`binary` keeps a reader from reading the Bear and Bull cases as a range to average --
the midpoint of a binary outcome corresponds to no state of the world.

EVIDENCE TIERS ARE SHARED WITH THE CLAIM REGISTER
---------------------------------------------------
`Tier` is imported from `claims.py` rather than redefined, so a catalyst and a claim are
graded on one scale. A catalyst sourced to a filing is Demonstrated; one resting on
management guidance about its own future is Assumed, however confidently it was said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .claims import Tier

KINDS = ("catalyst", "risk")
DIRECTIONS = ("positive", "negative", "binary")


class CatalystError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    id: str
    kind: str                # "catalyst" | "risk"
    description: str
    expected: str            # ISO date, or a bare year "2029" for period-level timing
    direction: str           # "positive" | "negative" | "binary"
    magnitude: str           # what it is worth, in the analyst's words
    tier: Tier
    source: str
    resolved: bool = False   # set True once the event has happened and been written up

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise CatalystError(f"{self.id}: kind {self.kind!r} not in {KINDS}.")
        if self.direction not in DIRECTIONS:
            raise CatalystError(
                f"{self.id}: direction {self.direction!r} not in {DIRECTIONS}.")
        if not self.source.strip():
            raise CatalystError(
                f"{self.id}: no source. A dated event without one is a guess with a "
                f"calendar entry.")
        self.deadline()  # validate the date format at construction, not at render time

    def deadline(self) -> date:
        """Latest date by which this is expected. A bare year resolves to 31 December,
        so a year-level event is not called stale in January."""
        raw = self.expected.strip()
        if len(raw) == 4 and raw.isdigit():
            return date(int(raw), 12, 31)
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CatalystError(
                f"{self.id}: expected {self.expected!r} is neither an ISO date nor a "
                f"four-digit year.") from exc

    def is_stale(self, as_of: date) -> bool:
        return not self.resolved and self.deadline() < as_of


@dataclass
class Register:
    events: list[Event] = field(default_factory=list)

    def add(self, event: Event) -> None:
        if any(e.id == event.id for e in self.events):
            raise CatalystError(f"Duplicate event id {event.id!r}.")
        self.events.append(event)

    def of_kind(self, kind: str) -> tuple[Event, ...]:
        return tuple(e for e in self.events
                     if e.kind == kind and not e.resolved)

    def stale(self, as_of: date) -> tuple[Event, ...]:
        return tuple(e for e in self.events if e.is_stale(as_of))

    def binary(self) -> tuple[Event, ...]:
        return tuple(e for e in self.events if e.direction == "binary")


def render(register: Register, as_of: date) -> str:
    out = ["CATALYSTS AND RISKS", "=" * 19, f"  as of {as_of.isoformat()}", ""]

    stale = register.stale(as_of)
    if stale:
        out += [f"  {len(stale)} EVENT(S) PAST THEIR DATE AND NOT MARKED RESOLVED.",
                "  Until each is resolved or re-dated, this report is describing as "
                "forthcoming",
                "  something that has already happened:"]
        for e in stale:
            out.append(f"    [{e.expected}] {e.id}: {e.description}")
        out.append("")

    for kind, heading in (("catalyst", "CATALYSTS"), ("risk", "RISKS")):
        events = sorted(register.of_kind(kind), key=lambda e: e.deadline())
        if not events:
            continue
        out += [f"  -- {heading} " + "-" * (58 - len(heading))]
        for e in events:
            mark = {"positive": "+", "negative": "-", "binary": "?"}[e.direction]
            flag = "  PAST DATE" if e.is_stale(as_of) else ""
            out.append(f"    [{mark}] {e.expected}  {e.description}{flag}")
            out.append(f"         magnitude: {e.magnitude}")
            out.append(f"         [{e.tier.value}] {e.source}")
        out.append("")

    binaries = register.binary()
    if binaries:
        out += ["  BINARY EVENTS -- do not average the branches:",
                *[f"    {e.id}: {e.description}" for e in binaries],
                "  A scenario range built across a binary outcome has a midpoint that "
                "corresponds",
                "  to no state of the world. Read the branches, not the middle."]
    return "\n".join(out)


def jnj_register() -> Register:
    """J&J's catalyst and risk calendar. Every entry is dated and sourced; the
    magnitudes are the analyst's."""
    r = Register()

    r.add(Event(
        "ira_2026", "risk",
        "Medicare negotiated prices take effect for Stelara, Xarelto and Imbruvica",
        "2026", "negative",
        "Compounds with Uptravi (~$1bn exposed) and Opsumit expiries in the same year; "
        "the Bear case carries FY2026 Innovative Medicine at -2.0% on the combination",
        Tier.DEMONSTRATED,
        "IRA first negotiation cycle, prices effective 1 January 2026"))

    r.add(Event(
        "stelara_residual", "risk",
        "Residual Stelara erosion off a base already down 41.3% to $6.08bn",
        "2027", "negative",
        "Smaller than the 2025 step: Stelara cost Innovative Medicine ~10.4pp of "
        "operational growth in 2025 and the segment still grew 5.3%. The remaining base "
        "is too small to dominate again",
        Tier.DEMONSTRATED,
        "J&J FY2025 results and ARS: Stelara -41.3% to $6.08bn, approx -10.4% impact on "
        "IM worldwide operational sales"))

    r.add(Event(
        "icotrokinra", "catalyst",
        "Icotrokinra (JNJ-2113) launch -- first targeted oral peptide for plaque "
        "psoriasis",
        "2026", "positive",
        "Management and sell-side frame it as a $5bn-plus opportunity. That figure is a "
        "forecast by interested parties, not a disclosure, and the scenarios do not "
        "carry it as a separate line",
        Tier.ASSUMED,
        "J&J 2026 investor materials and press coverage; peak-sales figure is an "
        "estimate, not a filed number"))

    r.add(Event(
        "tremfya_skyrizi", "risk",
        "Tremfya versus AbbVie's Skyrizi in IL-23 -- the defining immunology rivalry",
        "2027", "negative",
        "Tremfya is J&J's principal Stelara replacement and grew 40.5% to $5.2bn in "
        "FY2025, but AbbVie's Skyrizi and Rinvoq together are widely expected to exceed "
        "Humira's peak. Share gains are being made into a market a larger competitor is "
        "also expanding into",
        Tier.INFERRED,
        "J&J FY2025 results for Tremfya; competitive framing from trade coverage of the "
        "IL-23 class. The rivalry is documented; the outcome is not"))

    r.add(Event(
        "pfa_share", "risk",
        "J&J is a marginal player in pulsed field ablation, the technology displacing "
        "the electrophysiology market it leads",
        "2027", "negative",
        "THE MOST IMPORTANT ITEM IN THIS REGISTER. Electrophysiology is a named driver "
        "of FY2025 MedTech growth, and MedTech is the ONLY structurally fit valuation "
        "leg in this report. Boston Scientific held ~41% of PFA spend in early 2026 and "
        "Medtronic ~48%, leaving roughly a tenth for J&J and everyone else, against a "
        "J&J electrophysiology franchise of about $5bn that the company calls sector "
        "leading",
        Tier.INFERRED,
        "PFA spend share: Boston Scientific 100% (2023) -> ~83% (2024) -> 41% (early "
        "2026), Medtronic 48%; J&J launched Varipulse December 2024, Abbott's Volt "
        "entered January 2026. J&J EP franchise ~$5bn per J&J MedTech chairman. Share "
        "figures are third-party estimates, not filed data"))

    r.add(Event(
        "pfa_response", "catalyst",
        "J&J PFA portfolio build-out: Varipulse Pro, then Omnypulse, then Isopulse, "
        "with acquisitions no longer ruled out",
        "2028", "positive",
        "Management commits to one meaningful catheter addition a year for three to "
        "five years. Mapping integration is the structural advantage: more than half of "
        "competitors' cases already use J&J's Carto system",
        Tier.ASSUMED,
        "J&J MedTech chairman, trade press. A stated commitment about a company's own "
        "future is not a disclosure"))

    r.add(Event(
        "talc_2027", "risk",
        "First talc settlement payment, capped at $3bn",
        "2027", "negative",
        "NOT IN THE NUMBERS. $5.5bn total, balance due 2028, conditional on at least "
        "95% claimant participation. Trellis has no one-off-cash-outflow driver, so "
        "this sits outside every scenario. If the participation condition fails, the "
        "litigation reverts to open-ended exposure that nothing here prices",
        Tier.DEMONSTRATED,
        "J&J 8-K, 27 July 2026: $5.5bn comprehensive resolution covering ~76,000 "
        "ovarian claims"))

    r.add(Event(
        "darzalex_2029", "risk",
        "Darzalex US exposure in 2029 -- patent expiry and IRA negotiation, two "
        "separate constraints arriving together",
        "2029", "binary",
        "J&J's largest product: $14.35bn in FY2025, +23.0%, with Faspro carrying more "
        "than 80%. The IRA question is genuinely binary -- the ORPHAN Cures Act "
        "provisions may remove Darzalex from eligibility entirely, or CMS's rethink may "
        "collapse Faspro's protection from 2034 to 2029. But the main US patents are "
        "separately reported as expiring in 2029 regardless, so the Bull case's premise "
        "that a favourable IRA outcome removes the 2029 risk is WEAKER THAN IT LOOKS. "
        "Treat the Bull FY2029-FY2030 path as the optimistic end of a range whose "
        "downside is better documented than its upside",
        Tier.INFERRED,
        "Darzalex FY2025 sales from J&J results. IRA treatment: CMS signalled a rethink "
        "of the additional-active-ingredient approach; OBBBA ORPHAN Cures Act expanded "
        "the orphan exclusion to serial orphans. Patent expiry reported in trade "
        "coverage as 2029. The two constraints are documented separately and neither is "
        "resolved"))

    r.add(Event(
        "double_digit_growth", "catalyst",
        "Management target of double-digit company-wide sales growth by the end of the "
        "decade",
        "2029", "positive",
        "Set against this report's Bull case of 4.91% consolidated revenue CAGR. The "
        "gap is not a rounding difference -- it is roughly double. Either the analyst's "
        "organic paths are far too conservative, or the target depends on acquisitions "
        "and pipeline outcomes that no filed number yet supports. Stating the "
        "disagreement is more useful than resolving it by assumption",
        Tier.ASSUMED,
        "J&J executives, Q1 2026 earnings commentary. Management guidance about its own "
        "future is a forecast by an interested party"))

    return r
