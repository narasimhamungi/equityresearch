"""
Scenario engine: Bull / Base / Bear as time-varying driver schedules.

WHY THIS EXISTS, and why it is not `dataclasses.replace`
--------------------------------------------------------
Trellis's `run_forecast` applies a single frozen `Drivers` object to all five
forecast years. Flexing it with `dataclasses.replace` produces a scenario that says
"permanently X% worse than base" -- which is the wrong shape for the only kind of
event this report is actually about. A patent expiry, a biosimilar entry, a litigation
settlement and an acquisition's synergy ramp are all DATED. They land in a specific
year, do most of their damage over two or three, and then the business re-bases. A flat
driver cannot express that; it can only tilt the whole line.

`project_year(prior, drivers)` is public and takes the drivers for THAT year, so the
fix needs no change to Trellis: this module loops it with a different `Drivers` per
forecast year. That is the entire mechanism. Everything else in this file is the
discipline around it.

PER-YEAR FLEXES ARE APPLIED TO BASE, NOT CUMULATIVELY
-----------------------------------------------------
Year N's drivers = base drivers + year N's flexes. Deltas do NOT compound across years.
This is deliberate. Cumulative deltas make a schedule impossible to read: "-150bp in
each of years 1-3" silently means -450bp by year 3, and the analyst who wrote it
usually meant the trough, not the sum. Stating each year's level against the same
fixed base makes the intended path visible in the config itself, which is the only
place a reviewer will look.

FLEXES ARE NOT TRELLIS OVERRIDES
---------------------------------
Trellis has an `overrides` channel on `derive_drivers_from_history`, recorded as
`Drivers.overrides_applied` and documented there as "analyst-sourced, cited values used
in place" of data the structured pull genuinely could not reach. A scenario assumption
is a different claim entirely: it is not a better measurement of a real historical
value, it is a hypothesis about the future. Routing scenario flexes through that
channel would put a forward hypothesis in a field a reader is entitled to read as a
sourced historical fact. They are kept structurally separate for that reason, and the
base drivers a scenario starts from keep their own `overrides_applied` untouched.

EVIDENCE TIER IS TRACKED PER FLEX
----------------------------------
Every flex carries `kind`:
    derived   -- computed from data already in this project's sources (e.g. a
                 consolidated gross-margin effect implied by segment mix and segment
                 margins that are themselves cited to the 10-K). Reproducible.
    sourced   -- an external fact with a citation (a settlement amount, an LOE date,
                 a guided synergy figure).
    judgment  -- an analyst assumption. Legitimate, but it is the weakest tier and the
                 report must not present it as anything else.
A scenario whose downside case is entirely `judgment` is an opinion with arithmetic
attached. The summary surfaces the tier mix so that is visible rather than buried.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from trellis.forecast import Drivers, project_year, reconcile_forecast_year

#: Sentinel for a flex whose magnitude is a placeholder awaiting research. A schedule
#: containing one will not run -- see `validate`. This exists so an unfinished scenario
#: fails loudly at the config, instead of quietly producing a number that looks final.
UNSOURCED = "UNSOURCED"

KINDS = ("derived", "sourced", "judgment")
MODES = ("set", "delta")

#: Only numeric drivers are flexable. The policy strings (`dividend_policy`,
#: `capital_return_policy`) select a MECHANISM, not a magnitude -- switching them
#: between scenarios would mean the three cases are running different models, so the
#: comparison would no longer isolate the assumptions. The provenance tuples
#: (`years_used`, `assumptions`, `overrides_applied`) are records of how the base was
#: built and must survive a scenario unaltered.
_NON_FLEXABLE = frozenset({
    "dividend_policy", "capital_return_policy",
    "years_used", "assumptions", "overrides_applied",
})
FLEXABLE = tuple(
    f.name for f in dataclasses.fields(Drivers) if f.name not in _NON_FLEXABLE
)


@dataclass(frozen=True)
class Flex:
    """One driver moved, in one forecast year, for one stated reason."""
    driver: str
    mode: str      # "set" (absolute level) or "delta" (additive to base)
    value: float
    kind: str      # "derived" | "sourced" | "judgment"
    basis: str     # why this magnitude, and where it came from. Required.

    def apply(self, base_value: float) -> float:
        return self.value if self.mode == "set" else base_value + self.value

    def label(self) -> str:
        op = "=" if self.mode == "set" else ("+" if self.value >= 0 else "")
        return f"{self.driver} {op}{self.value:+.4f}".replace("=+", "= ") \
            if self.mode == "delta" else f"{self.driver} = {self.value:.4f}"


@dataclass(frozen=True)
class ScenarioYear:
    offset: int                 # 1 = first forecast year after base_year
    flexes: tuple[Flex, ...] = ()
    note: str = ""              # what is happening to the business in this year


@dataclass(frozen=True)
class Scenario:
    name: str
    thesis: str                 # the one-sentence economic story this path encodes
    years: tuple[ScenarioYear, ...] = ()

    def year(self, offset: int) -> ScenarioYear | None:
        for y in self.years:
            if y.offset == offset:
                return y
        return None


class ScenarioError(ValueError):
    """Raised when a scenario is malformed or incomplete. Never warned-and-continued:
    a scenario that cannot be validated must not silently produce a valuation."""


def validate(scenario: Scenario, horizon: int) -> None:
    """Reject a scenario that cannot be honestly run. Checks, in order:
    unknown/non-flexable driver names (catches typos, which would otherwise be
    silently ignored by a setattr-free dataclass replace), bad mode/kind, an
    out-of-horizon or duplicated year, a duplicated driver within one year, and any
    remaining UNSOURCED placeholder."""
    if not scenario.name or not scenario.thesis:
        raise ScenarioError("A scenario needs a name and a stated thesis.")

    seen_offsets: set[int] = set()
    missing: list[str] = []
    for y in scenario.years:
        if not (1 <= y.offset <= horizon):
            raise ScenarioError(
                f"{scenario.name}: year offset {y.offset} outside horizon 1..{horizon}."
            )
        if y.offset in seen_offsets:
            raise ScenarioError(f"{scenario.name}: duplicate year offset {y.offset}.")
        seen_offsets.add(y.offset)

        seen_drivers: set[str] = set()
        for f in y.flexes:
            if f.driver not in FLEXABLE:
                raise ScenarioError(
                    f"{scenario.name} y{y.offset}: '{f.driver}' is not a flexable "
                    f"driver. Flexable: {', '.join(FLEXABLE)}."
                )
            if f.driver in seen_drivers:
                raise ScenarioError(
                    f"{scenario.name} y{y.offset}: '{f.driver}' flexed twice in the "
                    f"same year -- the intended net effect is ambiguous."
                )
            seen_drivers.add(f.driver)
            if f.mode not in MODES:
                raise ScenarioError(f"{scenario.name} y{y.offset}: mode {f.mode!r} "
                                    f"not in {MODES}.")
            if f.kind not in KINDS:
                raise ScenarioError(f"{scenario.name} y{y.offset}: kind {f.kind!r} "
                                    f"not in {KINDS}.")
            if not f.basis.strip():
                raise ScenarioError(
                    f"{scenario.name} y{y.offset}: '{f.driver}' has no basis. Every "
                    f"flexed driver states why it moved by that amount."
                )
            if UNSOURCED in f.basis:
                missing.append(f"  {scenario.name} y{y.offset}: {f.driver} -- {f.basis}")

    if missing:
        raise ScenarioError(
            f"{scenario.name} still has {len(missing)} unsourced magnitude(s). "
            f"Research and cite them, or drop the flex -- it will not run as a "
            f"placeholder:\n" + "\n".join(missing)
        )


def build_driver_path(base: Drivers, scenario: Scenario,
                      horizon: int = 5) -> tuple[Drivers, ...]:
    """Base drivers -> one Drivers per forecast year. Years with no flexes get the
    base drivers unchanged, so Base-case is the degenerate case of this function with
    an empty schedule -- it is the same code path, not a separate one, which is what
    guarantees the three scenarios stay comparable."""
    validate(scenario, horizon)
    path: list[Drivers] = []
    for offset in range(1, horizon + 1):
        y = scenario.year(offset)
        if y is None or not y.flexes:
            path.append(base)
            continue
        updates = {f.driver: f.apply(getattr(base, f.driver)) for f in y.flexes}
        path.append(dataclasses.replace(base, **updates))
    return tuple(path)


@dataclass(frozen=True)
class ScenarioRun:
    scenario: Scenario
    base_year: int
    forecast: dict[int, dict[str, float]]
    driver_path: tuple[Drivers, ...]
    insolvent_years: tuple[int, ...]
    reconciliation_failures: tuple[str, ...]

    @property
    def clean(self) -> bool:
        """Arithmetic integrity only. NOT an economic verdict: `insolvent_years` being
        non-empty is a finding about the scenario, not a defect in it, and is
        deliberately excluded from this flag."""
        return not self.reconciliation_failures


def run_scenario(table: dict[int, dict[str, float]], base_year: int,
                 base_drivers: Drivers, scenario: Scenario,
                 horizon: int = 5) -> ScenarioRun:
    """Project `horizon` years with a different Drivers each year.

    Two checks are carried through per year rather than left to the caller:
    `reconcile_forecast_year` (Trellis's arithmetic invariant -- a failure here is a
    bug, and this module introduces a new way to hit it since it varies drivers
    mid-path) and `project_year`'s `insolvent` flag. The insolvency flag matters far
    more in a Bear case than it ever did in Trellis's single base case: a downside
    path that cannot fund its own dividend is a real result the report should state,
    and silently returning those numbers as a valuation input would be the exact
    failure this portfolio's other repos were built to avoid."""
    path = build_driver_path(base_drivers, scenario, horizon)
    forecast: dict[int, dict[str, float]] = {}
    insolvent: list[int] = []
    failures: list[str] = []

    prior = table[base_year]
    for i, drivers in enumerate(path, start=1):
        year = base_year + i
        projected = project_year(prior, drivers)
        forecast[year] = projected
        if projected.get("insolvent"):
            insolvent.append(year)
        check = reconcile_forecast_year(
            year, projected, prior["cash_and_equivalents"]
        )
        if not check.passed:
            failures.append(check.detail)
        prior = projected

    return ScenarioRun(
        scenario=scenario, base_year=base_year, forecast=forecast,
        driver_path=path, insolvent_years=tuple(insolvent),
        reconciliation_failures=tuple(failures),
    )


def provenance_table(scenario: Scenario) -> str:
    """Every flexed driver, its year, its evidence tier and its basis -- the block the
    report reproduces verbatim so a reader can challenge an assumption individually
    instead of accepting or rejecting the scenario whole."""
    lines = [f"{scenario.name}: {scenario.thesis}"]
    if not scenario.years:
        lines.append("  (no flexes -- base drivers held flat across the horizon)")
    for y in sorted(scenario.years, key=lambda s: s.offset):
        head = f"  Year +{y.offset}"
        if y.note:
            head += f" -- {y.note}"
        lines.append(head)
        for f in y.flexes:
            lines.append(f"    [{f.kind:<8}] {f.label()}")
            lines.append(f"               {f.basis}")
    return "\n".join(lines)


def tier_mix(scenario: Scenario) -> dict[str, int]:
    """Count of flexes by evidence tier. Surfaced in the summary so a scenario built
    mostly on judgment is visibly built mostly on judgment."""
    counts = {k: 0 for k in KINDS}
    for y in scenario.years:
        for f in y.flexes:
            counts[f.kind] += 1
    return counts


@dataclass(frozen=True)
class ResearchItem:
    driver: str
    years: tuple[int, ...]
    text: str


def research_items(scenario: Scenario) -> tuple[ResearchItem, ...]:
    """Outstanding UNSOURCED magnitudes, DEDUPLICATED by the underlying question.

    Deduplication is not cosmetic. A derived consolidated driver quotes the same
    segment rationale in every one of its five years, so a naive listing turns four
    real research tasks into thirteen entries -- and a checklist nobody can read is a
    checklist nobody works through, which defeats the point of blocking the run.
    Items are keyed on the question text and report which years they affect.
    """
    found: dict[tuple[str, str], list[int]] = {}
    for y in sorted(scenario.years, key=lambda s: s.offset):
        for f in y.flexes:
            if UNSOURCED not in f.basis:
                continue
            # A basis may embed several quoted sub-rationales (one per segment).
            for frag in f.basis.split(UNSOURCED)[1:]:
                text = frag.lstrip(" -")
                # Cut at whichever boundary comes first: the next quoted segment
                # rationale, or the derived trailer. Without this the first item
                # absorbs the opening of the second and the checklist reads as
                # corrupted -- which costs it exactly the trust it needs to be used.
                for boundary in (");", ". Implied revenue mix", ". Base-year segment"):
                    text = text.split(boundary)[0]
                text = text.strip().rstrip(").").strip()
                found.setdefault((f.driver, text), []).append(y.offset)
    return tuple(
        ResearchItem(driver=d, years=tuple(sorted(set(yrs))), text=t)
        for (d, t), yrs in found.items()
    )
