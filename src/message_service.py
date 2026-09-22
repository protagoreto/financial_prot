from src.messaging import OutboundMessage
from src.presentation import AnalysisPresentation
from src.presentation_text import render_analysis_text
from src.providers.message_base import MessageProvider


def send_analysis_presentation(
    provider: MessageProvider,
    destination: str,
    presentation: AnalysisPresentation,
) -> OutboundMessage:
    provider_name = provider.name.strip()

    if not provider_name:
        raise ValueError(
            "Message provider name cannot be blank."
        )

    message = OutboundMessage(
        destination=destination,
        text=render_analysis_text(presentation),
    )

    if not message.is_valid():
        raise ValueError(
            "Outbound message is invalid."
        )

    provider.send(message)

    return message
