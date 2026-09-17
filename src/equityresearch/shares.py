"""
Diluted share count.

WHY THIS IS NEW WORK RATHER THAN A CONFIG CHANGE
-------------------------------------------------
Checked directly against the upstream repos: Trellis's `schema.py` captures no share
count at all, and ValuationLab's `marketdata.py` takes `sharesOutstanding` from the
market-data provider -- a point-in-time BASIC count, which its own docstring already
flags. Neither repo can produce a diluted figure, so nothing downstream of them can.

That was tolerable upstream. ValuationLab's headline outputs are enterprise values and
method-fitness verdicts; the share count only ever touched the equity-value bridge at
the end. An initiation-of-coverage report's entire output is a per-share target price
against a per-share market price. Dividing an equity value by the wrong share base
moves the target price by exactly the dilution percentage, in the direction that
flatters the recommendation, and it is the first thing a buy-side reader checks. So it
gets fixed here rather than carried forward.

WHICH DILUTED NUMBER, AND THE HONEST CAVEAT
--------------------------------------------
Two different things are available, and they are not interchangeable:

  us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding
      Diluted, but a WEIGHTED AVERAGE over the fiscal period. It is the correct
      denominator for that period's diluted EPS. It is backward-looking: a company
      that repurchased steadily through the year ends the year below its own weighted
      average.

  dei:EntityCommonStockSharesOutstanding
      Point-in-time, as of the filing cover date -- the most CURRENT count available.
      But it is basic: it excludes in-the-money options, RSUs and convertibles.

There is no free XBRL tag that is both current and diluted, because that figure is not
a reported fact -- it is a calculation an analyst makes. So this module returns both,
computes the gap between them, and refuses to pick silently. `recommended()` states the
choice and its direction of error rather than hiding it:

  - Use weighted-average diluted as the denominator. Dilution is the larger and more
    persistent of the two effects for a mature filer, and understating the share base
    overstates the target price -- the error that matters.
  - State the residual. If the cover-page basic count is materially BELOW the
    weighted-average basic count, buybacks have shrunk the base since period-end and
    the diluted weighted average is now conservative by roughly that difference. Say
    so in the report; do not quietly split the difference.

The one thing this module will not do is invent a "current diluted" number by adding
the dilution gap to the cover-page count. That composite appears in no filing, and
manufacturing it would be exactly the kind of unsourced precision the rest of this
portfolio exists to refuse.
"""

from __future__ import annotations

from dataclasses import dataclass

DILUTED_WA_TAG = "WeightedAverageNumberOfDilutedSharesOutstanding"
BASIC_WA_TAG = "WeightedAverageNumberOfSharesOutstandingBasic"
BASIC_WA_TAG_ALT = "WeightedAverageNumberOfSharesOutstanding"
COVER_PAGE_TAG = "EntityCommonStockSharesOutstanding"


class ShareCountError(ValueError):
    """Raised when no defensible diluted share count can be produced. Deliberately
    fatal: the alternative is a per-share target price on a guessed denominator."""


@dataclass(frozen=True)
class ShareCount:
    fiscal_year: int
    diluted_weighted_average: float
    basic_weighted_average: float | None
    cover_page_basic: float | None
    cover_page_date: str | None
    source: str

    @property
    def dilution_shares(self) -> float | None:
        """Diluted minus basic weighted average -- the dilutive securities themselves."""
        if self.basic_weighted_average is None:
            return None
        return self.diluted_weighted_average - self.basic_weighted_average

    @property
    def dilution_pct(self) -> float | None:
        if self.basic_weighted_average in (None, 0):
            return None
        return self.diluted_weighted_average / self.basic_weighted_average - 1.0

    @property
    def buyback_drift(self) -> float | None:
        """Cover-page basic minus basic weighted average. Negative = the share base has
        shrunk since the period's average, so the diluted weighted average overstates
        today's count and the resulting per-share value is conservative."""
        if self.cover_page_basic is None or self.basic_weighted_average is None:
            return None
        return self.cover_page_basic - self.basic_weighted_average

    def recommended(self) -> tuple[float, str]:
        """(denominator, the caveat that goes in the report verbatim)."""
        note = [
            f"FY{self.fiscal_year} diluted weighted-average shares "
            f"{self.diluted_weighted_average:,.0f}."
        ]
        if self.dilution_pct is not None:
            note.append(
                f"Dilutive securities add {self.dilution_pct:.2%} over the basic "
                f"weighted average ({self.basic_weighted_average:,.0f})."
            )
        drift = self.buyback_drift
        if drift is not None and self.basic_weighted_average:
            direction = "below" if drift < 0 else "above"
            note.append(
                f"Cover-page basic count ({self.cover_page_basic:,.0f}"
                + (f" as of {self.cover_page_date}" if self.cover_page_date else "")
                + f") sits {abs(drift):,.0f} shares "
                f"({abs(drift) / self.basic_weighted_average:.2%}) {direction} the "
                f"basic weighted average"
                + (", so the denominator used here is conservative by roughly that "
                   "margin." if drift < 0 else
                   ", so the denominator used here may understate today's base.")
            )
        note.append(
            "No current-and-diluted count exists in XBRL; the two are not combined."
        )
        return self.diluted_weighted_average, " ".join(note)


def _annual_rows(facts: dict, taxonomy: str, tag: str) -> list[dict]:
    """Pull annual (FY, 10-K) unit rows for one tag out of a companyfacts payload."""
    node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
    if not node:
        return []
    rows: list[dict] = []
    for unit_rows in node.get("units", {}).values():
        rows.extend(unit_rows)
    return rows


def _pick_annual(rows: list[dict], fiscal_year: int) -> float | None:
    """The FY figure for `fiscal_year` from a 10-K, taking the LATEST-FILED row so a
    restated figure supersedes the original -- the same restatement discipline
    Trellis's ingest applies, reimplemented here rather than assumed, because a share
    count restated after a split would otherwise silently resolve to the pre-split
    number."""
    candidates = [
        r for r in rows
        if r.get("fy") == fiscal_year
        and r.get("fp") == "FY"
        and str(r.get("form", "")).startswith("10-K")
        and r.get("val") is not None
        # Period-length guard: a 10-K also carries quarterly and comparative-year
        # contexts. Require a full-year span so a Q4 row is never mistaken for FY.
        and (r.get("start") is None or _spans_a_year(r.get("start"), r.get("end")))
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: (r.get("filed", ""), r.get("end", "")))
    return float(candidates[-1]["val"])


def _spans_a_year(start: str | None, end: str | None) -> bool:
    if not start or not end:
        return False
    from datetime import date
    try:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
    except ValueError:
        return False
    return 300 <= (e - s).days <= 400


def _latest_cover_page(rows: list[dict]) -> tuple[float | None, str | None]:
    """Most recently filed cover-page count, with its as-of date."""
    dated = [r for r in rows if r.get("val") is not None]
    if not dated:
        return None, None
    dated.sort(key=lambda r: (r.get("filed", ""), r.get("end", "")))
    latest = dated[-1]
    return float(latest["val"]), latest.get("end")


def parse_share_count(facts: dict, fiscal_year: int) -> ShareCount:
    """Extract a share count from an SEC companyfacts payload. Pure -- no network, so
    it is testable against a fixture rather than only against a live filing."""
    diluted = _pick_annual(_annual_rows(facts, "us-gaap", DILUTED_WA_TAG), fiscal_year)
    if diluted is None:
        raise ShareCountError(
            f"No FY{fiscal_year} 10-K value for us-gaap:{DILUTED_WA_TAG}. Without a "
            f"diluted count there is no defensible per-share denominator -- supply one "
            f"manually with a citation rather than falling back to basic."
        )

    basic = _pick_annual(_annual_rows(facts, "us-gaap", BASIC_WA_TAG), fiscal_year)
    if basic is None:
        basic = _pick_annual(
            _annual_rows(facts, "us-gaap", BASIC_WA_TAG_ALT), fiscal_year
        )

    cover, cover_date = _latest_cover_page(
        _annual_rows(facts, "dei", COVER_PAGE_TAG)
    )

    if basic is not None and diluted < basic:
        raise ShareCountError(
            f"FY{fiscal_year}: diluted ({diluted:,.0f}) below basic ({basic:,.0f}). "
            f"Diluted cannot be lower than basic; the tags have resolved to "
            f"inconsistent contexts and the figures are not usable."
        )

    return ShareCount(
        fiscal_year=fiscal_year,
        diluted_weighted_average=diluted,
        basic_weighted_average=basic,
        cover_page_basic=cover,
        cover_page_date=cover_date,
        source=f"SEC XBRL companyfacts: us-gaap:{DILUTED_WA_TAG} (FY{fiscal_year}, "
               f"10-K), dei:{COVER_PAGE_TAG} (latest filed).",
    )


def fetch_share_count(cik: int, fiscal_year: int, session=None) -> ShareCount:
    """Live pull. Reuses Trellis's session and User-Agent handling rather than
    duplicating SEC's request etiquette in a second place."""
    import requests
    from trellis.ingest import make_session, _headers

    session = session or make_session()
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    resp = session.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return parse_share_count(resp.json(), fiscal_year)
