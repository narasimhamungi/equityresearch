"""
J&J Bull / Base / Bear scenario definitions, with magnitudes sourced.

WHAT CHANGED FROM THE FIRST DRAFT, AND WHY IT MATTERED
--------------------------------------------------------
The first version of this file built the Bear case around "the Innovative Medicine
patent cliff arrives faster and deeper than the base assumes." That framing was wrong,
and the filings say so plainly: the cliff already arrived and the company absorbed it.
Stelara lost US exclusivity in 2025, its sales fell 41.3% to $6.08bn, it took roughly
10.4 percentage points off Innovative Medicine's worldwide operational sales growth --
and the segment still grew 5.3% operationally to $60.4bn, its first year above $60bn,
with thirteen brands growing double digits.

Writing a downside case around an event that has already happened and been survived
would have produced a Bear scenario barely distinguishable from the Base, and the error
would have been invisible in the output: the numbers would have looked like a
considered downside. The forward question is not Stelara. It is what comes next.

WHAT COMES NEXT, AND THE ONE THING WORTH BUILDING A SCENARIO ON
----------------------------------------------------------------
Near term, 2026 carries several dated items at once: Medicare negotiated prices take
effect for Stelara, Xarelto and Imbruvica, Uptravi's patent expires with roughly $1bn
of sales exposed, Opsumit's composition patent expires, and the residual Stelara
decline continues off a smaller base.

The item that actually decides the five-year path is further out and is a POLICY
question rather than a patent one. Darzalex is J&J's largest product at $14.35bn in
2025, growing 23%. Its subcutaneous form, Darzalex Faspro, carries more than 80% of
that revenue. Under the IRA's original treatment, Faspro's additional active ingredient
restarted the 13-year clock and pushed negotiation eligibility to 2034 while the infused
form became eligible in 2029. CMS then signalled it was rethinking that approach --
which would collapse Faspro's protection to 2029, five years early -- and the ORPHAN
Cures Act provisions in the One Big Beautiful Bill Act subsequently expanded the orphan
exclusion to serial orphan designations, which on one reading removes Darzalex from
negotiation eligibility altogether.

Those two readings are worth billions a year from 2029, both are documented, and the
question is unresolved. That is what Bear and Bull are built on: not a guess about how
fast a known decline runs, but an open question with a dated answer and a large,
calculable difference between its branches.

EVIDENCE TIERS ARE APPLIED STRICTLY HERE
------------------------------------------
Every growth flex below is tagged `judgment`, not `sourced`, and that is deliberate even
where the underlying facts are filed. The FACTS are sourced -- Stelara's decline, the
2026 IRA effective dates, the talc payment schedule, the Darzalex eligibility dispute --
and each basis string cites them. The MAPPING from those facts to a particular growth
rate in a particular year is the analyst's, and tagging it `sourced` because its inputs
are sourced would launder a judgment into a citation. The exception is the talc cash
schedule, which J&J itself has stated as amounts and years.

The magnitudes below are a first calibration and should be reviewed rather than
inherited. The engine will run them; that is not the same as their being right.
"""

from equityresearch.scenarios import Flex, Scenario, ScenarioYear  # noqa: F401
from equityresearch.segment_bridge import SegmentPath, to_scenario_years

HORIZON = 5
BASE_FISCAL_YEAR = 2025

IM_FY2025 = 60_401_000_000.0
MT_FY2025 = 33_792_000_000.0
CONSOLIDATED_FY2025 = 94_193_000_000.0

IM_SOURCE = ("J&J FY2025 segment sales: TOTAL INNOVATIVE MEDICINE worldwide $60,401M, "
             "+5.3% operational, +4.1% organic")
MT_SOURCE = ("J&J FY2025: consolidated $94,193M less Innovative Medicine $60,401M; "
             "MedTech +5.4% operational, of which +1.1% from acquisitions (Shockwave)")

# Facts the bases cite, named so a reader can see what each scenario rests on without
# reading every basis string end to end.
F_STELARA = ("Stelara lost US exclusivity in 2025; sales -41.3% to $6.08bn; approx "
             "-10.4% impact on IM worldwide operational sales (J&J FY2025 ARS)")
F_IRA_2026 = ("Medicare negotiated prices take effect in 2026 for Stelara, Xarelto and "
              "Imbruvica")
F_2026_LOE = "Uptravi patent expiry (~$1bn sales exposed) and Opsumit composition expiry"
F_DARZALEX = ("Darzalex $14.35bn in 2025, +23.0%; Faspro carries >80% of it. Infused "
              "form IRA-eligible 2029; Faspro to 2034 under the original additional-"
              "active-ingredient treatment. CMS signalled a rethink that would collapse "
              "Faspro to 2029; ORPHAN Cures Act provisions in the OBBBA then expanded "
              "the orphan exclusion to serial orphans, which on one reading removes "
              "Darzalex from eligibility entirely. UNRESOLVED")
F_GROWTH = ("Darzalex +23.0% to $14.35bn, Tremfya +40.5% to $5.2bn (protected to 2031), "
            "Erleada +19.2% to $3.57bn; Carvykti, Tecvayli, Talvey, Rybrevant/Lazcluze "
            "and Spravato all contributing (J&J FY2025 results)")
F_MEDTECH = ("MedTech FY2025 +5.4% operational, +1.1% from Shockwave, so ~4.3% organic; "
             "growth led by electrophysiology and Abiomed in Cardiovascular and wound "
             "closure in General Surgery (J&J FY2025 results)")
F_TALC = ("J&J 8-K, 27 July 2026: $5.5bn comprehensive talc resolution covering ~76,000 "
          "ovarian claims, conditioned on >=95% claimant participation. First payment "
          "capped at $3bn in 2027, no further payments due until 2028")


# THE TALC SETTLEMENT IS NOT MODELLED, AND COULD NOT BE
# -------------------------------------------------------
# Both scenarios originally carried the talc payment as a `debt_repayment` flex, tagged
# `sourced`, citing J&J's 8-K, appearing in the provenance table. It did nothing.
#
# Trellis plugs cash: `long_term_debt = prior_debt - debt_repayment`, and the cash
# balance absorbs the offsetting financing flow. Measured directly on a single projected
# year, net debt came out at 7.0bn with no flex, 7.0bn with +3bn, and 7.0bn with -3bn.
# That is arithmetically CORRECT for an actual debt repayment -- paying debt with cash
# leaves net debt unchanged -- and it is exactly wrong for a litigation settlement, where
# cash leaves to a third party, debt does not move, and net debt should RISE by the
# payment. Trellis has no driver that reduces cash without also reducing debt.
#
# The first attempt at this used a NEGATIVE value on the reasoning that cash out should
# be negative, which modelled J&J borrowing $3bn instead. Flipping the sign corrected the
# reasoning and changed nothing, because the mechanism was never capable of it.
#
# So the flexes are removed. A flex that shows up in the provenance table with an 8-K
# citation and moves no number is worse than an absent one: it manufactures the
# appearance of having priced the settlement. The exposure is stated in
# INHERITED_CONSTRAINTS instead, where a reader will see it is NOT in the numbers.
#
# Upstream: Trellis's driver set has no one-off cash outflow, which any company facing a
# settlement, a fine or a large legal payment will need. Worth raising there.

J = "judgment"


# ---------------------------------------------------------------------------
# BASE -- Trellis's derived drivers, untouched
# ---------------------------------------------------------------------------
BASE = Scenario(
    name="Base",
    thesis=("Trellis's 5-year driver-based forecast, unmodified: trailing-window drivers "
            "held flat at a 4.58% consolidated revenue CAGR. The same forecast "
            "ValuationLab's DCF and DealLab's accretion model consumed, carried through "
            "without re-basing."),
    years=(),
)


# ---------------------------------------------------------------------------
# BEAR -- the Darzalex exemption falls, and 2026's dated items all land
# ---------------------------------------------------------------------------
BEAR_IM = SegmentPath(
    name="Innovative Medicine", base_revenue=IM_FY2025, source=IM_SOURCE,
    growth=(-0.020, 0.010, 0.025, -0.030, -0.010),
    rationale=(
        "FY2026 -2.0%: three dated items land together -- " + F_IRA_2026 + "; " +
        F_2026_LOE + "; residual Stelara decline off a base already down 41% (" +
        F_STELARA + "). FY2027 +1.0%, FY2028 +2.5%: Stelara's remaining base is small "
        "enough to stop dominating and " + F_GROWTH + " reasserts. FY2029 -3.0%, FY2030 "
        "-1.0%: the Darzalex branch goes against J&J -- " + F_DARZALEX + ". MAGNITUDES "
        "ARE THE ANALYST'S; the dates and the products are filed"),
)
BEAR_MT = SegmentPath(
    name="MedTech", base_revenue=MT_FY2025, source=MT_SOURCE,
    growth=(0.030, 0.030, 0.030, 0.030, 0.030),
    rationale=(
        "3.0% flat, below FY2025's ~4.3% organic. Deliberately NOT a mirror of the IM "
        "decline: the Bear case is a pharma-policy case, and forcing MedTech down with "
        "it would turn a specific thesis into a generic haircut. The step down reflects "
        "Shockwave and Abiomed contributions annualising, not deterioration. " +
        F_MEDTECH),
)

BEAR_EXTRA = {
    2: (Flex("rnd_pct_revenue", "delta", 0.005, J, expect="cost", basis=
             "FY2027 +50bp of revenue in R&D, defending against the 2029 Darzalex "
             "branch. Anchored on J&J's own disclosed R&D trajectory rather than a round "
             "number, but the step itself is the analyst's"),),
}

BEAR = Scenario(
    name="Bear",
    thesis=("2026's dated items land together -- IRA negotiated prices on three "
            "products, Uptravi and Opsumit expiries, residual Stelara decline -- and the "
            "Darzalex orphan exemption fails, exposing J&J's largest product to Medicare "
            "negotiation from 2029. MedTech is not assumed to deteriorate. Talc is NOT in "
            "these numbers -- see INHERITED_CONSTRAINTS."),
    years=to_scenario_years((BEAR_IM, BEAR_MT), HORIZON, extra=BEAR_EXTRA),
)


# ---------------------------------------------------------------------------
# BULL -- the exemption holds, and the launch portfolio carries
# ---------------------------------------------------------------------------
# Note what this case does NOT flex: any multiple. ValuationLab's finding that MedTech
# values cleanly while Innovative Medicine does not is evidence about valuation METHOD.
# Building a re-rating into the forecast would bury a valuation argument inside an
# operating one, where no reader could challenge it separately. The re-rating case
# belongs in the valuation section, argued on its own.
BULL_IM = SegmentPath(
    name="Innovative Medicine", base_revenue=IM_FY2025, source=IM_SOURCE,
    growth=(0.030, 0.050, 0.060, 0.060, 0.050),
    rationale=(
        "The Darzalex branch goes J&J's way: the expanded orphan exclusion holds and "
        "Faspro keeps protection to 2034 (" + F_DARZALEX + "), removing the largest "
        "forward risk from the horizon. FY2026 +3.0% still absorbs the 2026 items the "
        "Bear case carries (" + F_IRA_2026 + "; " + F_2026_LOE + ") -- those are dated "
        "facts, not scenario-dependent. FY2027-FY2030 accelerate on " + F_GROWTH +
        ". MAGNITUDES ARE THE ANALYST'S"),
)
BULL_MT = SegmentPath(
    name="MedTech", base_revenue=MT_FY2025, source=MT_SOURCE,
    growth=(0.045, 0.050, 0.050, 0.048, 0.045),
    rationale=(
        "ORGANIC rates, not FY2025's reported 5.4%, and the difference is deliberate. "
        "1.1pp of that reported figure came from Shockwave (" + F_MEDTECH + "), and "
        "Trellis grows revenue at the driver rate WITHOUT charging for the acquisition "
        "that produced it, while simultaneously sweeping every spare dollar into "
        "buybacks. Running MedTech at the reported rate would therefore book "
        "acquisition-driven growth AND return the cash that bought it -- the same "
        "dollar counted twice. The path here sits just above FY2025's ~4.3% organic, "
        "which is what the model can actually fund. If MedTech deserves the reported "
        "rate, the acquisition spend has to come out of the buyback sweep, and Trellis "
        "has no line for that. MAGNITUDES ARE THE ANALYST'S"),
)

BULL_EXTRA: dict[int, tuple[Flex, ...]] = {}

BULL = Scenario(
    name="Bull",
    thesis=("The Darzalex orphan exemption holds and Faspro retains protection to 2034, "
            "removing the largest forward risk from the horizon. The launch portfolio -- "
            "Darzalex, Tremfya, Erleada, Carvykti, Rybrevant -- carries Innovative "
            "Medicine through the 2026 items. MedTech grows at ORGANIC rates, not its "
            "reported 5.4%, because this model cannot pay for the acquisitions that "
            "produced the difference -- see INHERITED_CONSTRAINTS. "
            "Stated as an operating case; the segment re-rating argument is made "
            "separately in the valuation section."),
    years=to_scenario_years((BULL_IM, BULL_MT), HORIZON, extra=BULL_EXTRA),
)


ALL_SCENARIOS = (BASE, BEAR, BULL)


INHERITED_CONSTRAINTS = (
    "ValuationLab comps are ANNUAL, not LTM. Disclose the as-of date in methodology "
    "rather than implying current multiples.",

    "ERP is Damodaran's January 2026 implied print against a 2026-09-11 risk-free rate. "
    "ValuationLab flags the ~8-month mismatch; carry the flag forward verbatim.",

    "Beta is Blume-adjusted from two retail sources over a 5Y window spanning the 2023 "
    "Kenvue separation. Repeat that rather than presenting the beta as clean.",

    "FIXED IN THIS REPO: share count. Every per-share figure uses the diluted "
    "weighted-average count from shares.py, not the basic count used upstream.",

    "TALC IS NOT IN THE NUMBERS. " + F_TALC + ". Trellis has no driver for a one-off "
    "cash outflow -- debt_repayment moves debt and the cash plug together and leaves net "
    "debt unchanged, which is right for a debt repayment and wrong for a settlement. So "
    "$5.5bn of committed cash, and the further exposure if the 95% participation "
    "condition is not met, sit OUTSIDE every scenario above. Deduct it from equity value "
    "by hand, or state it as an unpriced risk. Do not read these cases as having "
    "absorbed it.",

    "ACQUISITION GROWTH IS NOT PAID FOR. Trellis grows revenue at the driver rate and "
    "charges nothing for the deals that produced the historical rate, while "
    "sweep_to_buybacks returns every spare dollar to shareholders -- so modelled "
    "buybacks run ~2.3x J&J's actual $5.95bn FY2025 repurchases. The Bull MedTech path "
    "is set to organic rates rather than reported for exactly this reason. The Base "
    "case, being Trellis unmodified, still carries the double-count: its 4.58% CAGR is "
    "derived from history that includes acquired growth. Read Base as the upper end of "
    "what organic performance alone supports.",

    "The Darzalex branch is not a magnitude the analyst chose; it is an unresolved policy "
    "question, and Bear and Bull take opposite sides of it deliberately. That is why "
    "their spread is wide. Do not average them -- the midpoint corresponds to no state "
    "of the world.",
)
