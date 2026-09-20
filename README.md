# EquityResearch

Initiation-of-coverage analysis on Johnson & Johnson, built on
[Trellis](https://github.com/narasimhamungi/trellis) (SEC XBRL ingestion and driver-based
forecasting) and [ValuationLab](https://github.com/narasimhamungi/valuationlab) (DCF,
comps, precedents, sum-of-the-parts).

**Status: analysis complete, prose sections unwritten.** Scenario magnitudes are sourced
to J&J's FY2025 results, the 2026 IRA effective dates, and the 27 July 2026 talc 8-K.
Three things sit deliberately outside the numbers and are disclosed on every run: the
$5.5bn talc cash (Trellis has no one-off-outflow driver), acquisition spend (the sweep
policy has no M&A line, so modelled buybacks run ~2.3x actual), and equity-compensation
issuance. Industry and competitive positioning are not written.

---

## The problem

ValuationLab's verdict on J&J is that **no valuation method is structurally fit to anchor
a conclusion**: the DCF's terminal value is 82% of enterprise value, the precedent deals
disagree 2.6x on identical subject financials, and the trading comps span 3.0x across
four peers. Its honest output is the divergence and its causes, not a price.

An initiation report is expected to end in a rating and a target price. This one asks
what can be established when the usual machinery has already disqualified itself.

## What was built

| Module | What it does |
|---|---|
| `scenarios.py` | Bull/Base/Bear as **time-varying driver schedules**, not flat ±X% tilts. A patent cliff is a dated event; a flat driver can only say "permanently worse". |
| `segment_bridge.py` | Growth is stated per **segment**; the consolidated driver is derived from those paths with weights recomputed each year. Mix shift falls out rather than being assumed. |
| `shares.py` | Diluted weighted-average share count from XBRL. Not available upstream — Trellis's schema has no share count and ValuationLab uses the provider's basic figure. |
| `market_implied.py` | Backs the one fit leg out of market capitalisation to find what the market implicitly pays for the rest, with a solved **flip point** for where the conclusion reverses. |
| `scenario_valuation.py` | Bridges scenario forecasts to the DCF and **decomposes the spread** into explicit-period and terminal-value channels. |
| `dispersion.py` | Scale-free dispersion statistics and a leave-one-out, because the measure used upstream cannot test the claim made with it. |
| `claims.py` | Every material claim tiered Demonstrated / Inferred / Assumed / Unsupported with its source, and a gate that stops an unsupported claim entering the thesis. |
| `recommendation.py` | Issues a rating only when stated gates pass; otherwise **NO CALL**, naming the gate. |

110+ tests. Every module was mutation-tested — deliberately broken to confirm the tests
catch it. Two mutations survived on the first pass and are documented where they sit.

## Findings

**1. The market implicitly prices Innovative Medicine near 9.0x revenue.** MedTech is the
only structurally fit leg (peer spread 1.5x against a 2.0x bar). Subtracting its EV range
from J&J's enterprise value leaves 8.4x–9.3x revenue for Innovative Medicine, against a
pharma peer range of 3.4x–8.6x. Above the peer **median** at every mark; above every
**peer** unless MedTech is worth more than 4.48x — the 84th percentile of its own peer
range. The conclusion is stated with that boundary, not without it.

**2. Wide pharma dispersion is one company.** Eli Lilly trades at 16.1x revenue. Adding
Amgen at 6.6x *tightens* the set. So the peer group is one company away from usable, and
the honest claim names it rather than asserting sector-wide heterogeneity.

**3. The evidence offered upstream for that heterogeneity cannot support it.**
ValuationLab argues dispersion is structural because adding peers widened the min/max
spread. That statistic is **monotonic in sample size** — it widens whatever you add,
including draws from a single distribution. Simulated from one tight lognormal, mean
spread runs 1.7x at four peers, 1.9x at six, 2.2x at ten. The claim is registered
UNSUPPORTED and the thesis does not use it. A narrower version is supported and is used.

**4. The 2.0x disqualification bar is not scale-free.** At four peers with the observed
dispersion, pure sampling exceeds it 68% of the time. The fitness verdicts still stand —
both legs use four peers, so the monotonicity cancels — but the threshold should not be
quoted as a clean test.

**5. Two silent data defects were found and fixed upstream.** J&J's fiscal years end on
the Sunday nearest 31 December, so FY2020–FY2022 closed in early January; keying the
table by calendar year filed each one year late and collided FY2022 with FY2023, dropping
an entire fiscal year across every line item with nothing failing. Separately, SEC's
`companyconcept` endpoint returns HTTP 200 with zero facts for tags that
`companyfacts` populates, reducing one peer to a single usable field per year. Both fixed
in Trellis with tests. J&J's derived revenue CAGR moved 3.34% → **4.58%**.

## Recommendation

**NO CALL.** Two of four gates fail. `anchor`: the SOTP's MedTech leg is structurally
fit, but it reaches 36% of revenue against an 80% bar — anchoring a rating on it would
price the other 64% by assumption and report the result as though it had been valued.
`robustness`: the peer-max comparison flips inside MedTech's own peer range. A rating
issued here would restate the uncertainty with a number written over it.

That is the result, not a gap. The thesis rests at the level of its weakest link —
**inferred** — and the report says so.

## Running it

```bash
pip install -e .
python -m pytest tests -q

export TRELLIS_USER_AGENT="you@example.com"
export VALUATIONLAB_PATH=/path/to/valuationlab

python scripts/run_report.py          # the full report
python scripts/run_implied.py         # market-implied multiple and flip point
python scripts/check_dispersion.py --live
python scripts/run_scenarios.py --checklist   # what is still unsourced
```

## What is not here

Seven scenario magnitudes — the LOE calendar, MedTech's growth path, the talc settlement
schedule, the R&D step-up. They need filing facts, and the scenario engine refuses to run
on placeholders rather than producing a target price that looks finished. The industry
and competitive positioning sections are qualitative and unwritten.

Peer multiples in `run_implied.py` are **copied** from ValuationLab's printed output
rather than imported, because that repo exposes its sum-of-the-parts as stdout. They go
stale silently if its snapshots refresh; the script says so in its own output. The fix is
a return value in ValuationLab.
