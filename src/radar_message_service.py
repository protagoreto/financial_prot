from src.message_service import send_analysis_presentation
from src.messaging import OutboundMessage
from src.presentation import build_analysis_presentation
from src.providers.message_base import MessageProvider
from src.radar_report import RadarReportRow


def send_radar_report_row(
    provider: MessageProvider,
    destination: str,
    row: RadarReportRow,
) -> OutboundMessage:
    presentation = build_analysis_presentation(
        row
    )

    return send_analysis_presentation(
        provider=provider,
        destination=destination,
        presentation=presentation,
    )
