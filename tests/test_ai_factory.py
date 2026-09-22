import pytest

from src.providers.ai_base import AIProvider
from src.providers.ai_factory import build_ai_provider
from src.providers.ai_local import LocalAIProvider


def test_build_ai_provider_returns_local_provider():
    provider = build_ai_provider("local")

    assert isinstance(provider, AIProvider)
    assert isinstance(provider, LocalAIProvider)
    assert provider.name == "local"


def test_build_ai_provider_normalizes_name():
    provider = build_ai_provider("  LOCAL  ")

    assert isinstance(provider, LocalAIProvider)
    assert provider.name == "local"


@pytest.mark.parametrize(
    "provider_name",
    [
        "",
        " ",
        "unknown",
        "openai",
    ],
)
def test_build_ai_provider_rejects_unsupported_provider(
    provider_name: str,
):
    with pytest.raises(
        ValueError,
        match="Unsupported AI provider",
    ):
        build_ai_provider(provider_name)
