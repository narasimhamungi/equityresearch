"""
J&J Bull / Base / Bear scenario definitions.

STATUS: STRUCTURE COMPLETE, MAGNITUDES NOT YET SOURCED.

This file states WHICH drivers move, in WHICH years, and WHY -- the part that is an
analytical decision. It does not state by how much, because those magnitudes depend on
facts that must be read out of filings (LOE dates, settlement terms, guided synergies)
rather than assumed. Every such magnitude is marked UNSOURCED, and `scenarios.validate`
refuses to run a schedule containing one. That is deliberate: a scenario file that runs
on placeholder numbers produces a target price that looks finished, and there is no
later point at which anyone is forced to notice it was not.

Run `python scripts/run_scenarios.py --checklist` to print exactly what is outstanding.

THE SHAPE OF THE ARGUMENT (this is the part that is settled)
-------------------------------------------------------------
Growth is specified per SEGMENT, never at the consolidated level, and the consolidated
`revenue_growth` driver is derived from the segment paths by `segment_bridge`. Reason:
the two segments face entirely different forces. A patent cliff is an Innovative
Medicine event. An Abiomed synergy ramp is a MedTech event. A single consolidated
growth rate averages them into one number and makes the thesis unreadable -- and the
thesis IS the divergence.

Base is Trellis's derived drivers held flat, unmodified. It carries no flexes at all.
That is not laziness: Base must be the upstream forecast exactly as ValuationLab and
DealLab consumed it, or the three projects stop being comparable and this report
silently re-bases the work it claims to build on.

Bear and Bull are then departures from that same base, so every difference between the
three cases is attributable to a specific, listed, dated assumption.
"""

from equityresearch.scenarios import UNSOURCED, Flex, Scenario, ScenarioYear
from equityresearch.segment_bridge import SegmentPath, to_scenario_years

HORIZON = 5
BASE_FISCAL_YEAR = 2025

# FY2025 segment revenue, as cited in ValuationLab's segments.py -- the same figures
# the SOTP ran on, so the two projects cannot drift apart on the base-year split.
IM_FY2025 = 60_401_000_000.0
MT_FY2025 = 33_792_000_000.0
CONSOLIDATED_FY2025 = 94_193_000_000.0

IM_SOURCE = ("J&J FY2025 10-K (jnj-20251228.htm), segment sales table: "
             "TOTAL INNOVATIVE MEDICINE worldwide $60,401M")
MT_SOURCE = ("J&J FY2025 10-K: consolidated $94,193M less Innovative Medicine $60,401M")

_TODO = f"{UNSOURCED} -- "


# ---------------------------------------------------------------------------
# BASE
# ---------------------------------------------------------------------------
BASE = Scenario(
    name="Base",
    thesis=("Trellis's 5-year driver-based forecast, unmodified: trailing-window "
            "drivers held flat. The same forecast ValuationLab's DCF and DealLab's "
            "accretion model consumed, carried through here without re-basing."),
    years=(),
)


# ---------------------------------------------------------------------------
# BEAR
# ---------------------------------------------------------------------------
# The downside is NOT "everything a bit worse." It is three specific, dated events,
# each hitting a specific line:
#   1. Innovative Medicine LOE / biosimilar erosion  -> IM segment revenue path
#   2. Pipeline defence spend to replace lost revenue -> rnd_pct_revenue
#   3. Litigation cash settlement                     -> debt_repayment (a CASH item)
#
# (3) is worth its own note. A litigation settlement is not an operating expense and
# must not be modelled as a margin haircut: doing so understates margins permanently
# for a one-off payment, and understates the cash outflow's balance-sheet effect. It
# is routed through the debt/cash schedule so the cash leaves once, which is also what
# makes the Bear case capable of tripping project_year's `insolvent` flag honestly.

BEAR_IM = SegmentPath(
    name="Innovative Medicine", base_revenue=IM_FY2025, source=IM_SOURCE,
    growth=(0.0,) * HORIZON,  # REPLACE
    rationale=(_TODO + "per-year IM revenue growth under accelerated biosimilar "
               "erosion. Source needed: 10-K Item 1A / MD&A product-level sales for "
               "the largest IM franchises, their US and ex-US exclusivity expiry "
               "dates, and IRA Medicare negotiation selection status. Shape the path "
               "to the actual expiry calendar -- erosion is front-loaded in the 12-24 "
               "months after entry, not linear across five years."),
)
BEAR_MT = SegmentPath(
    name="MedTech", base_revenue=MT_FY2025, source=MT_SOURCE,
    growth=(0.0,) * HORIZON,  # REPLACE
    rationale=(_TODO + "per-year MedTech growth in the downside. Note this should NOT "
               "simply mirror the IM decline: the Bear case is about IM, and forcing "
               "MedTech down too without a separate reason turns a specific thesis "
               "into a generic haircut. If MedTech holds up, say so -- that is the "
               "finding."),
)

BEAR_EXTRA = {
    2: (Flex("rnd_pct_revenue", "delta", 0.0, "judgment",
             _TODO + "incremental R&D as % of revenue to defend the pipeline. Anchor "
             "to J&J's own disclosed R&D trajectory and peer response to comparable "
             "cliffs, not to a round number."),),
    1: (Flex("debt_repayment", "set", 0.0, "sourced",
             _TODO + "annual cash outflow from talc settlement. Source needed: the "
             "current proposed settlement structure and payment schedule per the "
             "latest 10-K contingencies note and 8-K filings. Model the SCHEDULE, not "
             "an NPV -- the year the cash leaves is what determines whether the "
             "downside path can still fund the dividend."),),
}

BEAR = Scenario(
    name="Bear",
    thesis=("Innovative Medicine's exclusivity cliff arrives faster and deeper than "
            "the trailing-window base assumes, pipeline defence raises R&D intensity, "
            "and litigation cash leaves the balance sheet on a fixed schedule. MedTech "
            "is not assumed to deteriorate with it."),
    years=to_scenario_years((BEAR_IM, BEAR_MT), HORIZON, extra=BEAR_EXTRA),
)


# ---------------------------------------------------------------------------
# BULL
# ---------------------------------------------------------------------------
# The Bull case is where this report has to be most careful, because it is where it
# would be easiest to smuggle ValuationLab's SOTP finding in as a conclusion.
#
# ValuationLab found that MedTech values cleanly on its own peer group (~$101-157B EV)
# while Innovative Medicine does not clear the same dispersion bars against pharma
# peers. That is EVIDENCE about valuation method. It is NOT, on its own, an argument
# that the market is mispricing J&J -- a method finding says nothing about what the
# market has already priced.
#
# So the Bull case does not flex a multiple. It flexes the BUSINESS: MedTech's
# operating performance, driven by the Abiomed asset DealLab already modelled on real
# closed-deal terms. The re-rating argument then belongs in the valuation section as a
# separate, separately-defended claim -- with the SOTP cited as supporting evidence --
# rather than being baked into the forecast where it would be invisible.

BULL_IM = SegmentPath(
    name="Innovative Medicine", base_revenue=IM_FY2025, source=IM_SOURCE,
    growth=(0.0,) * HORIZON,  # REPLACE
    rationale=(_TODO + "per-year IM growth where launches and label expansions offset "
               "more of the cliff than the base assumes. Source needed: named "
               "late-stage pipeline assets with disclosed peak-sales guidance or "
               "consensus, and their approval timing. An unnamed 'pipeline delivers' "
               "assumption is not a bull case, it is a wish."),
)
BULL_MT = SegmentPath(
    name="MedTech", base_revenue=MT_FY2025, source=MT_SOURCE,
    growth=(0.0,) * HORIZON,  # REPLACE
    rationale=(_TODO + "per-year MedTech growth including the Abiomed contribution. "
               "Source needed: DealLab's own synergy and standalone-growth "
               "assumptions for Abiomed, plus realised MedTech growth since the "
               "Dec-2022 close. Using DealLab's figures keeps the two projects "
               "consistent; inventing new ones here would put the portfolio in "
               "contradiction with itself."),
)

BULL_EXTRA = {
    3: (Flex("gross_margin", "delta", 0.0, "judgment",
             _TODO + "consolidated gross-margin effect. FLAGGED AS THE WEAKEST ITEM "
             "IN THIS FILE: segment gross margin is not disclosed (only IM's FY2025 "
             "pretax margin, 36.9%, is available in this project's sources), so a "
             "mix-driven margin path cannot be derived the way revenue can. Either "
             "source a consolidated margin trajectory from management guidance and "
             "cite it, or delete this flex. Do not estimate it from the revenue mix "
             "-- that would be an invented segment margin wearing a derived label."),),
}

BULL = Scenario(
    name="Bull",
    thesis=("MedTech compounds above the trailing base on the Abiomed franchise, and "
            "Innovative Medicine's cliff is shallower than the base assumes as "
            "late-stage launches land. Stated as an operating case; the segment "
            "re-rating argument is made separately in the valuation section."),
    years=to_scenario_years((BULL_IM, BULL_MT), HORIZON, extra=BULL_EXTRA),
)


ALL_SCENARIOS = (BASE, BEAR, BULL)


# ---------------------------------------------------------------------------
# Constraints inherited from upstream. Stated here so the report cannot quietly
# assume more rigour exists than actually does.
# ---------------------------------------------------------------------------
INHERITED_CONSTRAINTS = (
    "ValuationLab comps are ANNUAL, not LTM. A live initiation report implying "
    "current multiples on annual figures is a real overstatement of freshness -- "
    "disclose the as-of date in the methodology section.",

    "ERP is Damodaran's January 2026 implied print, paired with a 2026-09-11 "
    "risk-free rate. ValuationLab already flags this ~8-month mismatch after a ~75bp "
    "rate move. Carry the flag forward verbatim; do not silently re-date it.",

    "Beta is Blume-adjusted from two retail sources over a 5Y window spanning the 2023 "
    "Kenvue separation. Stated in ValuationLab's CAPM basis; repeat it rather than "
    "presenting the beta as clean.",

    "FIXED IN THIS REPO: share count. Upstream used a point-in-time BASIC count from "
    "the market-data provider. Every per-share figure here uses the diluted "
    "weighted-average count from shares.py, with its own stated caveat.",

    "DEFECT FOUND UPSTREAM, NOT YET FIXED: valuationlab/scripts/run_valuation.py "
    "carries a comment calling the CAPM inputs 'placeholders with an honest label, "
    "not researched values' directly above a basis string containing dated, cited, "
    "researched figures. The comment is stale and now tells a reviewer to distrust "
    "work that is actually sourced. Fix in ValuationLab before this report cites it.",
)
