"""
Test ValuationLab's dispersion premise against live peer data.

WHAT IS BEING TESTED
---------------------
ValuationLab's SOTP rests on the claim that dispersion among large-cap pharma peers is
economic rather than a small-sample artefact, evidenced by adding two more peers and
observing the spread widen. `equityresearch.dispersion` shows that evidence cannot bear
the weight: min/max spread is monotonic in sample size, so it widens whatever you add,
including draws from a single tight distribution.

This runs the replacement test on real data. It rebuilds EV/Revenue for the four peers
ValuationLab uses, then for those four plus Eli Lilly and Amgen, and compares the
coefficient of variation -- which can fall when peers are added, and therefore can
distinguish a genuinely heterogeneous set from a bigger sample of one.

This report re-underwrites the premise rather than citing it. If the CV falls, the
premise is not supported and this report says so about its own foundation, which is the
only honest option once the measurement is known to be invalid.

    python check_dispersion.py            # snapshots where available, live where not
    python check_dispersion.py --live     # force live market data for all six

CIKs FOR THE ADDED PEERS ARE VERIFIED, NOT ASSERTED
----------------------------------------------------
LLY and AMGN are not in ValuationLab's peer lists, so their CIKs are introduced here.
The script prints the entity name SEC returns for each one before using it: a wrong CIK
would otherwise produce a perfectly plausible multiple for the wrong company.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from equityresearch.dispersion import (  # noqa: E402
    DISQUALIFYING_SPREAD, compare_peer_sets, dispersion, expected_spread_under_noise,
    leave_one_out,
)

BASE_FISCAL_YEAR = 2025
BASIS = "ev_revenue"

# ValuationLab's four, so the baseline is identical to the set its SOTP actually used.
PHARMA_4 = [
    {"cik": 78003, "ticker": "PFE", "name": "Pfizer Inc."},
    {"cik": 310158, "ticker": "MRK", "name": "Merck & Co., Inc."},
    {"cik": 1551152, "ticker": "ABBV", "name": "AbbVie Inc."},
    {"cik": 14272, "ticker": "BMY", "name": "Bristol-Myers Squibb Company"},
]
# The two the premise turns on. Names below are what we EXPECT; the script checks them
# against what SEC returns and stops if they disagree.
ADDED = [
    {"cik": 59478, "ticker": "LLY", "expect": "LILLY"},
    {"cik": 318154, "ticker": "AMGN", "expect": "AMGEN"},
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="force live market data instead of ValuationLab's snapshots")
    ap.add_argument("--valuationlab", default=None,
                    help="path to the ValuationLab checkout (default: VALUATIONLAB_PATH "
                         "or a sibling of this repo)")
    args = ap.parse_args()

    if not os.environ.get("TRELLIS_USER_AGENT"):
        print('Set $env:TRELLIS_USER_AGENT = "EquityResearch/0.1 you@example.com"',
              file=sys.stderr)
        return 1

    vl = Path(args.valuationlab or os.environ.get("VALUATIONLAB_PATH",
                                                  ROOT.parent / "valuationlab"))
    if not (vl / "src").exists():
        print(f"ValuationLab not found at {vl}. Pass --valuationlab or set "
              f"VALUATIONLAB_PATH.", file=sys.stderr)
        return 1
    sys.path.insert(0, str(vl / "src"))

    from trellis.ingest import fetch_all, fetch_company_metadata
    from trellis.statements import build_annual_table, fill_derived_gaps
    from valuationlab.comps import build_peer_multiple, summarize
    from valuationlab.marketdata import get_market_data

    snapshot = vl / "data" / "snapshots" / "market.json"

    # LLY and AMGN are not in ValuationLab's snapshot set, so they can only come from a
    # live quote. Mixing them with four peers priced at the snapshot date would compare
    # multiples struck days or months apart -- and since the whole test is a comparison
    # of dispersion between the four-peer and six-peer sets, a date mismatch inside the
    # larger set would show up as dispersion that is really just price drift. Refused
    # rather than warned about: the output would look identical either way.
    import json
    have = set(json.loads(snapshot.read_text()).get("tickers", {})
               or json.loads(snapshot.read_text()))
    missing = [p["ticker"] for p in ADDED if p["ticker"] not in have]
    if missing and not args.live:
        print(f"\n{', '.join(missing)} are not in ValuationLab's market snapshot "
              f"({snapshot.name}).\nRe-run with --live so all six peers are priced on "
              f"the same date:\n\n    python check_dispersion.py --live\n\n"
              f"That will not match ValuationLab's snapshot vintage, and it does not "
              f"need to:\nthis test compares the four-peer set against the six-peer set "
              f"WITHIN one run, so\ninternal consistency of the date is what matters, "
              f"not agreement with the SOTP.\nThe alternative is adding both tickers to "
              f"ValuationLab's snapshot set, which is\nthe better long-term fix and a "
              f"separate change.", file=sys.stderr)
        return 1
    if args.live:
        print("LIVE MODE: all six peers priced at today's quote, not ValuationLab's "
              "snapshot.\nInternally consistent, so the dispersion comparison is valid; "
              "the absolute\nmultiples will not match the SOTP run.\n")

    def multiple(peer: dict) -> float:
        obs = fetch_all(cik=peer["cik"])
        built = build_annual_table(obs)
        fill_derived_gaps(built.table)
        year_data = built.table.get(BASE_FISCAL_YEAR)
        if not year_data or "revenue" not in year_data:
            raise SystemExit(f"{peer['ticker']}: no FY{BASE_FISCAL_YEAR} revenue.")
        market = get_market_data(peer["ticker"], snapshot, prefer_live=args.live)
        pm = build_peer_multiple(peer["ticker"], peer.get("name", peer["ticker"]),
                                 BASE_FISCAL_YEAR, year_data, market)
        print(f"  {pm.ticker:<6} EV/Revenue {pm.ev_revenue:>6.3f}x   "
              f"EV {pm.enterprise_value/1e9:>7.1f}B on revenue "
              f"{pm.revenue/1e9:>6.1f}B   market {market.as_of} ({market.source})")
        return pm.ev_revenue

    print("VERIFYING THE ADDED CIKs BEFORE USING THEM")
    for peer in ADDED:
        meta = fetch_company_metadata(peer["cik"])
        name = (meta.get("name") or meta.get("entityName") or "").upper()
        print(f"  CIK {peer['cik']} -> {name or '(no name returned)'}  "
              f"SIC {meta.get('sic')} {meta.get('sic_description') or ''}")
        if peer["expect"] not in name:
            print(f"  STOP: expected a name containing {peer['expect']!r}. A wrong CIK "
                  f"produces a plausible multiple for the wrong company.", file=sys.stderr)
            return 1
        peer["name"] = name.title()

    print(f"\nBASELINE -- the four peers ValuationLab's SOTP uses")
    four = [multiple(p) for p in PHARMA_4]

    print(f"\nEXTENDED -- the same four plus the two the premise turns on")
    six = four + [multiple(p) for p in ADDED]

    print("\n" + "=" * 78)
    print("DISPERSION PREMISE")
    print("=" * 78)
    result = compare_peer_sets(four, six, tuple(p["ticker"] for p in ADDED))
    print(result.verdict())

    print("\n" + "=" * 78)
    print("LEAVE-ONE-OUT -- does the result rest on a single company?")
    print("=" * 78)
    print(leave_one_out(four, {p["ticker"]: m
                               for p, m in zip(ADDED, six[len(four):])}).describe())

    print("\n" + "=" * 78)
    print("IS THIS SPREAD SURPRISING UNDER A SINGLE DISTRIBUTION?")
    print("=" * 78)
    for d in (result.small, result.large):
        mean, p = expected_spread_under_noise(
            d.n, d.coefficient_of_variation, threshold=DISQUALIFYING_SPREAD)
        print(f"  n={d.n}: observed min/max {d.min_max_spread:.2f}x. Drawing {d.n} "
              f"peers from one distribution with this CV gives a mean spread of "
              f"{mean:.2f}x and exceeds the {DISQUALIFYING_SPREAD:.1f}x bar {p:.0%} of "
              f"the time.")
    print("\n  The disqualification bar is not scale-free: the same peer set trips it "
          "\n  more readily as it grows. Any change to peer-set size changes what "
          "\n  'spread exceeds 2.0x' means, independently of comparability.")

    print("\n" + "=" * 78)
    print("WHAT THIS DOES NOT TOUCH")
    print("=" * 78)
    print("  The SOTP's fitness verdicts compare MedTech at four peers against\n"
          "  Innovative Medicine at four peers. Equal n, so the monotonicity above\n"
          "  cancels and 1.5x against 2.5x is a fair comparison between equal-sized\n"
          "  sets. Those verdicts stand. What is in question is only the separate\n"
          "  argument for WHY pharma dispersion is wide.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
