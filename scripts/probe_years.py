"""
Why is FY2020 absent from J&J's historical table?

Trellis keys the annual table by the CALENDAR YEAR OF period_end, not by the fiscal
year SEC labels the fact with -- a deliberate choice, and correct, because SEC's `fy`
field reflects which filing republished a comparative, not which period it describes.

The consequence for a filer whose fiscal year ends on the Sunday nearest 31 December
is that some fiscal years close in EARLY JANUARY of the following calendar year, and
therefore land in the next year's bucket. J&J's FY2025 10-K is `jnj-20251228.htm`
(period end 28 Dec 2025 -> bucket 2025), but 53-week years close in January and shift
by one. Two fiscal years can then collide in the same bucket, and one is dropped.

So the question is not "is FY2020 missing data" but "what period does each bucket
actually cover, and did two fiscal years collide". Those are different problems with
different fixes, and the difference matters: a shifted label with a collision means the
lookback window spans more fiscal years than it has intervals, which would OVERSTATE
the derived revenue CAGR -- the single number every scenario is measured against.

Run:  python probe_years.py
"""

import os
import sys

if not os.environ.get("TRELLIS_USER_AGENT"):
    sys.exit('Set $env:TRELLIS_USER_AGENT = "EquityResearch/0.1 you@example.com" first.')

from trellis.ingest import fetch_all
from trellis.statements import build_annual_table, fill_derived_gaps

CIK = 200406
LOOKBACK_END, LOOKBACK_YEARS = 2025, 5

raw = fetch_all(CIK)
result = build_annual_table(raw)
table = result.table
fill_derived_gaps(table)

# period_end is carried per observation, not into the table, so recover the authoritative
# date per year from the raw revenue observations.
# Observation carries period_end and SEC's own fiscal_year label. Printing both is
# the point: where they disagree, the bucket is shifted relative to the fiscal year
# the company itself calls it, which is exactly what a January close produces.
ends: dict[int, set[tuple[str, int]]] = {}
for obs in raw.get("revenue", []):
    if obs.fiscal_period != "FY" or not obs.period_end:
        continue
    ends.setdefault(int(obs.period_end[:4]), set()).add(
        (obs.period_end, obs.fiscal_year))

print("=" * 78)
print("BUCKET -> PERIOD END(S) SEEN IN RAW REVENUE OBSERVATIONS")
print("=" * 78)
for year in sorted(table):
    rev = table[year].get("revenue")
    seen = sorted(ends.get(year, set()))
    rev_s = f"{rev / 1e9:7.2f}B" if rev else "    n/a"
    print(f"  {year}  revenue {rev_s}   period_end (SEC fy label): "
          + ", ".join(f"{pe} (fy={fy})" for pe, fy in seen))

print("\n" + "=" * 78)
print("COLLISIONS -- two distinct periods competing for one bucket")
print("=" * 78)
if not result.fye_collisions:
    print("  None. Every bucket resolved to a single period.")
for c in result.fye_collisions:
    print(f"  {c.year} {c.canonical_name}: kept {c.kept_period_end}, "
          f"DROPPED {c.dropped_period_end}")

print("\n" + "=" * 78)
print("STUB / TRANSITION PERIODS -- excluded from driver derivation")
print("=" * 78)
if not result.stub_periods:
    print("  None.")
for s in result.stub_periods:
    print(f"  {s.year}: ends {s.period_end}, {s.duration_days} days")

print("\n" + "=" * 78)
print("WHAT THE DERIVED CAGR IS ACTUALLY MEASURING")
print("=" * 78)
window = [y for y in range(LOOKBACK_END - LOOKBACK_YEARS + 1, LOOKBACK_END + 1)
          if y in table]
print(f"  Lookback buckets: {window}")
if len(window) >= 2:
    first, last = table[window[0]].get("revenue"), table[window[-1]].get("revenue")
    intervals = len(window) - 1
    if first and last:
        cagr = (last / first) ** (1 / intervals) - 1
        print(f"  {window[0]} revenue {first / 1e9:.2f}B -> {window[-1]} "
              f"{last / 1e9:.2f}B over {intervals} interval(s) = {cagr:.2%}")
        print(f"\n  CHECK: do the period_end dates above show {intervals} fiscal years "
              f"elapsed,\n  or more? If more, a fiscal year was lost to a collision and "
              f"this CAGR is\n  overstated -- it divides a longer span by too few "
              f"intervals.")
