from datetime import date

import pytest

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.radar import (
    RadarEntry,
    RadarScenario,
    RadarSort,
    RadarSortDirection,
    RadarSortMetric,
    sort_radar_entries,
)
from src.value import ValueCondition


AS_OF_DATE = date(2026, 9, 21)
FISCAL_PERIOD_END = date(2026, 12, 31)


def _scenario(
    name: str = "base",
    expected_return: float | None = 0.10,
    required_price: float | None = 50.0,
    price_margin: float | None = 0.0,
) -> RadarScenario:
    return RadarScenario(
        name=name,
        expected_return=expected_return,
        required_price=required_price,
        price_margin=price_margin,
        condition=ValueCondition.TARGET_MET,
    )


def _entry(
    company_id: int,
    scenarios: tuple[RadarScenario, ...],
) -> RadarEntry:
    return RadarEntry(
        company_id=company_id,
        as_of_date=AS_OF_DATE,
        fiscal_period_end=FISCAL_PERIOD_END,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        quality_reasons=(),
        risk_reasons=(),
        value_trap_reasons=(),
        scenarios=scenarios,
    )


def test_sort_expected_return_descending():
    entries = (
        _entry(
            1,
            (_scenario(expected_return=0.08),),
        ),
        _entry(
            2,
            (_scenario(expected_return=0.15),),
        ),
        _entry(
            3,
            (_scenario(expected_return=0.11),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 3, 1]


def test_sort_expected_return_ascending():
    entries = (
        _entry(
            1,
            (_scenario(expected_return=0.08),),
        ),
        _entry(
            2,
            (_scenario(expected_return=0.15),),
        ),
        _entry(
            3,
            (_scenario(expected_return=0.11),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
            direction=RadarSortDirection.ASCENDING,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1, 3, 2]


def test_sort_price_margin():
    entries = (
        _entry(
            1,
            (_scenario(price_margin=-0.10),),
        ),
        _entry(
            2,
            (_scenario(price_margin=0.25),),
        ),
        _entry(
            3,
            (_scenario(price_margin=0.05),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.PRICE_MARGIN,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 3, 1]


def test_sort_required_price():
    entries = (
        _entry(
            1,
            (_scenario(required_price=40.0),),
        ),
        _entry(
            2,
            (_scenario(required_price=70.0),),
        ),
        _entry(
            3,
            (_scenario(required_price=55.0),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.REQUIRED_PRICE,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 3, 1]


def test_none_values_are_always_last():
    entries = (
        _entry(
            3,
            (_scenario(expected_return=None),),
        ),
        _entry(
            2,
            (_scenario(expected_return=0.05),),
        ),
        _entry(
            1,
            (_scenario(expected_return=None),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
            direction=RadarSortDirection.ASCENDING,
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 1, 3]


def test_missing_scenario_is_always_last():
    entries = (
        _entry(
            3,
            (_scenario(name="bear"),),
        ),
        _entry(
            2,
            (_scenario(expected_return=0.05),),
        ),
        _entry(
            1,
            (),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 1, 3]


def test_equal_values_use_company_id_as_tie_breaker():
    entries = (
        _entry(
            3,
            (_scenario(expected_return=0.10),),
        ),
        _entry(
            1,
            (_scenario(expected_return=0.10),),
        ),
        _entry(
            2,
            (_scenario(expected_return=0.10),),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [1, 2, 3]


def test_sort_uses_named_scenario_only():
    entries = (
        _entry(
            1,
            (
                _scenario(
                    name="bear",
                    expected_return=0.30,
                ),
                _scenario(
                    name="base",
                    expected_return=0.05,
                ),
            ),
        ),
        _entry(
            2,
            (
                _scenario(
                    name="bear",
                    expected_return=0.01,
                ),
                _scenario(
                    name="base",
                    expected_return=0.15,
                ),
            ),
        ),
    )

    result = sort_radar_entries(
        entries=entries,
        radar_sort=RadarSort(
            metric=RadarSortMetric.EXPECTED_RETURN,
            scenario_name="base",
        ),
    )

    assert [
        entry.company_id
        for entry in result
    ] == [2, 1]


def test_blank_scenario_name_is_rejected():
    radar_sort = RadarSort(
        metric=RadarSortMetric.EXPECTED_RETURN,
        scenario_name="   ",
    )

    assert radar_sort.is_valid() is False

    with pytest.raises(
        ValueError,
        match="scenario_name",
    ):
        sort_radar_entries(
            entries=(),
            radar_sort=radar_sort,
        )


def test_duplicate_scenario_names_are_rejected():
    entries = (
        _entry(
            1,
            (
                _scenario(name="base"),
                _scenario(name="base"),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate scenario",
    ):
        sort_radar_entries(
            entries=entries,
            radar_sort=RadarSort(
                metric=RadarSortMetric.EXPECTED_RETURN,
                scenario_name="base",
            ),
        )