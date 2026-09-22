from src.messaging import OutboundMessage
from src.providers.message_base import MessageProvider


def test_message_provider_is_abstract():
    assert MessageProvider.__abstractmethods__ == {
        "name",
        "send",
    }


class FakeMessageProvider(MessageProvider):
    @property
    def name(self) -> str:
        return "fake"

    def send(
        self,
        message: OutboundMessage,
    ) -> None:
        return None


def test_message_provider_can_be_implemented():
    provider = FakeMessageProvider()

    assert isinstance(provider, MessageProvider)
    assert provider.name == "fake"
