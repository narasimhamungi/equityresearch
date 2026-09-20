# Johnson & Johnson — Initiation of Coverage

**Rating: NO CALL** · Price $267.20 · Diluted shares 2,429,400,000 · Market cap $649.1bn
Inputs as of 2026-09-17. Every figure below is reproducible; commands are in the README.

---

## 1. The problem

An initiation report is expected to end in a rating and a target price. This one does
not, and the reason is the finding.

[ValuationLab](https://github.com/narasimhamungi/valuationlab) applies three valuation
methods to J&J and disqualifies all three on measured thresholds. The DCF's terminal
value is **82% of enterprise value**, so the conclusion restates the WACC and terminal
growth assumptions rather than reading the forecast. The precedent transactions spread
**2.6x** on identical subject financials — Actelion at 12.3x EV/Revenue against
Celgene at 4.8x — so the answer is a function of which deal you pick. The trading comps
span **3.0x** across four peers, and a median across companies that disagree by more
than 2x is an average of businesses in different situations.

Only one thing survives its own fitness test: the **MedTech leg of the
sum-of-the-parts**, whose peer multiples span 1.5x against a 2.0x bar.

So the question this report asks is not "what is J&J worth". It is: given one defensible
number, **what is the market already paying for everything else?**

---

## 2. Industry and competitive position

### 2.1 The company is now two businesses, and they are not converging

J&J completed its separation from consumer health in 2023 and is a pure-play healthcare
company: **Innovative Medicine $60.4bn** (64% of revenue) and **MedTech $33.8bn** (36%).
They face entirely different forces — a patent cliff is an Innovative Medicine event, a
technology displacement is a MedTech event — which is why this report forecasts them
separately and derives the consolidated rate rather than setting it.

### 2.2 Innovative Medicine: the cliff arrived and was absorbed

The most common framing of J&J — a company facing a patent cliff — is a year out of date.
Stelara lost US exclusivity in 2025, sales fell **41.3% to $6.08bn**, and it cost the
segment roughly **10.4 percentage points** of operational growth. Innovative Medicine
still grew **5.3% to $60.4bn**, its first year above $60bn, with thirteen brands growing
double digits. **Excluding Stelara, the segment grew about 16%.**

That absorption is genuinely impressive and it is the strongest fact in J&J's favour.

The replacement portfolio is concentrated in two franchises:

**Oncology — the anchor, and the concentration.** Darzalex is J&J's largest product at
**$14.35bn, +23.0%**, with the subcutaneous Faspro formulation carrying more than 80%.
Around it sit Carvykti (BCMA cell therapy), Tecvayli and Talvey (bispecifics), giving J&J
a defensible claim to leadership in multiple myeloma. The concentration is the risk: one
product is roughly a quarter of segment revenue and faces a dated 2029 constraint
(§5).

**Immunology — being rebuilt against a larger competitor.** Tremfya grew **40.5% to
$5.2bn** and is protected to 2031. But Tremfya versus AbbVie's Skyrizi is the defining
IL-23 rivalry, and Skyrizi and Rinvoq together are widely expected to exceed Humira's
peak. J&J is taking share in a market a larger competitor is also expanding into.
Icotrokinra, the first targeted oral peptide for plaque psoriasis, launched in 2026 and
is framed as a $5bn-plus opportunity — **by management and sell-side, not by any
disclosure**, and it is not carried as a separate line in any scenario here.

### 2.3 MedTech: the incumbent is losing the growth vector

**This is the most important competitive finding in the report, and it cuts against the
one leg the valuation rests on.**

J&J built the electrophysiology market. Biosense Webster dominates EP mapping, more than
half of *competitors'* procedures use J&J's Carto system, and the franchise is around
$5bn — J&J's MedTech chairman calls it sector leading. Electrophysiology is a named
driver of FY2025 MedTech growth.

Pulsed field ablation is displacing the ablation techniques that franchise was built on,
and J&J is a marginal player in it:

| PFA spend share | 2023 | 2024 | early 2026 |
|---|---|---|---|
| Boston Scientific | 100% | ~83% | **41%** |
| Medtronic | — | entered Jan 2024 | **48%** |
| J&J (Varipulse, Dec 2024) + Abbott (Volt, Jan 2026) + others | — | — | **~11%** |

Catheter unit volumes grew about 20% in 2025. So the market is expanding fast and J&J is
holding roughly a tenth of the new modality while leading the old one.

Two things work in J&J's favour and neither is a disclosure. Mapping integration is a
real structural advantage — Varipulse runs on Carto, which hospitals already own.
Management commits to one meaningful catheter addition a year for three to five years
(Varipulse Pro, then Omnypulse, then Isopulse) and has stopped ruling out acquisitions
in the space.

**Why this matters more than it looks:** MedTech is the only structurally fit valuation
leg in this report. The entire market-implied analysis in §4 subtracts MedTech's
enterprise value from J&J's. If electrophysiology deteriorates, the anchor moves — and
the direction of that move makes Innovative Medicine look *more* expensive, not less.

### 2.4 Competitive summary

| | Position | Direction |
|---|---|---|
| Multiple myeloma | Leader (Darzalex, Carvykti, Tecvayli, Talvey) | Defensible to 2029 |
| IL-23 immunology | Challenger to AbbVie | Growing share, smaller franchise |
| EP mapping | Dominant | Stable, structural |
| **PFA ablation** | **~11% with Abbott and others** | **Losing the growth vector** |
| Orthopaedics, surgery, vision | Scale incumbent | Steady, unremarkable |

---

## 3. Financial position and forecast

### 3.1 The base

Trellis derives J&J's drivers from FY2021–FY2025 with no sourced overrides and no
fallback assumptions — an unusually clean starting point. **Revenue CAGR 4.58%, gross
margin 69.06%.**

Both figures are corrected. The historical table originally read 3.34% because J&J's
fiscal years end on the Sunday nearest 31 December: FY2020–FY2022 closed in early
January, were filed a year late by calendar-year keying, and FY2023 collided with FY2022
and was dropped across every line item. Nothing failed — the remaining years were
internally consistent. Fixed upstream in Trellis (`1b61d95`).

### 3.2 Scenarios

Bull, Base and Bear are **time-varying driver schedules**, not ±X% tilts, because the
events that matter are dated. Growth is stated per segment and the consolidated rate is
derived, with weights recomputed each year.

| | FY26 | FY27 | FY28 | FY29 | FY30 | 5y CAGR |
|---|---|---|---|---|---|---|
| Bear | −0.2% | +1.7% | +2.7% | −0.7% | +0.6% | **+0.80%** |
| Base | +4.6% | +4.6% | +4.6% | +4.6% | +4.6% | **+4.58%** |
| Bull | +3.5% | +5.0% | +5.6% | +5.6% | +4.8% | **+4.91%** |

FY2030 EPS: **$9.89 / $12.08 / $12.27** (diluted, on a modelled declining share count).

### 3.3 The uncomfortable result

**Bull is 33bp of revenue and 19 cents of EPS above Base.**

That is not a weak assumption. It is what happens when you stop crediting J&J with growth
it has to buy. FY2025 MedTech grew 5.4% reported, of which **1.1pp came from Shockwave**.
Trellis grows revenue at the driver rate without charging for the acquisition, while its
capital-return policy sweeps every spare dollar into buybacks — so running MedTech at the
reported rate books acquired growth *and* returns the cash that bought it. Setting
MedTech to organic removes the double-count, and the upside collapses toward the base.

Note the Base carries the same double-count: its 4.58% derives from history that includes
acquired growth. **Read Base as an upper bound on what organic performance supports.**

Against this, management targets double-digit company-wide growth by the end of the
decade — roughly double the Bull case. The gap is stated rather than resolved. Either
these organic paths are far too conservative, or the target depends on acquisitions and
pipeline outcomes no filed number yet supports.

---

## 4. Valuation

### 4.1 What the market implicitly pays for Innovative Medicine

Enterprise value is market cap plus net debt: **$649.1bn + $19.7bn = $668.9bn**.
Subtract MedTech's enterprise value — the one fit leg — and the remainder is what the
market implicitly assigns to Innovative Medicine:

| MedTech marked at | Implied IM EV | Implied multiple | vs pharma peers 3.4x–8.6x |
|---|---|---|---|
| low (3.10x) | $564bn | **9.3x** | above every peer |
| median (3.79x) | $541bn | **9.0x** | above every peer |
| high (4.73x) | $509bn | **8.4x** | above median, within range |

**Robustness, stated rather than buried.** "Above every pharma peer" is *not* robust: it
flips when MedTech is marked above **4.48x — the 84th percentile of its own peer range**.
What holds at every mark is **above the pharma peer median (4.7x)**, roughly twice it.

### 4.2 What this is not

Innovative Medicine's peer set is disqualified from valuing the segment, and nothing here
repairs that. This does **not** say Innovative Medicine is worth some other number and
the market is wrong by the difference — that claim needs the peer median this project
has already rejected. It locates the market's implied multiple within the distribution of
what comparable companies trade at. A location, not a valuation.

### 4.3 The peer set is one company away from usable

ValuationLab's disqualification of the pharma peer set is correct but its stated *reason*
was not supportable, and this report corrected it upstream rather than repeating it.

The original argument: dispersion is economic rather than small-sample noise, evidenced by
the min/max spread widening from 2.5x to 4.7x when Lilly and Amgen were added. **A min/max
spread is monotonic in sample size** — the minimum can only fall and the maximum can only
rise — so it widens whatever you add. Simulated from a single tight lognormal with no
change in the underlying distribution: mean spread 1.7x at four peers, 1.9x at six, 2.2x
at ten. The observation was consistent with the claim and with its opposite.

Re-measured on scale-free statistics, the result is inconclusive and rests on one company:

| | 4 peers | 6 peers |
|---|---|---|
| min/max spread | 2.54x | 4.77x |
| coefficient of variation | 0.460 | **0.641 ↑** |
| IQR / median | 0.674 | **0.629 ↓** |

Two scale-free measures disagreeing is the signature of one extreme observation.
Leave-one-out confirms it: **Lilly alone raises CV to 0.701; Amgen alone lowers it to
0.394.** So the supported claim is narrower and names the company — **Eli Lilly trades at
16.1x revenue against 3.4x–8.6x for Pfizer, Merck, AbbVie and Bristol-Myers.**

A second-order consequence: **the 2.0x disqualification bar is not scale-free either.** At
four peers with the observed dispersion, pure sampling exceeds it about 68% of the time.
The fitness verdicts stand — both peer sets have four members, so the monotonicity
cancels — but the threshold should not be quoted as a clean test in isolation.

### 4.4 What J&J pays for growth

[DealLab](https://github.com/narasimhamungi/deallab) models the closed J&J/Abiomed
transaction on disclosed terms. After crediting every identified synergy at present
value, **$7.4bn of the price — 41.3% — is unaccounted for**. That is the amount paid for
benefits nobody has articulated: option value, strategic positioning, or overpayment.
All three look identical in a model.

Read alongside §3.3, the picture is coherent: organic upside 33bp above trend, and the
growth above that acquired at a 41% unexplained premium on the one deal measured in
detail.

---

## 5. Catalysts and risks

Full dated register with sources in `catalysts.py`; printed with staleness checks on
every run. The four that matter:

**Darzalex 2029 — binary, and the Bull case's weak point.** Two separate constraints
arrive together. The IRA question is genuinely unresolved: CMS signalled a rethink that
would collapse Faspro's protection from 2034 to 2029, while the ORPHAN Cures Act
provisions in the OBBBA expanded the orphan exclusion to serial orphans, which on one
reading removes Darzalex from eligibility entirely. **But the main US patents are
separately reported as expiring in 2029 regardless.** So a favourable IRA outcome does not
clear the risk, and the Bull FY2029–FY2030 path should be read as the optimistic end of a
range whose downside is better documented than its upside. **Do not average the branches
— the midpoint corresponds to no state of the world.**

**PFA share erosion — the threat to the anchor.** §2.3. J&J holds roughly a tenth of PFA
spend while leading the market being displaced, and MedTech is the only fit valuation leg.

**Talc, $5.5bn — outside the numbers.** First payment capped at $3bn in 2027, balance
2028, conditional on at least 95% claimant participation (8-K, 27 July 2026). Trellis has
no one-off-cash-outflow driver, so this sits outside every scenario. Deduct by hand or
carry as unpriced risk; **do not read these cases as having absorbed it.** If the
participation condition fails, the litigation reverts to open-ended exposure that nothing
here prices.

**2026 compression.** Medicare negotiated prices take effect for Stelara, Xarelto and
Imbruvica; Uptravi expires with roughly $1bn exposed; Opsumit's composition patent
expires. All in one year, all dated, all carried in every scenario because they are facts
rather than assumptions.

---

## 6. Investment thesis

**J&J is priced as a company that will keep compounding, and the evidence says its
organic engine is closer to flat than the price implies.**

Three things, each measured:

1. **The market implicitly pays about 9.0x revenue for Innovative Medicine** — above the
   pharma peer median at every mark of MedTech's range, above every pharma peer unless
   MedTech deserves a near-top-of-set multiple.

2. **Organic upside is 33bp above trend.** Strip the acquisitions the model cannot fund
   and the bull case is 19 cents of FY2030 EPS above the base. Growth above that is
   bought, at a 41% unexplained premium on the one deal measured in detail.

3. **The anchor is under competitive pressure.** MedTech is the only fit valuation leg,
   electrophysiology is a named driver of its growth, and J&J holds roughly a tenth of
   the technology displacing it.

The direction is expensive rather than cheap — the opposite of the thesis this report set
out to test.

**What would make this wrong:** the Darzalex IRA branch going J&J's way *and* the patent
position proving more durable than reported; Icotrokinra delivering at the scale
management frames; J&J's PFA roadmap or an acquisition recovering share; or the market
genuinely pricing J&J as a single entity, in which case the sum-of-the-parts inference in
§4.1 does not describe how it is being valued at all.

---

## 7. Recommendation

**NO CALL.** Four gates, two fail.

| Gate | Result |
|---|---|
| `anchor` | **FAIL** — the SOTP MedTech leg is structurally fit but reaches 36% of revenue against an 80% bar |
| `evidence` | pass — no unsupported claim in the thesis chain |
| `robustness` | **FAIL** — the peer-max comparison flips inside MedTech's own peer range |
| `solvency` | pass |

A failing gate does not soften a rating — it removes it. HOLD is a real view that price
is near value; using it to mean "could not tell" makes the two indistinguishable.

**What would close the anchor gate:** a defensible valuation for Innovative Medicine,
which needs a pharma peer set that is not one company away from unusable. **What would
close robustness:** a view on whether MedTech deserves a top-of-set multiple — which, on
§2.3, is now harder to argue than when this analysis began.

The thesis rests at the level of its weakest link: **INFERRED**.

---

## 8. What this report does not contain

Stated so a reader is not left to find them:

- **Talc cash.** $5.5bn committed, outside every scenario (§5).
- **Acquisition spend.** The sweep policy has no M&A line, so modelled buybacks run
  **2.3x** J&J's actual $5.95bn FY2025 repurchases. The two EPS paths bracket the answer:
  a fixed share count understates, the swept count overstates. No acquisition rate is
  invented to split the difference.
- **Equity-compensation issuance**, which would slow the share-count decline.
- **A scenario-level DCF.** Terminal value is 82% of EV and Gordon growth reads the final
  year alone, so scenario values would mostly restate a year-five assumption. `decompose()`
  measures this; the report does not present numbers it would produce.
- **Management access, channel checks, primary research.** This is built from filings and
  public data.

**Inherited constraints:** ValuationLab's comps are annual, not LTM. The equity risk
premium is Damodaran's January 2026 print against a September 2026 risk-free rate — an
eight-month mismatch, disclosed upstream and repeated here. Beta is Blume-adjusted from
two retail sources over a window spanning the 2023 Kenvue separation.
