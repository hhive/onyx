from types import SimpleNamespace
from uuid import uuid4

from onyx.llm import factory
from onyx.llm.constants import LlmProviderNames


class _Secret:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool) -> str:
        assert apply_mask is False
        return self.value


def test_get_sub2api_llm_for_user_uses_user_credential(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4())
    credential = SimpleNamespace(
        api_key=_Secret("sk-user"),
        api_base_url="https://sub2api.example.com/v1",
        text_model_name="gpt-5.5",
    )
    db_session = object()
    calls = []

    def get_credential(session, user_id):
        assert session is db_session
        assert user_id == user.id
        return credential

    monkeypatch.setattr(
        factory,
        "get_sub2api_credential_for_user",
        get_credential,
    )
    monkeypatch.setattr(
        factory,
        "get_llm",
        lambda **kwargs: calls.append(kwargs) or "llm",
    )

    result = factory._get_sub2api_llm_for_user(user, db_session)

    assert result == "llm"
    assert calls == [
        {
            "provider": LlmProviderNames.OPENAI_COMPATIBLE,
            "model": "gpt-5.5",
            "deployment_name": None,
            "api_key": "sk-user",
            "api_base": "https://sub2api.example.com/v1",
            "api_version": None,
            "custom_config": None,
            "timeout": None,
            "temperature": None,
            "additional_headers": None,
            "max_input_tokens": 128000,
            "model_kwargs": {},
        }
    ]
