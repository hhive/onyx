from types import SimpleNamespace
from uuid import uuid4

from onyx.image_gen.factory import ImageGenerationProviderName
from onyx.tools import tool_constructor


class _Secret:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool) -> str:
        assert apply_mask is False
        return self.value


def test_get_user_sub2api_image_generation_config_uses_user_credential(
    monkeypatch,
) -> None:
    user = SimpleNamespace(id=uuid4())
    credential = SimpleNamespace(
        api_key=_Secret("sk-image-user"),
        api_base_url="https://sub2api.example.com/v1",
        image_model_name="gpt-image-2",
    )
    llm = SimpleNamespace(config=SimpleNamespace(max_input_tokens=8192))
    db_session = object()

    def get_credential(session, user_id):
        assert session is db_session
        assert user_id == user.id
        return credential

    monkeypatch.setattr(
        tool_constructor,
        "get_sub2api_credential_for_user",
        get_credential,
    )

    result = tool_constructor._get_user_sub2api_image_generation_config(
        llm=llm,
        db_session=db_session,
        user=user,
    )

    assert result is not None
    assert result.model_provider == ImageGenerationProviderName.OPENAI.value
    assert result.model_name == "gpt-image-2"
    assert result.api_key == "sk-image-user"
    assert result.api_base == "https://sub2api.example.com/v1"
    assert result.api_version is None
    assert result.deployment_name == "gpt-image-2"
    assert result.max_input_tokens == 8192


def test_construct_tools_prefers_user_sub2api_image_generation_config(
    monkeypatch,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        oauth_accounts=[],
        is_anonymous=False,
        enable_memory_tool=False,
    )
    credential = SimpleNamespace(
        api_key=_Secret("sk-image-user"),
        api_base_url="https://sub2api.example.com/v1",
        image_model_name="gpt-image-2",
    )
    llm = SimpleNamespace(config=SimpleNamespace(max_input_tokens=8192))
    tool_model = SimpleNamespace(
        id=7,
        name="generate_image",
        in_code_tool_id=100,
        openapi_schema=None,
        mcp_server_id=None,
    )
    persona = SimpleNamespace(
        id=1,
        name="Assistant",
        tools=[tool_model],
        document_sets=[],
        search_start_date=None,
        attached_documents=[],
        hierarchy_nodes=[],
    )
    created_tools = []

    class FakeImageGenerationTool:
        __name__ = "ImageGenerationTool"

        def __init__(
            self,
            image_generation_credentials,
            provider,
            model,
            tool_id,
            emitter,
        ) -> None:
            self.image_generation_credentials = image_generation_credentials
            self.provider = provider
            self.model = model
            self.tool_id = tool_id
            self.emitter = emitter
            created_tools.append(self)

        @classmethod
        def is_available(cls, _db_session) -> bool:
            return False

    def get_built_in_tool_by_id(_tool_id):
        return FakeImageGenerationTool

    def get_current_search_settings(_db_session):
        return object()

    def get_default_document_index(
        _search_settings,
        _secondary_search_settings,
        _db_session,
    ):
        return object()

    def get_sub2api_credential_for_user(_db_session, _user_id):
        return credential

    def get_global_image_generation_config(_llm, _db_session):
        raise AssertionError("global image generation config should not be used")

    monkeypatch.setattr(tool_constructor, "ImageGenerationTool", FakeImageGenerationTool)
    monkeypatch.setattr(
        tool_constructor,
        "get_built_in_tool_by_id",
        get_built_in_tool_by_id,
    )
    monkeypatch.setattr(
        tool_constructor,
        "get_current_search_settings",
        get_current_search_settings,
    )
    monkeypatch.setattr(
        tool_constructor,
        "get_default_document_index",
        get_default_document_index,
    )
    monkeypatch.setattr(
        tool_constructor,
        "get_sub2api_credential_for_user",
        get_sub2api_credential_for_user,
    )
    monkeypatch.setattr(
        tool_constructor,
        "_get_image_generation_config",
        get_global_image_generation_config,
    )

    result = tool_constructor._construct_tools_impl(
        persona=persona,
        db_session=object(),
        emitter=object(),
        user=user,
        llm=llm,
    )

    assert result[7] == created_tools
    assert len(created_tools) == 1
    image_tool = created_tools[0]
    assert image_tool.provider == ImageGenerationProviderName.OPENAI.value
    assert image_tool.model == "gpt-image-2"
    assert image_tool.image_generation_credentials.api_key == "sk-image-user"
    assert (
        image_tool.image_generation_credentials.api_base
        == "https://sub2api.example.com/v1"
    )
