from datetime import date

from src.assessment import AssessmentLevel, RiskLevel
from src.investment import AnalysisAvailability
from src.messaging import OutboundMessage
from src.providers.message_base import MessageProvider
from src.radar_message_service import send_radar_report_row
from src.radar_report import RadarReportRow
from src.value import ValueCondition


class FakeMessageProvider(MessageProvider):
    def __init__(self) -> None:
        self.messages: list[OutboundMessage] = []

    @property
    def name(self) -> str:
        return "fake"

    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        self.messages.append(message)


def test_send_radar_report_row():
    provider = FakeMessageProvider()

    row = RadarReportRow(
        company_id=1,
        name="Example Company",
        ticker="EX",
        exchange="TEST",
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
        required_price=100.0,
        price_margin=0.05,
        condition=ValueCondition.TARGET_MET,
    )

    message = send_radar_report_row(
        provider=provider,
        destination="123456",
        row=row,
    )

    assert len(provider.messages) == 1
    assert provider.messages[0] == message
    assert message.destination == "123456"
    assert "Example Company" in message.text
    assert "Base" in message.text
    assert "0.12" in message.text
    assert "100.0" in message.text
