from datetime import date

import pytest

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.message_service import send_analysis_presentation
from src.messaging import OutboundMessage
from src.presentation import AnalysisPresentation
from src.providers.message_base import MessageProvider
from src.value import ValueCondition


class FakeMessageProvider(MessageProvider):
    def __init__(
        self,
        provider_name: str = "fake",
    ) -> None:
        self._provider_name = provider_name
        self.messages: list[OutboundMessage] = []

    @property
    def name(self) -> str:
        return self._provider_name

    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        self.messages.append(message)


def _presentation() -> AnalysisPresentation:
    return AnalysisPresentation(
        company_id=1,
        name="Test Company",
        ticker="TEST",
        exchange="BME",
        as_of_date=date(2026, 9, 22),
        fiscal_period_end=date(2026, 12, 31),
        target_return=0.10,
        years=5,
        availability=AnalysisAvailability.COMPLETE,
        quality_level=AssessmentLevel.STRONG,
        risk_level=RiskLevel.LOW,
        value_trap_warning=False,
        scenario_name="Base",
        expected_return=0.12,
        required_price=55.0,
        price_margin=0.10,
        condition=ValueCondition.TARGET_MET,
    )


def test_send_analysis_presentation():
    provider = FakeMessageProvider()

    message = send_analysis_presentation(
        provider=provider,
        destination="123456",
        presentation=_presentation(),
    )

    assert message.is_valid()
    assert message.destination == "123456"
    assert "Test Company (TEST)" in message.text
    assert "Expected return: 0.12" in message.text

    assert provider.messages == [message]


def test_send_analysis_presentation_rejects_blank_destination():
    provider = FakeMessageProvider()

    with pytest.raises(
        ValueError,
        match="Outbound message is invalid",
    ):
        send_analysis_presentation(
            provider=provider,
            destination=" ",
            presentation=_presentation(),
        )

    assert provider.messages == []


def test_send_analysis_presentation_rejects_blank_provider_name():
    provider = FakeMessageProvider(
        provider_name=" ",
    )

    with pytest.raises(
        ValueError,
        match="Message provider name cannot be blank",
    ):
        send_analysis_presentation(
            provider=provider,
            destination="123456",
            presentation=_presentation(),
        )

    assert provider.messages == []
