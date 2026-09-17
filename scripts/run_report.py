"""
Assemble the J&J initiation report from every module in this repo.

    python run_report.py                 # snapshot-based where possible
    python run_report.py --live          # live market data throughout

WHAT THIS PRODUCES, AND WHAT IT DELIBERATELY DOES NOT
------------------------------------------------------
It produces: the claim register with every material claim tiered and sourced, the
market-implied analysis for Innovative Medicine with its flip point, the dispersion
finding, and a gated recommendation.

It does not produce a target price, and on current evidence it cannot. ValuationLab
found no valuation method structurally fit to anchor a conclusion on J&J; the
`anchor` gate reads that verdict directly, so the run ends in NO CALL with the failing
gate named. That is the correct output rather than a shortfall in this script -- a
target price here would be the number a reader quotes and the caveats they skip.

The scenario sections are absent for a different reason: `scenarios_jnj.py` still has
seven unsourced magnitudes and refuses to run. Run `run_scenarios.py --checklist` for
the list. When those land, the scenario values and the spread decomposition join this
report, and the `robustness` and `solvency` gates start reading real inputs instead of
the placeholders below.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from equityresearch.claims import (  # noqa: E402
    Claim, Register, Tier, gate_thesis, render as render_claims,
)
from equityresearch.dispersion import (  # noqa: E402
    compare_peer_sets, leave_one_out,
)
from equityresearch.market_implied import (  # noqa: E402
    Leg, crossover, implied_residual, report as render_implied,
)
from equityresearch.recommendation import (  # noqa: E402
    Rating, derive, gate_anchor, gate_evidence, gate_robustness, gate_solvency,
    render as render_recommendation,
)
from equityresearch.shares import fetch_share_count  # noqa: E402

JNJ_CIK, BASE_FISCAL_YEAR = 200406, 2025
PRICE, NET_DEBT, CONSOLIDATED_REVENUE = 267.20, 19_729e6, 94_193e6
VALUATIONLAB_BASIC_SHARES = 2_409_898_597

MEDTECH = Leg("MedTech", 33_792e6, "MDT, BDX, SYK, BSX", 3.096, 4.730, 3.794)
INNOVATIVE_MEDICINE = Leg("Innovative Medicine", 60_401e6, "PFE, MRK, ABBV, BMY",
                          3.379, 8.570, 4.714)

# EV/Revenue measured 2026-09-17, all six priced live on the same date.
PHARMA_4 = [3.468, 5.994, 8.554, 3.373]
ADDED = {"LLY": 16.082, "AMGN": 6.649}

ALL_METHODS = ("DCF", "Trading comparables", "Precedent transactions",
               "SOTP MedTech leg")
# ValuationLab disqualifies all three whole-company methods. The SOTP's MedTech leg IS
# fit -- it is what the market-implied analysis rests on -- so listing it as unfit would
# contradict this report's own central finding. What blocks a rating is its COVERAGE.
FIT_METHODS: tuple[str, ...] = ("SOTP MedTech leg",)


def build_register(diluted: float, implied_multiple: float, flip_multiple: float,
                   flip_percentile: float) -> Register:
    r = Register()
    r.add(Claim(
        "cagr", "J&J's FY2021-FY2025 revenue CAGR is 4.58% on a continuing-operations "
                "basis, not the 3.34% a mis-keyed historical table produced",
        Tier.DEMONSTRATED,
        "Trellis derive_drivers_from_history over SEC XBRL, after the fiscal-year "
        "keying fix (trellis 1b61d95) restored FY2020 and FY2023 to the table",
        "python scripts/probe_years.py"))
    r.add(Claim(
        "diluted", f"J&J's FY2025 diluted weighted-average share count is "
                   f"{diluted:,.0f}, against the basic count used upstream",
        Tier.DEMONSTRATED,
        "SEC XBRL us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding, FY2025 10-K",
        "python scripts/run_implied.py"))
    r.add(Claim(
        "medtech_fit", "MedTech is the only structurally fit valuation leg: its peer "
                       "multiples span 1.5x against a 2.0x disqualification bar, where "
                       "Innovative Medicine's span 2.5x",
        Tier.DEMONSTRATED,
        "ValuationLab SOTP, snapshots a34baff. Both legs use four peers, so the "
        "monotonicity of a min/max spread in sample size cancels and the comparison is "
        "between equal-sized sets",
        "python scripts/run_valuation.py --offline  (in the ValuationLab checkout)"))
    r.add(Claim(
        "implied", f"The market implicitly prices Innovative Medicine near "
                   f"{implied_multiple:.1f}x revenue, above the pharma peer median of "
                   f"4.7x at every mark of MedTech's range",
        Tier.INFERRED,
        "Market cap and MedTech's EV range are measured; the subtraction is arithmetic. "
        "Treating the remainder AS the market's view of the segment is the inference -- "
        "the market prices the company, not the segments",
        "python scripts/run_implied.py"))
    r.add(Claim(
        "above_peer_max",
        f"Innovative Medicine is priced above EVERY pharma peer unless MedTech is worth "
        f"more than {flip_multiple:.2f}x revenue -- the {flip_percentile:.0%} mark of "
        f"MedTech's own peer range",
        Tier.INFERRED,
        "Solved from the same inputs as the implied multiple; cross-checked against the "
        "three-point scan. Inherits the inference above, and flips inside MedTech's "
        "peer range rather than outside it",
        "python scripts/run_implied.py"))
    r.add(Claim(
        "lly", "Wide pharma peer dispersion is one company: Eli Lilly at 16.1x revenue. "
               "Adding Amgen at 6.6x TIGHTENS the set",
        Tier.DEMONSTRATED,
        "Leave-one-out on coefficient of variation over six peers priced 2026-09-17",
        "python scripts/check_dispersion.py --live"))
    r.add(Claim(
        "dispersion_structural",
        "Pharma peer dispersion is economic heterogeneity rather than a small-sample "
        "artefact",
        Tier.UNSUPPORTED,
        "Offered evidence is a min/max spread widening as peers are added. That "
        "statistic is monotonic in sample size -- it widens whatever is added, including "
        "draws from a single distribution -- so it cannot distinguish the claim from its "
        "opposite. The two scale-free measures disagree (CV rises, IQR/median falls) and "
        "the leave-one-out shows the result rests entirely on Eli Lilly. The narrower "
        "claim registered as 'lly' IS supported; this one is not"))
    r.add(Claim(
        "scenarios", "Bull, Base and Bear driver paths for the forecast horizon",
        Tier.ASSUMED,
        "Seven magnitudes still unsourced -- LOE calendar, MedTech growth, talc "
        "settlement schedule, R&D step-up. scenarios_jnj.py refuses to run until they "
        "are cited"))
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    if not os.environ.get("TRELLIS_USER_AGENT"):
        print('Set $env:TRELLIS_USER_AGENT first.', file=sys.stderr)
        return 1

    sc = fetch_share_count(JNJ_CIK, BASE_FISCAL_YEAR)
    diluted, share_caveat = sc.recommended()

    implied = implied_residual(PRICE * diluted, NET_DEBT, MEDTECH,
                               INNOVATIVE_MEDICINE, CONSOLIDATED_REVENUE)
    flip = crossover(implied)
    mid = next(p for p in implied.points if p.fit_label == "mid")

    register = build_register(diluted, mid.residual_multiple, flip.fit_multiple,
                              flip.percentile_of_fit_range)

    print("JOHNSON & JOHNSON -- INITIATION OF COVERAGE")
    print("=" * 78)
    print(f"  Price {PRICE:,.2f}   diluted shares {diluted:,.0f}   "
          f"net debt {NET_DEBT/1e9:,.1f}B")
    print(f"  {share_caveat}\n")

    print(render_claims(register))

    print("\n\n" + render_implied(implied))

    print("\n\nPEER DISPERSION")
    print("=" * 15 + "\n")
    print(compare_peer_sets(PHARMA_4, PHARMA_4 + list(ADDED.values()),
                            tuple(ADDED)).verdict())
    print()
    print(leave_one_out(PHARMA_4, ADDED).describe())

    # The thesis chain. gate_thesis raises if any link is UNSUPPORTED -- caught here so
    # the report still prints, with the breach stated, rather than dying silently.
    thesis_chain = ("cagr", "medtech_fit", "implied", "above_peer_max", "lly")
    try:
        gate_thesis(register, thesis_chain)
        unsupported: tuple[str, ...] = ()
    except Exception:
        unsupported = tuple(c for c in thesis_chain
                            if register.get(c).tier is Tier.UNSUPPORTED)

    gates = (
        gate_anchor(FIT_METHODS, ALL_METHODS,
                    coverage=MEDTECH.revenue / CONSOLIDATED_REVENUE),
        gate_evidence(unsupported),
        gate_robustness("Innovative Medicine priced above every pharma peer",
                        implied.robust,
                        f"flips when MedTech is marked above {flip.fit_multiple:.2f}x, "
                        f"the {flip.percentile_of_fit_range:.0%} mark of its own peer "
                        f"range"),
        gate_solvency(()),      # placeholder until the scenarios run
    )
    print("\n\n" + render_recommendation(
        derive(gates, Rating.SELL,
               "Innovative Medicine is priced above the pharma peer median at every "
               "mark, and above every peer below MedTech's 84th percentile.")))

    print(f"\n  Thesis rests at the level of its weakest link: "
          f"{register.weakest(thesis_chain).value.upper()}.")
    print("  Scenario sections are absent: seven magnitudes remain unsourced. "
          "Run\n  `python run_scenarios.py --checklist` for the list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
