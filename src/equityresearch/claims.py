"""
Every material claim in the report, with its evidence tier and its source.

WHY A REGISTER RATHER THAN PROSE
---------------------------------
An initiation report is a document in which a reader cannot tell, from the writing
alone, which sentences are measurements and which are the analyst's opinion. Both are
written in the same confident register, and the second kind is usually the one that
moves the recommendation. The convention that hedged language signals uncertainty does
not survive contact with a report that wants to sound decisive.

So claims are registered as data before they are rendered as prose, each carrying the
tier of evidence behind it and the specific source that establishes it. The rendering
then cannot detach a claim from its tier, because the tier is printed with it.

THE FOUR TIERS
---------------
    DEMONSTRATED  Computed by this portfolio's own code from filed data, reproducible by
                  re-running it. "J&J's FY2021-FY2025 revenue CAGR is 4.58%" is
                  demonstrated: Trellis derives it from SEC XBRL and the run prints it.

    INFERRED      Follows by argument from demonstrated facts, but is not itself a
                  measurement. "The market implicitly prices Innovative Medicine near
                  9.0x revenue" is inferred -- the market cap and the MedTech EV are
                  measured, the subtraction is arithmetic, but treating the remainder AS
                  the market's view of that segment is an inference about how the market
                  is thinking.

    ASSUMED       A necessary input nobody has established. Every scenario magnitude
                  lands here until it is sourced. Assumed claims are legitimate and the
                  report needs them; what is not legitimate is letting one pass as
                  measured.

    UNSUPPORTED   Stated somewhere and not established anywhere -- including claims
                  inherited from this portfolio's own upstream repos. These exist to be
                  FLAGGED, not used. `gate_thesis` refuses to let one through.

THE POINT OF THE UNSUPPORTED TIER
----------------------------------
It is not decoration. This project has already found one: ValuationLab's README argues
pharma dispersion is structural rather than a small-sample artefact, evidenced by
adding two peers and watching the min/max spread widen. `dispersion.py` shows that
evidence cannot support the claim -- min/max is monotonic in sample size, so it widens
whatever you add -- and the leave-one-out shows the result rests entirely on Eli Lilly.
The claim is not false; it is unestablished by what was offered for it, and a narrower
version IS supported. Registering it as UNSUPPORTED is what stops this report citing
its own upstream work uncritically, which is the easiest mistake available here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(Enum):
    DEMONSTRATED = "demonstrated"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    UNSUPPORTED = "unsupported"

    @property
    def rank(self) -> int:
        return {"demonstrated": 3, "inferred": 2, "assumed": 1, "unsupported": 0}[
            self.value]


class ClaimError(ValueError):
    """Raised when the register is malformed or a gate is breached. Fatal by design:
    every failure here produces a report that reads as though it were sound."""


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    tier: Tier
    source: str              # what establishes it, or -- for UNSUPPORTED -- what does not
    reproduce: str = ""      # the command that regenerates it, for DEMONSTRATED claims

    def __post_init__(self) -> None:
        if not self.id or not self.text.strip():
            raise ClaimError("A claim needs an id and text.")
        if not self.source.strip():
            raise ClaimError(
                f"{self.id}: no source. A claim without a stated source is an "
                f"assertion, and the tier would be a label with nothing behind it.")
        if self.tier is Tier.DEMONSTRATED and not self.reproduce.strip():
            raise ClaimError(
                f"{self.id}: tier is DEMONSTRATED but no reproduction command is given. "
                f"'Demonstrated' means a reader can re-run it; without the command that "
                f"is a promise rather than a demonstration.")

    def render(self) -> str:
        head = f"  [{self.tier.value.upper():<12}] {self.text}"
        lines = [head, f"                 source: {self.source}"]
        if self.reproduce:
            lines.append(f"                 reproduce: {self.reproduce}")
        return "\n".join(lines)


@dataclass
class Register:
    claims: list[Claim] = field(default_factory=list)

    def add(self, claim: Claim) -> None:
        if any(c.id == claim.id for c in self.claims):
            raise ClaimError(f"Duplicate claim id {claim.id!r}.")
        self.claims.append(claim)

    def get(self, claim_id: str) -> Claim:
        for c in self.claims:
            if c.id == claim_id:
                return c
        raise ClaimError(f"No claim {claim_id!r} in the register.")

    def by_tier(self, tier: Tier) -> tuple[Claim, ...]:
        return tuple(c for c in self.claims if c.tier is tier)

    def weakest(self, claim_ids: tuple[str, ...]) -> Tier:
        """An argument is only as good as its weakest link, so a conclusion resting on
        several claims inherits the lowest tier among them rather than an average."""
        if not claim_ids:
            raise ClaimError("No claims given; there is no argument to rank.")
        return min((self.get(i).tier for i in claim_ids), key=lambda t: t.rank)


def gate_thesis(register: Register, claim_ids: tuple[str, ...]) -> None:
    """Refuse to build a thesis on an unsupported claim.

    Assumed claims pass -- a forward-looking report cannot be written without them, and
    the register prints them as assumed wherever they appear. Unsupported claims do not
    pass, because 'unsupported' means the thing offered as evidence does not establish
    the claim, and building on it would launder that into the conclusion.
    """
    bad = [i for i in claim_ids if register.get(i).tier is Tier.UNSUPPORTED]
    if bad:
        detail = "\n".join(f"    {i}: {register.get(i).text}\n"
                           f"      what fails: {register.get(i).source}" for i in bad)
        raise ClaimError(
            f"The thesis rests on {len(bad)} unsupported claim(s). Establish them, "
            f"restate them narrowly enough to be supported, or drop them -- do not "
            f"build on them:\n{detail}")


def render(register: Register, title: str = "CLAIM REGISTER") -> str:
    out = [title, "=" * len(title), ""]
    counts = {t: len(register.by_tier(t)) for t in Tier}
    out.append("  " + "   ".join(f"{t.value}: {n}" for t, n in counts.items()))
    for tier in (Tier.DEMONSTRATED, Tier.INFERRED, Tier.ASSUMED, Tier.UNSUPPORTED):
        claims = register.by_tier(tier)
        if not claims:
            continue
        out += ["", f"  -- {tier.value.upper()} " + "-" * (58 - len(tier.value))]
        for c in claims:
            out.append(c.render())
    if register.by_tier(Tier.UNSUPPORTED):
        out += ["", "  Unsupported claims are listed so a reader can see what this "
                    "report declines to",
                "  rely on. They are not used in the thesis; `gate_thesis` enforces "
                "that."]
    return "\n".join(out)
