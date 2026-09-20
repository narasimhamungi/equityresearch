"""
Share count over the forecast horizon, when the model is buying stock back.

WHY A FIXED SHARE COUNT IS WRONG HERE
---------------------------------------
Trellis derived `capital_return_policy = "sweep_to_buybacks"` for J&J, because the
historical data shows it repurchasing. Every forecast year therefore sweeps cash above
a floor into buybacks -- and the scenario runner was dividing each year's net income by
the FIXED FY2025 diluted count. Every EPS figure it printed was understated, and
progressively more so: FY2026 barely, FY2030 by the whole cumulative repurchase.

The direction is the same in all three scenarios, so the Bear/Base/Bull COMPARISON
survives. The absolute figures do not, and those are what a reader quotes.

THE ASSUMPTION THIS CANNOT AVOID, AND THE CIRCULARITY IN IT
-------------------------------------------------------------
Converting buyback dollars into shares needs a repurchase price. There is no filed
answer -- it is a forecast of where the stock trades over five years, which is most of
what the report is trying to determine.

The obvious default is today's price, and for this report that default is
self-undermining. The central finding is that the market may be paying above every
pharma peer for Innovative Medicine -- that the stock is expensive. Repurchasing at a
price your own thesis calls too high destroys value per share rather than creating it,
so crediting the Bear case with accretion bought at that price flatters exactly the
scenario that says the price is wrong.

So `repurchase_price` is required rather than defaulted, and `circularity_warning`
states the problem in the output wherever the price used sits at or above the price the
thesis disputes. Sensitivity is one call: run it at a lower price and see how much of
the EPS path was buyback arithmetic rather than operating performance.

THE SWEEP ASSUMES THE COMPANY MAKES NO ACQUISITIONS
-----------------------------------------------------
Trellis's `sweep_to_buybacks` returns every dollar above a cash floor to shareholders.
It has no line for acquisitions, so for a serial acquirer every dollar that would have
bought a company buys stock instead.

For J&J that is not a rounding difference. FY2025 actual buybacks were $6.0bn against
$24.5bn of operating cash flow and $12.4bn of dividends; the sweep forecasts $17.3bn in
the first year and $11-15bn a year after. The company spent roughly $17bn on Abiomed and
$13bn on Shockwave within three years, which is precisely the cash the sweep is handing
back instead.

So the two EPS paths bracket the answer rather than either being it. A fixed share count
understates EPS by ignoring buybacks entirely; the swept count overstates it by
assuming five years of no M&A. `acquisition_blind_warning` compares the modelled pace to
the last actual year and says so, rather than inventing an acquisition rate to split the
difference -- that number would be no better sourced than the one it replaced.

WHAT IS DELIBERATELY NOT MODELLED
-----------------------------------
Share issuance from equity compensation, which partly offsets repurchases at most large
caps and would need a dilution assumption of its own. Ignoring it makes the share count
fall faster than it really would, so the EPS path here is optimistic even before the
price question. Stated rather than silently corrected with an invented offset rate.
"""

from __future__ import annotations

from dataclasses import dataclass


class ShareCountError(ValueError):
    pass


@dataclass(frozen=True)
class SharePoint:
    year: int
    buybacks: float
    shares_retired: float
    shares_end: float


@dataclass(frozen=True)
class SharePath:
    opening_shares: float
    repurchase_price: float
    points: tuple[SharePoint, ...]

    def shares_for(self, year: int) -> float:
        """Weighted-average shares for `year`: the mean of opening and closing, since
        repurchases happen through the year rather than on day one. Using the closing
        count would overstate the reduction and flatter EPS by roughly half a year of
        buybacks in every year of the horizon."""
        prior = self.opening_shares
        for p in self.points:
            if p.year == year:
                return (prior + p.shares_end) / 2.0
            prior = p.shares_end
        raise ShareCountError(f"No share count for FY{year}.")

    @property
    def total_reduction(self) -> float:
        return 1.0 - (self.points[-1].shares_end / self.opening_shares) if self.points \
            else 0.0


def build_share_path(forecast: dict[int, dict[str, float]], opening_shares: float,
                     repurchase_price: float) -> SharePath:
    if opening_shares <= 0:
        raise ShareCountError("Opening share count must be positive.")
    if repurchase_price <= 0:
        raise ShareCountError(
            "A repurchase price is required and must be positive. There is no filed "
            "answer -- it is a forecast of where the stock trades -- so it is stated "
            "explicitly rather than defaulted to today's price behind the reader's back.")

    points: list[SharePoint] = []
    shares = opening_shares
    for year in sorted(forecast):
        buybacks = max(forecast[year].get("buybacks", 0.0), 0.0)
        retired = buybacks / repurchase_price
        if retired >= shares:
            raise ShareCountError(
                f"FY{year}: modelled buybacks of {buybacks:,.0f} at "
                f"{repurchase_price:,.2f} would retire {retired:,.0f} shares against "
                f"{shares:,.0f} outstanding. The forecast or the price is wrong.")
        shares -= retired
        points.append(SharePoint(year=year, buybacks=buybacks, shares_retired=retired,
                                 shares_end=shares))
    return SharePath(opening_shares=opening_shares,
                     repurchase_price=repurchase_price, points=tuple(points))


def circularity_warning(path: SharePath, market_price: float,
                        thesis_says_expensive: bool) -> str:
    """The self-undermining case, stated where it applies.

    Returns an empty string when there is nothing to flag, so a caller can print it
    unconditionally.
    """
    if not thesis_says_expensive:
        return ""
    if path.repurchase_price < market_price:
        return ""
    return (
        f"  CIRCULARITY: shares are repurchased at {path.repurchase_price:,.2f}, at or "
        f"above the market price of {market_price:,.2f} that this report argues may be "
        f"too high. If the thesis is right, these buybacks destroy value per share "
        f"rather than creating it, and the EPS path below is flattered by exactly the "
        f"assumption the thesis disputes. Re-run at a lower price to see how much of "
        f"the path is buyback arithmetic rather than operating performance.")


def acquisition_blind_warning(path: SharePath, last_actual_buybacks: float,
                              tolerance: float = 1.5) -> str:
    """Flag a modelled buyback pace materially above what the company actually does.

    `tolerance` is the multiple of the last actual year beyond which the gap stops being
    noise. Returns an empty string when there is nothing to say, so a caller can print
    it unconditionally.
    """
    if last_actual_buybacks <= 0 or not path.points:
        return ""
    ongoing = [p.buybacks for p in path.points[1:]] or [path.points[0].buybacks]
    pace = sum(ongoing) / len(ongoing)
    if pace <= last_actual_buybacks * tolerance:
        return ""
    return (
        f"  ACQUISITION-BLIND: the model repurchases {pace:,.0f} a year on average "
        f"against {last_actual_buybacks:,.0f} actually repurchased in the last reported "
        f"year -- {pace / last_actual_buybacks:.1f}x. The sweep policy has no line for "
        f"acquisitions, so for a serial acquirer every dollar that would buy a company "
        f"buys stock instead. The EPS path below therefore OVERSTATES, while a fixed "
        f"share count UNDERSTATES. The answer is between them, and no acquisition rate "
        f"is invented here to split the difference.")


def render(path: SharePath, scenario_name: str) -> str:
    lines = [f"  {scenario_name} -- share count at {path.repurchase_price:,.2f}/share",
             f"    {'year':<8}{'buybacks':>18}{'retired':>16}{'shares end':>18}"]
    for p in path.points:
        lines.append(f"    FY{p.year:<6}{p.buybacks:>18,.0f}{p.shares_retired:>16,.0f}"
                     f"{p.shares_end:>18,.0f}")
    lines.append(f"    Cumulative reduction {path.total_reduction:.2%}. Equity "
                 f"compensation issuance is NOT modelled, so the real count would fall "
                 f"more slowly and this EPS path is optimistic before the price "
                 f"question is even reached.")
    return "\n".join(lines)
