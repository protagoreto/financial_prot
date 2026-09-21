from datetime import date

import pytest

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import (
    RadarEntry,
    RadarFilter,
    RadarScenario,
    RadarSnapshot,
    filter_radar_entries,
)
from src.value import ValueCondition


AS_OF_DATE = date(2026, 9, 21)
FISCAL_PERIOD_END = date(2026, 12, 31)


def _scenario(
    name: str = "base",
    expected_return: float | None = 0.12,
    price_margin: float | None = 0.10,
    condition: ValueCondition = ValueCondition.TARGET_MET,
) -> RadarScenario:
    return RadarScenario(
        name=name,
        expected_return=expected_return,
        required_price=55.0,
        price_margin=price_margin,
        condition=condition,
    )


def _entry(
    company_id: int,
    availability: AnalysisAvailability = AnalysisAvailability.COMPLETE,
    quality_level: AssessmentLevel | None = AssessmentLevel.STRONG,
    risk_level: RiskLevel | None = RiskLevel.LOW,
    value_trap_warning: bool | None = False,
    scenarios: tuple[RadarScenario, ...] | None = None,
) -> RadarEntry:
    return RadarEntry(
        company_id=company_id,
        as_of_date=AS_OF_DATE,
        fiscal_period_end=FISCAL_PERIOD_END,
        availability=availability,
        quality_level=quality_level,
        risk_level=risk_level,
        value_trap_warning=value_trap_warning,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=(
            (_scenario(),)
            if scenarios is None
            else scenarios
        ),
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


def test_empty_filter_preserves_all_entries_and_order():
    snapshot = _snapshot(
        _entry(3),
        _entry(1),
        _entry(2),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [3, 1, 2]


def test_filter_combines_fundamental_criteria_with_and_semantics():
    snapshot = _snapshot(
        _entry(1),
        _entry(
            2,
            risk_level=RiskLevel.HIGH,
        ),
        _entry(
            3,
            quality_level=AssessmentLevel.WEAK,
        ),
        _entry(
            4,
            value_trap_warning=True,
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            availability=AnalysisAvailability.COMPLETE,
            quality_level=AssessmentLevel.STRONG,
            risk_level=RiskLevel.LOW,
            value_trap_warning=False,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1]


def test_unknown_value_trap_does_not_match_false():
    snapshot = _snapshot(
        _entry(
            1,
            value_trap_warning=None,
        ),
        _entry(
            2,
            value_trap_warning=False,
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            value_trap_warning=False,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2]


def test_filter_uses_named_scenario():
    snapshot = _snapshot(
        _entry(
            1,
            scenarios=(
                _scenario(
                    name="bear",
                    condition=ValueCondition.TARGET_NOT_MET,
                ),
                _scenario(
                    name="base",
                    condition=ValueCondition.TARGET_MET,
                ),
            ),
        ),
        _entry(
            2,
            scenarios=(
                _scenario(
                    name="base",
                    condition=ValueCondition.TARGET_NOT_MET,
                ),
            ),
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            scenario_name="base",
            condition=ValueCondition.TARGET_MET,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1]


def test_missing_named_scenario_does_not_match():
    snapshot = _snapshot(
        _entry(
            1,
            scenarios=(
                _scenario(name="bear"),
            ),
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            scenario_name="base",
            condition=ValueCondition.TARGET_MET,
        ),
    )

    assert result == ()


def test_filter_applies_minimum_expected_return():
    snapshot = _snapshot(
        _entry(
            1,
            scenarios=(
                _scenario(expected_return=0.15),
            ),
        ),
        _entry(
            2,
            scenarios=(
                _scenario(expected_return=0.09),
            ),
        ),
        _entry(
            3,
            scenarios=(
                _scenario(expected_return=None),
            ),
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            scenario_name="base",
            min_expected_return=0.10,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1]


def test_filter_applies_minimum_price_margin():
    snapshot = _snapshot(
        _entry(
            1,
            scenarios=(
                _scenario(price_margin=0.20),
            ),
        ),
        _entry(
            2,
            scenarios=(
                _scenario(price_margin=-0.05),
            ),
        ),
        _entry(
            3,
            scenarios=(
                _scenario(price_margin=None),
            ),
        ),
    )

    result = filter_radar_entries(
        snapshot=snapshot,
        radar_filter=RadarFilter(
            scenario_name="base",
            min_price_margin=0.0,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1]


def test_scenario_criteria_require_scenario_name():
    radar_filter = RadarFilter(
        min_expected_return=0.10,
    )

    assert radar_filter.is_valid() is False

    with pytest.raises(
        ValueError,
        match="scenario_name",
    ):
        filter_radar_entries(
            snapshot=_snapshot(_entry(1)),
            radar_filter=radar_filter,
        )


def test_blank_scenario_name_is_invalid():
    radar_filter = RadarFilter(
        scenario_name="   ",
    )

    assert radar_filter.is_valid() is False


def test_duplicate_scenario_names_are_rejected():
    snapshot = _snapshot(
        _entry(
            1,
            scenarios=(
                _scenario(name="base"),
                _scenario(name="base"),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate scenario",
    ):
        filter_radar_entries(
            snapshot=snapshot,
            radar_filter=RadarFilter(
                scenario_name="base",
            ),
        )