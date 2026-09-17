"""
Scenario forecasts -> per-share values, and where the spread between them comes from.

THE UNCOMFORTABLE FINDING THIS MODULE IS BUILT TO EXPOSE
---------------------------------------------------------
`scenarios.py` exists because a patent cliff is a DATED event: erosion lands hard in
one year, troughs in the next, and the business re-bases. That argument is correct about
the business and it is the reason the driver schedule varies year by year instead of
tilting a flat rate.

It may be almost irrelevant to the DCF, and this module measures whether it is.

ValuationLab disqualified J&J's DCF because terminal value is 82% of enterprise value.
Gordon growth computes that terminal value from the FINAL explicit year's free cash flow
alone. So a scenario's effect on the DCF arrives through two channels of very unequal
size: the discounted five-year cash flows, which carry roughly 18% of the value, and the
terminal value, which carries the rest and sees only year five. Two scenarios with
completely different paths through years one to four but the same year-five cash flow
will produce nearly the same DCF.

That has a sharp consequence for how the report may present its cases. If the Bull-Bear
per-share spread turns out to be overwhelmingly a terminal-value effect, then the three
"scenarios" are three year-five assumptions wearing five years of detail, and presenting
the dated path as though it drove the valuation would be a misrepresentation of where
the number actually comes from. The path would still be the right way to think about the
BUSINESS -- and the right input to anything reading cumulative cash, leverage or the
dividend -- but not the thing the DCF responds to.

So this does not report three target prices. It reports three values and the
decomposition that says how much of their difference is the forecast doing work versus
one assumption being restated with a long preamble.

INHERITED DISQUALIFICATION
---------------------------
ValuationLab disqualifies a DCF whose terminal value exceeds 75% of EV, on the grounds
that the conclusion restates the WACC and terminal growth assumptions rather than
reading the forecast. Running the same DCF three times does not repair that -- if
anything it compounds it, since every scenario inherits the same terminal dominance. A
per-share number produced here is therefore never labelled a target price, and
`disqualified` is carried on every result so a caller cannot use one without seeing it.

PER-SHARE IS RECOMPUTED ON DILUTED SHARES
------------------------------------------
`DCFResult.implied_share_price` divides by `market.shares_outstanding`, which is the
provider's BASIC count (see ValuationLab's `marketdata`). Every per-share figure here is
recomputed from equity value on the diluted weighted-average count from `shares.py`, and
both are reported so the difference is visible rather than silently applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

#: ValuationLab's bar: above this share of EV, the DCF is disqualified from anchoring.
TERMINAL_DOMINANCE_THRESHOLD = 0.75

#: If this share or more of a scenario's EV difference from Base comes through terminal
#: value, the explicit five-year path is not what is moving the answer.
TERMINAL_CHANNEL_THRESHOLD = 0.80


class DCFLike(Protocol):
    pv_explicit_fcf: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    implied_share_price: float


class ScenarioValuationError(ValueError):
    pass


@dataclass(frozen=True)
class ScenarioValue:
    name: str
    pv_explicit: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    per_share_diluted: float
    per_share_basic: float
    insolvent_years: tuple[int, ...]

    @property
    def terminal_share(self) -> float:
        return self.pv_terminal / self.enterprise_value

    @property
    def disqualified(self) -> bool:
        """Carried on every result so a caller cannot quote a per-share figure without
        the verdict attached."""
        return self.terminal_share > TERMINAL_DOMINANCE_THRESHOLD


@dataclass(frozen=True)
class SpreadDecomposition:
    """Where one scenario's difference from Base actually comes from."""
    scenario: str
    ev_delta: float
    explicit_delta: float
    terminal_delta: float

    @property
    def terminal_channel_share(self) -> float:
        """Fraction of the EV difference arriving through terminal value. Can exceed 1
        or go negative when the two channels pull in opposite directions -- which is
        itself worth seeing, since it means the explicit period is offsetting rather
        than reinforcing the terminal effect."""
        if self.ev_delta == 0:
            return float("nan")
        return self.terminal_delta / self.ev_delta

    @property
    def path_is_decorative(self) -> bool:
        """True when the dated five-year path is not what moves the valuation."""
        share = self.terminal_channel_share
        return share == share and abs(share) >= TERMINAL_CHANNEL_THRESHOLD


def value_scenario(name: str, dcf: DCFLike, diluted_shares: float,
                   basic_shares: float, insolvent_years: tuple[int, ...] = ()
                   ) -> ScenarioValue:
    if diluted_shares <= 0 or basic_shares <= 0:
        raise ScenarioValuationError("Share counts must be positive.")
    if dcf.enterprise_value <= 0:
        raise ScenarioValuationError(
            f"{name}: enterprise value {dcf.enterprise_value:,.0f} is not positive. A "
            f"per-share figure from this would be meaningless, not merely low.")
    return ScenarioValue(
        name=name, pv_explicit=dcf.pv_explicit_fcf, pv_terminal=dcf.pv_terminal_value,
        enterprise_value=dcf.enterprise_value, equity_value=dcf.equity_value,
        per_share_diluted=dcf.equity_value / diluted_shares,
        per_share_basic=dcf.equity_value / basic_shares,
        insolvent_years=insolvent_years)


def decompose(base: ScenarioValue, other: ScenarioValue) -> SpreadDecomposition:
    """Split a scenario's EV difference from Base into its explicit and terminal parts.

    The two deltas sum to the EV delta by construction -- enterprise value is exactly
    pv_explicit + pv_terminal -- so this is an identity, not an estimate, and any
    rounding in it comes from the DCF itself rather than from this decomposition.
    """
    if base.name == other.name:
        raise ScenarioValuationError("Cannot decompose a scenario against itself.")
    return SpreadDecomposition(
        scenario=other.name,
        ev_delta=other.enterprise_value - base.enterprise_value,
        explicit_delta=other.pv_explicit - base.pv_explicit,
        terminal_delta=other.pv_terminal - base.pv_terminal)


def report(base: ScenarioValue, others: tuple[ScenarioValue, ...]) -> str:
    out = ["SCENARIO VALUES -- not target prices; see the verdict below", ""]
    header = f"  {'scenario':<10}{'EV':>18}{'equity':>18}{'per share':>12}{'terminal':>10}"
    out += [header, "  " + "-" * (len(header) - 2)]
    for v in (base, *others):
        flag = "  DISQUALIFIED" if v.disqualified else ""
        out.append(f"  {v.name:<10}{v.enterprise_value:>18,.0f}"
                   f"{v.equity_value:>18,.0f}{v.per_share_diluted:>12,.2f}"
                   f"{v.terminal_share:>9.0%}{flag}")
        if v.insolvent_years:
            out.append(f"    ! cannot fund itself in {v.insolvent_years} -- an economic "
                       f"finding, and the equity value above does not price it")

    if any(v.disqualified for v in (base, *others)):
        out += ["", f"  Every case above trips ValuationLab's terminal-dominance bar "
                    f"({TERMINAL_DOMINANCE_THRESHOLD:.0%} of EV). Running the same "
                    f"disqualified DCF three times does not repair it -- all three "
                    f"inherit the same dependence on WACC and terminal growth. These "
                    f"are scenario values, and none of them is a target price."]

    out += ["", "  WHERE THE SPREAD COMES FROM", ""]
    decorative = []
    for v in others:
        d = decompose(base, v)
        out.append(f"    {d.scenario:<10} EV vs Base {d.ev_delta:>+18,.0f}  "
                   f"= explicit {d.explicit_delta:>+15,.0f} + terminal "
                   f"{d.terminal_delta:>+18,.0f}   ({d.terminal_channel_share:>6.0%} "
                   f"terminal)")
        if d.path_is_decorative:
            decorative.append(d.scenario)

    if decorative:
        out += ["", f"  {', '.join(decorative)}: the difference from Base arrives almost "
                    f"entirely through terminal value, which Gordon growth computes from "
                    f"the FINAL forecast year alone. The dated year-by-year path is "
                    f"therefore not what moves these numbers -- a scenario with the same "
                    f"year-five cash flow and a completely different route to it would "
                    f"value the same. Present the path as the case for the BUSINESS, and "
                    f"do not present it as the driver of these valuations."]
    else:
        out += ["", "  The explicit forecast period carries a meaningful share of the "
                    "difference between cases, so the year-by-year path is doing real "
                    "work in these numbers rather than decorating a year-five "
                    "assumption."]
    return "\n".join(out)
