from datetime import date

import pytest

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import (
    RadarEntry,
    RadarScenario,
    RadarSnapshot,
)
from src.radar_report import build_radar_report
from src.value import ValueCondition


AS_OF_DATE = date(2026, 9, 22)
FISCAL_PERIOD_END = date(2026, 12, 31)


def _entry(
    company_id: int,
    scenarios: tuple[RadarScenario, ...],
) -> RadarEntry:
    return RadarEntry(
        company_id=company_id,
        name=f"Company {company_id}",
        ticker=f"C{company_id}",
        exchange="BME",
        as_of_date=AS_OF_DATE,
        fiscal_period_end=FISCAL_PERIOD_END,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=("quality",),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=scenarios,
    )


def _scenario(
    name: str = "base",
    expected_return: float | None = 0.12,
    required_price: float | None = 55.0,
    price_margin: float | None = 0.10,
) -> RadarScenario:
    return RadarScenario(
        name=name,
        expected_return=expected_return,
        required_price=required_price,
        price_margin=price_margin,
        condition=ValueCondition.TARGET_MET,
    )


def _snapshot(
    *entries: RadarEntry,
) -> RadarSnapshot:
    return RadarSnapshot(
        as_of_date=AS_OF_DATE,
        target_return=0.10,
        years=5,
        entries=entries,
    )


def test_report_projects_company_and_scenario_data():
    snapshot = _snapshot(
        _entry(1, (_scenario(),)),
    )

    rows = build_radar_report(
        snapshot=snapshot,
        scenario_name="base",
    )

    assert len(rows) == 1

    row = rows[0]

    assert row.company_id == 1
    assert row.name == "Company 1"
    assert row.ticker == "C1"
    assert row.exchange == "BME"
    assert row.as_of_date == AS_OF_DATE
    assert row.fiscal_period_end == FISCAL_PERIOD_END
    assert row.target_return == pytest.approx(0.10)
    assert row.years == 5
    assert row.availability == AnalysisAvailability.COMPLETE
    assert row.quality_level == AssessmentLevel.STRONG
    assert row.risk_level == RiskLevel.LOW
    assert row.value_trap_warning is False
    assert row.scenario_name == "base"
    assert row.expected_return == pytest.approx(0.12)
    assert row.required_price == pytest.approx(55.0)
    assert row.price_margin == pytest.approx(0.10)
    assert row.condition == ValueCondition.TARGET_MET


def test_report_preserves_entry_order():
    snapshot = _snapshot(
        _entry(3, (_scenario(),)),
        _entry(1, (_scenario(),)),
        _entry(2, (_scenario(),)),
    )

    rows = build_radar_report(
        snapshot=snapshot,
        scenario_name="base",
    )

    assert [
        row.company_id
        for row in rows
    ] == [3, 1, 2]


def test_report_can_project_filtered_or_sorted_entries():
    snapshot = _snapshot(
        _entry(1, (_scenario(),)),
        _entry(2, (_scenario(),)),
        _entry(3, (_scenario(),)),
    )

    selected_entries = (
        snapshot.entries[2],
        snapshot.entries[0],
    )

    rows = build_radar_report(
        snapshot=snapshot,
        scenario_name="base",
        entries=selected_entries,
    )

    assert [
        row.company_id
        for row in rows
    ] == [3, 1]


def test_report_uses_only_named_scenario():
    entry = _entry(
        1,
        (
            _scenario(
                name="bear",
                expected_return=-0.05,
                required_price=35.0,
                price_margin=-0.30,
            ),
            _scenario(
                name="base",
                expected_return=0.12,
                required_price=55.0,
                price_margin=0.10,
            ),
        ),
    )

    rows = build_radar_report(
        snapshot=_snapshot(entry),
        scenario_name="base",
    )

    row = rows[0]

    assert row.scenario_name == "base"
    assert row.expected_return == pytest.approx(0.12)
    assert row.required_price == pytest.approx(55.0)
    assert row.price_margin == pytest.approx(0.10)


def test_report_preserves_missing_scenario_as_unavailable():
    entry = _entry(
        1,
        (),
    )

    rows = build_radar_report(
        snapshot=_snapshot(entry),
        scenario_name="base",
    )

    row = rows[0]

    assert row.scenario_name == "base"
    assert row.expected_return is None
    assert row.required_price is None
    assert row.price_margin is None
    assert row.condition is None


def test_report_preserves_missing_metrics():
    entry = _entry(
        1,
        (
            _scenario(
                expected_return=None,
                required_price=None,
                price_margin=None,
            ),
        ),
    )

    rows = build_radar_report(
        snapshot=_snapshot(entry),
        scenario_name="base",
    )

    row = rows[0]

    assert row.expected_return is None
    assert row.required_price is None
    assert row.price_margin is None


def test_report_rejects_blank_scenario_name():
    snapshot = _snapshot()

    with pytest.raises(
        ValueError,
        match="non-empty scenario_name",
    ):
        build_radar_report(
            snapshot=snapshot,
            scenario_name="   ",
        )


def test_report_rejects_duplicate_scenario_names():
    entry = _entry(
        1,
        (
            _scenario(),
            _scenario(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate scenario names",
    ):
        build_radar_report(
            snapshot=_snapshot(entry),
            scenario_name="base",
        )