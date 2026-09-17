"""
The market-implied multiple for Innovative Medicine.

WHY THIS RUNS ON DILUTED SHARES WHEN VALUATIONLAB'S SOTP DOES NOT
------------------------------------------------------------------
ValuationLab computes market cap from the provider's BASIC shares outstanding, which its
own `marketdata` docstring flags. That was tolerable there: its headline outputs are
enterprise values and method-fitness verdicts, and the share count only touched the
equity bridge at the end.

Here it is load-bearing in a way it was not upstream. Market cap is the FIRST term of
this inversion -- everything downstream is a subtraction from it -- so understating the
share base understates enterprise value, understates the residual, and understates the
implied multiple. That is the direction that would make the finding look weaker, not
stronger, which is the tolerable direction to be wrong in but not a reason to stay wrong.

So this uses the diluted weighted-average count from `shares.py` and prints both, with
the difference, so the report can state exactly what changed and why.

    python run_implied.py            # uses ValuationLab's committed snapshots
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from equityresearch.market_implied import (  # noqa: E402
    DISQUALIFYING_SPREAD, ImpliedError, Leg, assert_matches_upstream,
    implied_residual, report,
)
from equityresearch.shares import fetch_share_count  # noqa: E402

JNJ_CIK = 200406
BASE_FISCAL_YEAR = 2025

# ---------------------------------------------------------------------------
# From ValuationLab's SOTP run (snapshots a34baff, market as of 2026-09-15).
# Hardcoded rather than imported because ValuationLab exposes the SOTP as printed
# output, not as a return value this script can consume. That is a real coupling
# weakness: these figures go stale silently if the snapshots are refreshed and this
# file is not. The reconciliation check below is what catches it.
# ---------------------------------------------------------------------------
CONSOLIDATED_REVENUE = 94_193e6
NET_DEBT = 19_729e6
PRICE = 267.20
VALUATIONLAB_BASIC_SHARES = 2_409_898_597
VALUATIONLAB_THRESHOLD = 2.0

MEDTECH = Leg(name="MedTech", revenue=33_792e6, peer_group="MDT, BDX, SYK, BSX",
              peer_multiple_low=3.096, peer_multiple_median=3.794,
              peer_multiple_high=4.730)
INNOVATIVE_MEDICINE = Leg(
    name="Innovative Medicine", revenue=60_401e6, peer_group="PFE, MRK, ABBV, BMY",
    peer_multiple_low=3.379, peer_multiple_median=4.714, peer_multiple_high=8.570)


def main() -> int:
    assert_matches_upstream(VALUATIONLAB_THRESHOLD)

    if not os.environ.get("TRELLIS_USER_AGENT"):
        print('Set $env:TRELLIS_USER_AGENT = "EquityResearch/0.1 you@example.com"',
              file=sys.stderr)
        return 1

    sc = fetch_share_count(JNJ_CIK, BASE_FISCAL_YEAR)
    diluted, caveat = sc.recommended()

    print("SHARE COUNT")
    print(f"  {caveat}")
    print(f"  {sc.source}")
    delta = diluted - VALUATIONLAB_BASIC_SHARES
    print(f"  ValuationLab's SOTP uses {VALUATIONLAB_BASIC_SHARES:,.0f} basic; this run "
          f"uses {diluted:,.0f} diluted, a difference of {delta:+,.0f} shares "
          f"({delta / VALUATIONLAB_BASIC_SHARES:+.2%}). Market cap moves by "
          f"{delta * PRICE:+,.0f}, and every figure below with it.\n")

    for label, shares in (("ValuationLab basic (comparison)", VALUATIONLAB_BASIC_SHARES),
                          ("Diluted (used for the report)", diluted)):
        print("=" * 78)
        print(label)
        print("=" * 78)
        try:
            result = implied_residual(
                market_cap=PRICE * shares, net_debt=NET_DEBT, fit_leg=MEDTECH,
                residual_leg=INNOVATIVE_MEDICINE,
                consolidated_revenue=CONSOLIDATED_REVENUE)
        except ImpliedError as e:
            print(f"REFUSED: {e}\n")
            return 1
        print(report(result))
        print()

    print("=" * 78)
    print("READ THIS BEFORE QUOTING ANY NUMBER ABOVE")
    print("=" * 78)
    print(
        "  The peer multiples and segment revenues here are copied from ValuationLab's\n"
        "  printed SOTP, not imported from it -- that repo exposes the SOTP as output,\n"
        "  not as a value this script can consume. If its snapshots have been refreshed\n"
        "  since, these go stale silently. Re-run ValuationLab's run_valuation.py\n"
        "  --offline and check the three legs against the figures at the top of this\n"
        "  file before publishing. Wiring this properly means giving ValuationLab a\n"
        f"  return value, which is the right fix and a separate change.\n"
        f"\n"
        f"  Disqualification bar mirrored from ValuationLab: {DISQUALIFYING_SPREAD}x.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
