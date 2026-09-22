from src.messaging import OutboundMessage


def test_outbound_message_is_valid():
    message = OutboundMessage(
        destination="123456",
        text="Test message",
    )

    assert message.is_valid()


def test_outbound_message_rejects_blank_destination():
    message = OutboundMessage(
        destination="   ",
        text="Test message",
    )

    assert not message.is_valid()


def test_outbound_message_rejects_blank_text():
    message = OutboundMessage(
        destination="123456",
        text="   ",
    )

    assert not message.is_valid()
