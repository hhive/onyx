from unittest.mock import Mock
from unittest.mock import patch

from onyx.configs.model_configs import GEN_AI_TEMPERATURE
from onyx.llm.constants import LlmProviderNames
from onyx.llm.factory import _build_provider_extra_headers
from onyx.llm.factory import _build_sub2api_runtime_llm
from onyx.llm.factory import get_llm
from onyx.llm.factory import get_llm_for_persona
from onyx.llm.factory import llm_from_provider
from onyx.llm.well_known_providers.constants import OLLAMA_API_KEY_CONFIG_KEY
from onyx.server.manage.llm.models import LLMProviderView
from onyx.server.manage.llm.models import ModelConfigurationView


def test_build_provider_extra_headers_adds_bearer_for_ollama_api_key() -> None:
    headers = _build_provider_extra_headers(
        LlmProviderNames.OLLAMA_CHAT,
        {OLLAMA_API_KEY_CONFIG_KEY: "  test-key  "},
    )

    assert headers == {"Authorization": "Bearer test-key"}


def test_build_provider_extra_headers_keeps_existing_bearer_prefix() -> None:
    headers = _build_provider_extra_headers(
        LlmProviderNames.OLLAMA_CHAT,
        {OLLAMA_API_KEY_CONFIG_KEY: "bearer test-key"},
    )

    assert headers == {"Authorization": "bearer test-key"}


def test_build_provider_extra_headers_ignores_empty_ollama_api_key() -> None:
    headers = _build_provider_extra_headers(
        LlmProviderNames.OLLAMA_CHAT,
        {OLLAMA_API_KEY_CONFIG_KEY: "   "},
    )

    assert headers == {}


def _build_provider_view(
    provider: str,
    max_input_tokens: int | None,
) -> LLMProviderView:
    return LLMProviderView(
        id=1,
        name="test-provider",
        provider=provider,
        model_configurations=[
            ModelConfigurationView(
                name="test-model",
                is_visible=True,
                max_input_tokens=max_input_tokens,
                supports_image_input=False,
            )
        ],
        api_key=None,
        api_base="http://localhost:11434",
        api_version=None,
        custom_config=None,
        is_public=True,
        is_auto_mode=False,
        groups=[],
        personas=[],
        deployment_name=None,
    )


def test_get_llm_sets_ollama_num_ctx_model_kwarg() -> None:
    with patch("onyx.llm.factory.LitellmLLM") as mock_litellm_llm:
        get_llm(
            provider=LlmProviderNames.OLLAMA_CHAT,
            model="test-model",
            deployment_name=None,
            max_input_tokens=4096,
            model_kwargs={"num_ctx": 8192},
        )

        kwargs = mock_litellm_llm.call_args.kwargs
        assert kwargs["model_kwargs"] == {"num_ctx": 8192}


def test_get_llm_does_not_set_ollama_num_ctx_for_non_ollama_provider() -> None:
    with patch("onyx.llm.factory.LitellmLLM") as mock_litellm_llm:
        get_llm(
            provider=LlmProviderNames.OPENAI,
            model="gpt-4o-mini",
            deployment_name=None,
            max_input_tokens=4096,
        )

        kwargs = mock_litellm_llm.call_args.kwargs
        assert kwargs["model_kwargs"] == {}


def test_llm_from_provider_passes_configured_ollama_num_ctx() -> None:
    provider = _build_provider_view(
        provider=LlmProviderNames.OLLAMA_CHAT,
        max_input_tokens=16384,
    )

    with patch("onyx.llm.factory.get_llm") as mock_get_llm:
        llm_from_provider(
            model_name="test-model",
            llm_provider=provider,
        )

        kwargs = mock_get_llm.call_args.kwargs
        assert kwargs["max_input_tokens"] == 16384
        assert kwargs["model_kwargs"] == {"num_ctx": 16384}


def test_llm_from_provider_omits_ollama_num_ctx_when_model_context_unknown() -> None:
    provider = _build_provider_view(
        provider=LlmProviderNames.OLLAMA_CHAT,
        max_input_tokens=None,
    )

    with (
        patch(
            "onyx.llm.factory.get_max_input_tokens_from_llm_provider",
            return_value=32000,
        ),
        patch("onyx.llm.factory.get_llm") as mock_get_llm,
    ):
        llm_from_provider(
            model_name="test-model",
            llm_provider=provider,
        )

        kwargs = mock_get_llm.call_args.kwargs
        assert kwargs["max_input_tokens"] == 32000
        assert kwargs["model_kwargs"] == {}


def test_llm_from_provider_never_sets_ollama_num_ctx_for_non_ollama_provider() -> None:
    provider = _build_provider_view(
        provider=LlmProviderNames.OPENAI,
        max_input_tokens=16384,
    )

    with patch("onyx.llm.factory.get_llm") as mock_get_llm:
        llm_from_provider(
            model_name="test-model",
            llm_provider=provider,
        )

        kwargs = mock_get_llm.call_args.kwargs
        assert kwargs["max_input_tokens"] == 16384
        assert kwargs["model_kwargs"] == {}


def _mock_persona(default_model_configuration_id: int | None = None) -> Mock:
    persona = Mock()
    persona.id = 7
    persona.default_model_configuration_id = default_model_configuration_id
    return persona


def _mock_user() -> Mock:
    user = Mock()
    user.id = 1
    user.role = None
    return user


def test_get_llm_for_persona_uses_sub2api_default_runtime_llm_without_db_default() -> None:
    runtime_llm = Mock()
    user = _mock_user()

    with (
        patch(
            "onyx.llm.factory._build_sub2api_default_runtime_llm",
            return_value=runtime_llm,
        ) as mock_build_runtime,
        patch("onyx.llm.factory.get_default_llm") as mock_get_default,
    ):
        llm = get_llm_for_persona(
            _mock_persona(),
            user,
            additional_headers={"x-test": "1"},
        )

    assert llm is runtime_llm
    mock_build_runtime.assert_called_once_with(
        user=user,
        temperature=GEN_AI_TEMPERATURE,
        additional_headers={"x-test": "1"},
    )
    mock_get_default.assert_not_called()


def test_get_llm_for_persona_falls_back_to_db_default_without_sub2api_credential() -> None:
    default_llm = Mock()

    with (
        patch("onyx.llm.factory._build_sub2api_default_runtime_llm", return_value=None),
        patch("onyx.llm.factory.get_default_llm", return_value=default_llm),
    ):
        llm = get_llm_for_persona(_mock_persona(), _mock_user())

    assert llm is default_llm


def test_get_llm_for_persona_without_persona_uses_sub2api_runtime_default_first() -> None:
    runtime_llm = Mock()

    with (
        patch(
            "onyx.llm.factory._build_sub2api_default_runtime_llm",
            return_value=runtime_llm,
        ) as mock_build_runtime,
        patch("onyx.llm.factory.get_default_llm") as mock_get_default,
    ):
        llm = get_llm_for_persona(None, _mock_user())

    assert llm is runtime_llm
    mock_build_runtime.assert_called_once()
    mock_get_default.assert_not_called()


def test_build_sub2api_runtime_llm_sets_browser_user_agent() -> None:
    credential = Mock()
    credential.api_key.get_value.return_value = "test-api-key"

    with (
        patch("onyx.llm.factory.get_session_with_current_tenant") as mock_session,
        patch(
            "onyx.llm.factory.get_sub2api_user_credentials",
            return_value=credential,
        ),
        patch(
            "onyx.llm.factory.resolve_sub2api_api_base_url",
            return_value="http://127.0.0.1:8080/v1",
        ),
        patch("onyx.llm.factory.get_llm") as mock_get_llm,
    ):
        mock_session.return_value.__enter__.return_value = Mock()

        _build_sub2api_runtime_llm(
            user=_mock_user(),
            model_name="gpt-5.5",
            temperature=0,
            additional_headers={"X-Test": "1"},
        )

    kwargs = mock_get_llm.call_args.kwargs
    assert kwargs["provider"] == LlmProviderNames.OPENAI_COMPATIBLE
    assert kwargs["additional_headers"] == {
        "X-Test": "1",
        "User-Agent": "Mozilla/5.0",
    }
    assert kwargs["litellm_client"].api_key == "test-api-key"
    assert str(kwargs["litellm_client"].base_url) == "http://127.0.0.1:8080/v1/"
