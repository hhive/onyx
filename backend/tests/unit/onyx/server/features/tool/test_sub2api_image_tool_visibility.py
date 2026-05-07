from types import SimpleNamespace
from uuid import uuid4

from onyx.server.features.tool import api as tool_api


class _Secret:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool) -> str:
        assert apply_mask is False
        return self.value


def _tool() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        name="generate_image",
        description="Generate an image",
        openapi_schema=None,
        display_name="Image Generation",
        in_code_tool_id="ImageGenerationTool",
        custom_headers=None,
        passthrough_auth=False,
        mcp_server_id=None,
        user_id=None,
        oauth_config_id=None,
        oauth_config=None,
        enabled=True,
    )


def test_list_tools_includes_image_generation_with_user_sub2api_credential(
    monkeypatch,
) -> None:
    user = SimpleNamespace(id=uuid4())
    credential = SimpleNamespace(
        api_key=_Secret("sk-user"),
        api_base_url="https://sub2api.example.com/v1",
        image_model_name="gpt-image-2",
    )

    class FakeImageGenerationTool:
        __name__ = "ImageGenerationTool"

        @classmethod
        def is_available(cls, _db_session) -> bool:
            return False

    monkeypatch.setattr(tool_api, "get_tools", lambda *_args, **_kwargs: [_tool()])
    monkeypatch.setattr(
        tool_api,
        "get_built_in_tool_by_id",
        lambda _tool_id: FakeImageGenerationTool,
    )
    monkeypatch.setattr(
        tool_api,
        "get_sub2api_credential_for_user",
        lambda _db_session, user_id: credential if user_id == user.id else None,
    )

    tools = tool_api.list_tools(db_session=object(), user=user)

    assert len(tools) == 1
    assert tools[0].in_code_tool_id == "ImageGenerationTool"


def test_list_tools_hides_image_generation_without_config_or_user_credential(
    monkeypatch,
) -> None:
    user = SimpleNamespace(id=uuid4())

    class FakeImageGenerationTool:
        __name__ = "ImageGenerationTool"

        @classmethod
        def is_available(cls, _db_session) -> bool:
            return False

    monkeypatch.setattr(tool_api, "get_tools", lambda *_args, **_kwargs: [_tool()])
    monkeypatch.setattr(
        tool_api,
        "get_built_in_tool_by_id",
        lambda _tool_id: FakeImageGenerationTool,
    )
    monkeypatch.setattr(
        tool_api,
        "get_sub2api_credential_for_user",
        lambda _db_session, _user_id: None,
    )

    tools = tool_api.list_tools(db_session=object(), user=user)

    assert tools == []
