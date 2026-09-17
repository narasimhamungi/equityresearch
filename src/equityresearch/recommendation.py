"""
The investment recommendation, and the gates it has to clear first.

THE PROBLEM THIS SOLVES
------------------------
An initiation report is expected to end in a rating and a target price. That
expectation is strong enough that the number usually gets produced whether or not the
analysis supports one -- the format demands a figure, so a figure appears, and the
caveats go in a footnote nobody reads against it.

ValuationLab already reached the opposite conclusion on J&J: every valuation method
trips a disqualifying condition, so its derived recommendation is NONE and its stated
output is the divergence and its causes rather than a price. A report built on that
work cannot then print a target price as though the problem had been solved by being
restated at greater length.

So the recommendation is gated. Each gate is a condition that must hold for a rating to
mean anything, checked against the actual analysis rather than asserted. If a gate
fails, the module returns NO CALL and names the gate -- which is itself a finding, and a
more useful one than a number manufactured to fill the slot.

THE GATES
----------
  anchor        At least one valuation method must be structurally fit to anchor a
                conclusion. Without one there is no defensible estimate of value, and a
                rating is a statement about value versus price.

  evidence      The thesis must not rest on an unsupported claim (see `claims.py`).

  robustness    Where the thesis rests on a comparison that could flip across a
                plausible range of inputs, it must not flip -- or the conclusion is
                about which end of the range was chosen.

  solvency      No scenario used in the conclusion may be one the forecast says cannot
                fund itself, unless that insolvency is the point being made.

A rating issued with gates failing is not a bolder call; it is the same uncertainty with
a number written over it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Rating(Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    NO_CALL = "NO CALL"


class RecommendationError(ValueError):
    pass


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    detail: str          # what was measured, either way -- not just why it failed

    def render(self) -> str:
        mark = "ok  " if self.passed else "FAIL"
        return f"  [{mark}] {self.name}: {self.detail}"


@dataclass(frozen=True)
class Recommendation:
    rating: Rating
    gates: tuple[Gate, ...]
    reasoning: str
    target_price: float | None = None

    @property
    def failed(self) -> tuple[Gate, ...]:
        return tuple(g for g in self.gates if not g.passed)

    def __post_init__(self) -> None:
        if self.failed and self.rating is not Rating.NO_CALL:
            raise RecommendationError(
                f"Rating {self.rating.value} issued with {len(self.failed)} gate(s) "
                f"failing: {', '.join(g.name for g in self.failed)}. A rating is a "
                f"statement about value against price; if the gates that make a value "
                f"estimate meaningful have failed, the rating restates the uncertainty "
                f"rather than resolving it.")
        if self.target_price is not None and self.rating is Rating.NO_CALL:
            raise RecommendationError(
                "A target price with NO CALL is the number the reader will quote and "
                "the verdict they will ignore. Omit it.")
        if self.target_price is not None and self.target_price <= 0:
            raise RecommendationError("Target price must be positive.")


#: A fit method must reach at least this share of the subject's revenue before it can
#: anchor a rating on the whole company.
MIN_COVERAGE = 0.80


def gate_anchor(fit_methods: tuple[str, ...], all_methods: tuple[str, ...],
                coverage: float = 1.0) -> Gate:
    """Fitness is necessary but not sufficient: the fit method must also cover enough of
    the business.

    Written first as fitness alone, which produced a contradiction inside this report --
    the market-implied analysis rests on MedTech being a structurally fit leg while the
    recommendation said no method was fit at all. Both readings were defensible and they
    disagreed, which means the gate was asking the wrong question. What actually blocks a
    rating on J&J is not that nothing is fit; it is that the only thing fit covers 36% of
    revenue, and a rating is a claim about the whole company.
    """
    if not fit_methods:
        return Gate("anchor", False,
                    f"none of {len(all_methods)} methods is fit to anchor "
                    f"({', '.join(all_methods)}) -- there is no defensible estimate of "
                    f"value to compare the price against")
    if coverage < MIN_COVERAGE:
        return Gate("anchor", False,
                    f"{', '.join(fit_methods)} is structurally fit but reaches only "
                    f"{coverage:.0%} of revenue, against an {MIN_COVERAGE:.0%} bar. A "
                    f"rating is a claim about the whole company; anchoring one on this "
                    f"would price {1 - coverage:.0%} of the business by assumption and "
                    f"report the result as though it had been valued")
    return Gate("anchor", True,
                f"{len(fit_methods)} of {len(all_methods)} methods fit to anchor "
                f"({', '.join(fit_methods)}), covering {coverage:.0%} of revenue")


def gate_evidence(unsupported_claim_ids: tuple[str, ...]) -> Gate:
    if not unsupported_claim_ids:
        return Gate("evidence", True, "no unsupported claim in the thesis chain")
    return Gate("evidence", False,
                f"thesis rests on unsupported claim(s): "
                f"{', '.join(unsupported_claim_ids)}")


def gate_robustness(claim: str, holds_across_range: bool, detail: str) -> Gate:
    return Gate("robustness", holds_across_range,
                f"{claim} -- {detail}" if not holds_across_range
                else f"{claim} holds across the range ({detail})")


def gate_solvency(insolvent_scenarios: tuple[str, ...],
                  intentional: bool = False) -> Gate:
    if not insolvent_scenarios:
        return Gate("solvency", True, "no scenario used here fails to fund itself")
    if intentional:
        return Gate("solvency", True,
                    f"{', '.join(insolvent_scenarios)} cannot fund itself, and that is "
                    f"the finding being reported rather than an input being relied on")
    return Gate("solvency", False,
                f"{', '.join(insolvent_scenarios)} cannot fund itself, and the "
                f"conclusion relies on it")


def derive(gates: tuple[Gate, ...], proposed: Rating, reasoning: str,
           target_price: float | None = None) -> Recommendation:
    """Issue `proposed` if every gate passes; otherwise NO CALL with the failures.

    The rating is never softened -- a failing gate does not turn a BUY into a HOLD, it
    turns it into no call at all. A HOLD is a real view that price is near value, and
    using it as a way to say "we could not tell" makes the two indistinguishable in a
    reader's hands.
    """
    if not gates:
        raise RecommendationError(
            "No gates evaluated. An ungated recommendation is an opinion with a "
            "rating attached.")
    failed = [g for g in gates if not g.passed]
    if failed:
        return Recommendation(
            rating=Rating.NO_CALL, gates=gates, target_price=None,
            reasoning=(
                f"No rating. {len(failed)} of {len(gates)} gates fail: "
                f"{', '.join(g.name for g in failed)}. "
                f"The honest output is what the analysis does establish -- see the "
                f"findings above -- not a rating that would imply the gaps were "
                f"resolved. Closing any one of these gates is a specific, stateable "
                f"piece of work rather than a matter of judgement."))
    return Recommendation(rating=proposed, gates=gates, reasoning=reasoning,
                          target_price=target_price)


def render(rec: Recommendation) -> str:
    out = ["RECOMMENDATION", "=" * 14, "", f"  {rec.rating.value}"]
    if rec.target_price is not None:
        out.append(f"  Target price {rec.target_price:,.2f}")
    out += ["", "  Gates", ""]
    out += [g.render() for g in rec.gates]
    out += ["", "  " + rec.reasoning]
    return "\n".join(out)
