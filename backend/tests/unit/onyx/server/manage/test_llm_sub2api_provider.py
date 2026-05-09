from types import SimpleNamespace
from uuid import uuid4

from onyx.llm.constants import LlmProviderNames
from onyx.server.manage.llm import api as llm_api


class _Secret:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool) -> str:
        assert apply_mask is False
        return self.value


def test_list_llm_provider_basics_includes_user_sub2api_models(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), role="basic")
    credential = SimpleNamespace(
        api_key=_Secret("sk-user"),
        api_base_url="https://sub2api.example.com/v1",
        text_model_name="gpt-5.5",
    )

    monkeypatch.setattr(llm_api, "fetch_existing_llm_providers", lambda *_args: [])
    monkeypatch.setattr(llm_api, "fetch_default_llm_model", lambda *_args: None)
    monkeypatch.setattr(llm_api, "fetch_default_vision_model", lambda *_args: None)
    monkeypatch.setattr(llm_api, "fetch_user_group_ids", lambda *_args: set())
    monkeypatch.setattr(
        llm_api,
        "get_sub2api_credential_for_user",
        lambda _db_session, user_id: credential if user_id == user.id else None,
    )
    monkeypatch.setattr(
        llm_api,
        "_fetch_sub2api_model_configurations",
        lambda _credential: [
            llm_api.ModelConfigurationView(
                name="gpt-5.4",
                is_visible=True,
                max_input_tokens=None,
                supports_image_input=True,
                supports_reasoning=False,
                display_name="gpt-5.4",
            ),
            llm_api.ModelConfigurationView(
                name="gpt-5.5",
                is_visible=True,
                max_input_tokens=None,
                supports_image_input=True,
                supports_reasoning=False,
                display_name="gpt-5.5",
            ),
        ],
    )

    response = llm_api.list_llm_provider_basics(user=user, db_session=object())

    assert response.default_text is not None
    assert response.default_text.provider_id == llm_api.SUB2API_PROVIDER_ID
    assert response.default_text.model_name == "gpt-5.5"
    assert len(response.providers) == 1
    provider = response.providers[0]
    assert provider.id == llm_api.SUB2API_PROVIDER_ID
    assert provider.name == llm_api.SUB2API_PROVIDER_NAME
    assert provider.provider == LlmProviderNames.OPENAI_COMPATIBLE
    assert [model.name for model in provider.model_configurations] == [
        "gpt-5.4",
        "gpt-5.5",
    ]
    assert all(model.supports_image_input for model in provider.model_configurations)


def test_fetch_sub2api_models_filters_non_chat_models_and_marks_chat_models_vision_capable(
    monkeypatch,
) -> None:
    credential = SimpleNamespace(
        api_key=_Secret("sk-user"),
        api_base_url="https://sub2api.example.com/v1",
        text_model_name="fallback-model",
    )

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"id": "gpt-5.5"},
                    {"id": "claude-sonnet-4"},
                    {"id": "text-embedding-3-large", "type": "embedding"},
                    {"id": "gpt-image-2", "type": "image"},
                    {
                        "id": "custom-image-model",
                        "capabilities": ["image_generation"],
                    },
                    {"id": "dall-e-3"},
                ]
            }

    monkeypatch.setattr(llm_api.httpx, "get", lambda *_args, **_kwargs: _Response())

    models = llm_api._fetch_sub2api_model_configurations(credential)

    assert [model.name for model in models] == [
        "fallback-model",
        "gpt-5.5",
        "claude-sonnet-4",
    ]
    assert all(model.supports_image_input for model in models)


def test_sub2api_image_generation_model_detection_uses_type_capabilities_and_name() -> None:
    assert llm_api._is_sub2api_image_generation_model("model-a", "image")
    assert llm_api._is_sub2api_image_generation_model(
        "model-b",
        None,
        {"capabilities": {"image_generation": True}},
    )
    assert llm_api._is_sub2api_image_generation_model("gpt-image-2")
    assert llm_api._is_sub2api_image_generation_model("dall-e-3")
    assert not llm_api._is_sub2api_image_generation_model("gpt-5.5")
