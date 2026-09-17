"""
Adapter to ValuationLab's live Trellis path.

WHY THIS DELEGATES INSTEAD OF COPYING
--------------------------------------
`load_financial_live` in ValuationLab's `scripts/run_valuation.py` does a specific,
non-obvious thing: it walks backwards from the newest year, skips stub/transition
periods, and picks the most recent year that carries EVERY field the valuation needs --
rather than just taking `max(table)`. It then derives drivers with the company
profile's sourced overrides and the same stub exclusions.

Copying that here would give two implementations of base-year selection. The moment
either changes, this report's forecast silently stops being the forecast ValuationLab's
DCF and DealLab's accretion model ran on -- which is precisely the comparability the
Base case exists to preserve. So this module loads ValuationLab's function from your
checkout and calls it. If the file moves or the function is renamed, this fails loudly
at import rather than drifting quietly.

It lives in `scripts/` rather than `src/` deliberately: it depends on a path outside
this repo, so it is configuration, not library code.

THE OFFLINE SNAPSHOT PATH IS NOT USABLE HERE
---------------------------------------------
ValuationLab's `load_financial_snapshot` returns base_year, table and forecast, but NOT
`drivers`. Scenarios are built by flexing the base drivers, so there is nothing to flex
without them. Re-deriving drivers from the snapshot table would produce a *different*
object from the one that generated the snapshot's committed forecast, so this module
refuses rather than papering over it. Use `--live`.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

#: Set VALUATIONLAB_PATH if your checkout is not a sibling of this repo.
_DEFAULT = Path(__file__).resolve().parents[2] / "valuationlab"
VALUATIONLAB_PATH = Path(os.environ.get("VALUATIONLAB_PATH", _DEFAULT))


def _load_run_valuation():
    target = VALUATIONLAB_PATH / "scripts" / "run_valuation.py"
    if not target.exists():
        raise FileNotFoundError(
            f"ValuationLab's run_valuation.py not found at {target}. Clone "
            f"ValuationLab beside this repo, or set VALUATIONLAB_PATH to your "
            f"checkout root. This module deliberately does not carry its own copy of "
            f"the loader -- two copies would drift and this report's Base case would "
            f"stop matching the forecast ValuationLab and DealLab actually ran on."
        )
    # ValuationLab's scripts import each other by bare name and its package lives
    # under src/, so both go on the path before the module is executed.
    for p in (str(VALUATIONLAB_PATH / "scripts"), str(VALUATIONLAB_PATH / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)

    spec = importlib.util.spec_from_file_location("vl_run_valuation", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(cik: int) -> dict:
    """{base_year, table, forecast, drivers, generated, trellis_version}.

    Requires TRELLIS_USER_AGENT -- Trellis raises without it, and SEC requires a
    descriptive agent. Checked here so the failure names the fix instead of surfacing
    from three frames down inside an EDGAR request.
    """
    if not os.environ.get("TRELLIS_USER_AGENT"):
        raise RuntimeError(
            'TRELLIS_USER_AGENT is not set. PowerShell:\n'
            '  $env:TRELLIS_USER_AGENT = "EquityResearch/0.1 you@example.com"\n'
            "SEC requires a descriptive User-Agent identifying the requester."
        )

    module = _load_run_valuation()
    fn = getattr(module, "load_financial_live", None)
    if fn is None:
        raise AttributeError(
            f"load_financial_live not found in {VALUATIONLAB_PATH}/scripts/"
            f"run_valuation.py. It was renamed or moved upstream -- update this "
            f"adapter rather than reimplementing base-year selection here."
        )

    data = fn(cik)
    if "drivers" not in data:
        raise KeyError(
            "ValuationLab's loader returned no 'drivers'. Scenarios are built by "
            "flexing the base drivers, so there is nothing to flex. Re-deriving them "
            "here would produce a different object from the one that generated this "
            "forecast, breaking comparability with ValuationLab and DealLab."
        )
    return data


if __name__ == "__main__":
    # Smoke test: python valuationlab_loader.py 200406
    cik = int(sys.argv[1]) if len(sys.argv) > 1 else 200406
    d = load(cik)
    print(f"base_year={d['base_year']}  years={sorted(d['table'])}")
    print(f"revenue FY{d['base_year']} = {d['table'][d['base_year']]['revenue']:,.0f}")
    print(f"drivers: revenue_growth={d['drivers'].revenue_growth:.4f} "
          f"gross_margin={d['drivers'].gross_margin:.4f}")
    for line in d["drivers"].overrides_applied:
        print(f"  override: {line}")
    for line in d["drivers"].assumptions:
        print(f"  assumption: {line}")
