"""
What does this filer actually tag, annually, in its 10-Ks?

`diagnose_tags.py` answers "does the filer use THESE candidate tags" -- which only
helps when the right tag is already on the candidate list. This answers the prior
question: what is in the payload at all. Use it when a filer comes back nearly empty
and you do not yet know what to look for.

Abbott (CIK 1800) is the case this was written for: `AccountsReceivableNetCurrent`
returns HTTP 200 with zero facts behind it, while `long_term_debt` resolves normally --
so the session, headers and filters are all working, and the tags Trellis looks for
simply are not where the data is.

    python probe_filer.py 1800
    python probe_filer.py 1800 --contains Receivable
"""

import argparse
import collections
import os
import sys

if not os.environ.get("TRELLIS_USER_AGENT"):
    sys.exit('Set $env:TRELLIS_USER_AGENT = "EquityResearch/0.1 you@example.com" first.')

from trellis.ingest import _headers, make_session

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("cik", type=int)
p.add_argument("--contains", default=None,
               help="only show concepts whose name contains this substring")
p.add_argument("--year", type=int, default=None, help="restrict to one fiscal year")
a = p.parse_args()

session = make_session()
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{a.cik:010d}.json"
print(f"fetching {url}\n")
resp = session.get(url, headers=_headers(), timeout=60)
resp.raise_for_status()
facts = resp.json()

print(f"entity: {facts.get('entityName')}")
taxonomies = facts.get("facts", {})
print(f"taxonomies present: {list(taxonomies)}\n")

rows_by_concept: dict[str, list[dict]] = {}
for taxonomy, concepts in taxonomies.items():
    for name, node in concepts.items():
        if a.contains and a.contains.lower() not in name.lower():
            continue
        rows = [r for unit in node.get("units", {}).values() for r in unit]
        annual = [r for r in rows
                  if r.get("fp") == "FY"
                  and str(r.get("form", "")).startswith("10-K")
                  and (a.year is None or r.get("fy") == a.year)]
        if annual:
            rows_by_concept[f"{taxonomy}:{name}"] = annual

print(f"{len(rows_by_concept)} concept(s) with FY/10-K facts"
      + (f" containing '{a.contains}'" if a.contains else "")
      + (f" for fy={a.year}" if a.year else "") + "\n")

# Most-recent fiscal year per concept, so a concept that stopped being used is visible.
summary = []
for concept, rows in rows_by_concept.items():
    years = sorted({r.get("fy") for r in rows if r.get("fy")})
    latest = rows[-1]
    summary.append((years[-1] if years else 0, concept, len(rows),
                    years[0] if years else None, years[-1] if years else None,
                    latest.get("end"), latest.get("val")))

summary.sort(key=lambda t: (-t[0], t[1]))
for _, concept, n, y0, y1, end, val in summary:
    v = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
    print(f"  {concept:<70} {n:>4} rows  fy{y0}-{y1}  last {end}  {v}")

if not rows_by_concept:
    print("  Nothing. Either the CIK is wrong, or this filer's facts are filed under a "
          "different entity -- check entityName above against who you expected.")

print("\nform/fp distribution across ALL facts (is the FY/10-K filter the problem?):")
forms = collections.Counter()
fps = collections.Counter()
for taxonomy, concepts in taxonomies.items():
    for node in concepts.values():
        for unit in node.get("units", {}).values():
            for r in unit:
                forms[r.get("form")] += 1
                fps[r.get("fp")] += 1
print(f"  forms: {dict(forms.most_common(8))}")
print(f"  fp:    {dict(fps.most_common(8))}")
