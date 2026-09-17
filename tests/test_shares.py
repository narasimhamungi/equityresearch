import pytest

from equityresearch.shares import ShareCountError, parse_share_count


def _row(val, fy=2025, fp="FY", form="10-K", start="2024-12-30", end="2025-12-28",
         filed="2026-02-17"):
    return {"val": val, "fy": fy, "fp": fp, "form": form,
            "start": start, "end": end, "filed": filed}


def _facts(diluted=None, basic=None, cover=None):
    facts = {"facts": {"us-gaap": {}, "dei": {}}}
    if diluted is not None:
        facts["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"] = {
            "units": {"shares": diluted}}
    if basic is not None:
        facts["facts"]["us-gaap"]["WeightedAverageNumberOfSharesOutstandingBasic"] = {
            "units": {"shares": basic}}
    if cover is not None:
        facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"] = {
            "units": {"shares": cover}}
    return facts


def test_parses_diluted_basic_and_cover_page():
    sc = parse_share_count(
        _facts(diluted=[_row(2_440_000_000)], basic=[_row(2_405_000_000)],
               cover=[_row(2_390_000_000, start=None, end="2026-02-10")]),
        2025)
    assert sc.diluted_weighted_average == 2_440_000_000
    assert sc.dilution_shares == 35_000_000
    assert sc.dilution_pct == pytest.approx(0.014553, rel=1e-3)
    assert sc.cover_page_date == "2026-02-10"


def test_buyback_drift_is_signed_and_the_caveat_calls_the_denominator_conservative():
    """The direction of the error is the whole point -- a reader needs to know which
    way the per-share number is wrong, not just that it is approximate."""
    sc = parse_share_count(
        _facts(diluted=[_row(2_440_000_000)], basic=[_row(2_405_000_000)],
               cover=[_row(2_380_000_000, start=None, end="2026-02-10")]),
        2025)
    assert sc.buyback_drift == -25_000_000
    denom, note = sc.recommended()
    assert denom == 2_440_000_000
    assert "conservative" in note and "not combined" in note


def test_restated_value_supersedes_the_original():
    """A later-filed figure wins. Without this a post-split restatement resolves to
    the pre-split count and every per-share number is off by the split ratio."""
    sc = parse_share_count(_facts(diluted=[
        _row(2_440_000_000, filed="2026-02-17"),
        _row(4_880_000_000, filed="2026-08-01"),
    ]), 2025)
    assert sc.diluted_weighted_average == 4_880_000_000


def test_quarterly_context_inside_a_10k_is_not_mistaken_for_the_full_year():
    sc = parse_share_count(_facts(diluted=[
        _row(2_440_000_000),
        _row(2_460_000_000, start="2025-09-29", end="2025-12-28"),  # Q4 span
    ]), 2025)
    assert sc.diluted_weighted_average == 2_440_000_000


def test_wrong_fiscal_year_is_not_borrowed():
    with pytest.raises(ShareCountError, match="No FY2025"):
        parse_share_count(_facts(diluted=[
            _row(2_500_000_000, fy=2024, start="2023-12-31", end="2024-12-29")]), 2025)


def test_missing_diluted_tag_is_fatal_not_a_basic_fallback():
    """Refusing beats silently reverting to the basic count this module exists to
    replace."""
    with pytest.raises(ShareCountError, match="defensible per-share denominator"):
        parse_share_count(_facts(basic=[_row(2_405_000_000)]), 2025)


def test_diluted_below_basic_is_rejected_as_inconsistent_contexts():
    with pytest.raises(ShareCountError, match="cannot be lower than basic"):
        parse_share_count(
            _facts(diluted=[_row(2_300_000_000)], basic=[_row(2_405_000_000)]), 2025)


def test_falls_back_to_the_alternate_basic_tag():
    facts = _facts(diluted=[_row(2_440_000_000)])
    facts["facts"]["us-gaap"]["WeightedAverageNumberOfSharesOutstanding"] = {
        "units": {"shares": [_row(2_405_000_000)]}}
    assert parse_share_count(facts, 2025).basic_weighted_average == 2_405_000_000


def test_works_with_no_basic_and_no_cover_page():
    sc = parse_share_count(_facts(diluted=[_row(2_440_000_000)]), 2025)
    assert sc.dilution_pct is None and sc.buyback_drift is None
    denom, note = sc.recommended()
    assert denom == 2_440_000_000 and "2,440,000,000" in note


def test_non_10k_forms_are_ignored():
    with pytest.raises(ShareCountError):
        parse_share_count(_facts(diluted=[_row(2_440_000_000, form="10-Q")]), 2025)
