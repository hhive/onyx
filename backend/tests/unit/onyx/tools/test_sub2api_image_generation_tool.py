from unittest.mock import MagicMock
from unittest.mock import patch

from onyx.tools.tool_constructor import _get_sub2api_image_generation_config
from onyx.tools.tool_implementations.images.image_generation_tool import (
    ImageGenerationTool,
)


class FakeUser:
    id = "user-1"


class FakeEncryptedValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool = False) -> str:
        return "****" if apply_mask else self.value


class FakeCredential:
    def __init__(self, api_key: str) -> None:
        self.api_key = FakeEncryptedValue(api_key)


def test_image_generation_tool_available_when_sub2api_image_configured() -> None:
    with (
        patch(
            "onyx.tools.tool_implementations.images.image_generation_tool.is_sub2api_image_generation_configured",
            return_value=True,
        ),
        patch(
            "onyx.tools.tool_implementations.images.image_generation_tool.get_default_image_generation_config",
        ) as mock_get_default,
    ):
        assert ImageGenerationTool.is_available(MagicMock()) is True
        mock_get_default.assert_not_called()


def test_get_sub2api_image_generation_config_uses_user_credential_and_default_model(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "onyx.tools.tool_constructor.SUB2API_DEFAULT_IMAGE_MODEL",
        "gpt-image-2",
    )

    with (
        patch(
            "onyx.tools.tool_constructor.is_sub2api_image_generation_configured",
            return_value=True,
        ),
        patch(
            "onyx.tools.tool_constructor.get_sub2api_user_credentials",
            return_value=FakeCredential("sk-user"),
        ),
        patch(
            "onyx.server.sub2api.image_generation.resolve_sub2api_api_base_url",
            return_value="http://127.0.0.1:8080/v1",
        ),
    ):
        config = _get_sub2api_image_generation_config(FakeUser(), MagicMock())

    assert config is not None
    credentials, provider, model = config
    assert credentials.api_key == "sk-user"
    assert credentials.api_base == "http://127.0.0.1:8080/v1"
    assert provider == "openai"
    assert model == "gpt-image-2"


def test_get_sub2api_image_generation_config_skips_without_user_credential() -> None:
    with (
        patch(
            "onyx.tools.tool_constructor.is_sub2api_image_generation_configured",
            return_value=True,
        ),
        patch(
            "onyx.tools.tool_constructor.get_sub2api_user_credentials",
            return_value=None,
        ),
    ):
        assert _get_sub2api_image_generation_config(FakeUser(), MagicMock()) is None
