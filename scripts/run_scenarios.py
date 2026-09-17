"""
Run the J&J Bull/Base/Bear schedules.

  --checklist   print outstanding research items and exit. No network, no SEC.
  --live        pull SEC data via Trellis, run all three scenarios, print the
                comparison. Requires TRELLIS_USER_AGENT.

The checklist mode exists because the honest state of this report is "structure
decided, magnitudes not yet researched," and a tool that cannot report that state
invites someone to run it with placeholders and treat the output as a finding.
"""

import argparse
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")

from equityresearch.scenarios import (  # noqa: E402
    UNSOURCED, ScenarioError, provenance_table, research_items, run_scenario,
    tier_mix, validate,
)
from equityresearch.shares import fetch_share_count  # noqa: E402

from scenarios_jnj import (  # noqa: E402
    ALL_SCENARIOS, BASE_FISCAL_YEAR, CONSOLIDATED_FY2025, HORIZON,
    INHERITED_CONSTRAINTS,
)

JNJ_CIK = 200406


def _wrap(text: str, width: int = 88) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width) or [""]


def checklist() -> int:
    outstanding = 0
    for scen in ALL_SCENARIOS:
        # A derived revenue_growth flex inherits UNSOURCED from the segment
        # rationales it quotes -- correct: the derivation is sound, the inputs are not.
        items = research_items(scen)
        print(f"\n{'=' * 78}\n{scen.name}: {scen.thesis}\n{'=' * 78}")
        if not items:
            print("  Nothing outstanding.")
        for it in items:
            outstanding += 1
            years = ",".join(f"y+{y}" for y in it.years)
            print(f"\n  [{years}] {it.driver}")
            for line in _wrap(it.text):
                print(f"      {line}")
        print(f"\n  Evidence tier mix: {tier_mix(scen)}")

    print(f"\n{'=' * 78}\nINHERITED CONSTRAINTS\n{'=' * 78}")
    for c in INHERITED_CONSTRAINTS:
        print(f"  - {c}")
    print(f"\n{outstanding} magnitude(s) outstanding. "
          f"Scenarios will not run until these are sourced or the flex is deleted.")
    return 1 if outstanding else 0


def live() -> int:
    from valuationlab_loader import load  # user-supplied; see README
    data = load(JNJ_CIK)
    table, base_year, base_drivers = data["table"], data["base_year"], data["drivers"]

    actual = table[base_year]["revenue"]
    if abs(actual - CONSOLIDATED_FY2025) > 1.0:
        print(f"WARNING: Trellis FY{base_year} revenue {actual:,.0f} does not match "
              f"the segment base {CONSOLIDATED_FY2025:,.0f} hardcoded in "
              f"scenarios_jnj.py. The segment split is stale -- update it from the "
              f"current 10-K before trusting any derived growth path.", file=sys.stderr)

    sc = fetch_share_count(JNJ_CIK, base_year)
    denom, caveat = sc.recommended()
    print(f"\nSHARE COUNT\n  {caveat}\n  {sc.source}\n")

    for scen in ALL_SCENARIOS:
        try:
            validate(scen, HORIZON)
        except ScenarioError as e:
            print(f"\n{scen.name}: BLOCKED\n{e}\n", file=sys.stderr)
            continue
        run = run_scenario(table, base_year, base_drivers, scen, HORIZON)
        print(f"\n{'=' * 78}\n{provenance_table(scen)}\n")
        print(f"  tier mix: {tier_mix(scen)}")
        if run.reconciliation_failures:
            print("  ARITHMETIC FAILURE -- do not use these numbers:")
            for f in run.reconciliation_failures:
                print(f"    {f}")
        if run.insolvent_years:
            print(f"  FINDING: path cannot fund itself in {run.insolvent_years} "
                  f"(cash below floor with the revolver exhausted). This is an "
                  f"economic result, not a bug -- state it in the report.")
        for year in sorted(run.forecast):
            y = run.forecast[year]
            print(f"    FY{year}  rev {y['revenue'] / 1e9:8.1f}B  "
                  f"EBIT {y['operating_income'] / 1e9:7.1f}B  "
                  f"NI {y['net_income'] / 1e9:7.1f}B  "
                  f"EPS {y['net_income'] / denom:6.2f}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--checklist", action="store_true")
    g.add_argument("--live", action="store_true")
    a = p.parse_args()
    raise SystemExit(checklist() if a.checklist else live())
