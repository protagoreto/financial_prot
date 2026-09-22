from dataclasses import dataclass


@dataclass(frozen=True)
class OutboundMessage:
    destination: str
    text: str

    def is_valid(self) -> bool:
        if not self.destination.strip():
            return False

        if not self.text.strip():
            return False

        return True
