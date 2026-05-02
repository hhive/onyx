from types import SimpleNamespace

from onyx.server.query_and_chat import chat_backend


def test_get_available_tokens_for_persona_passes_db_session_to_user_llm(
    monkeypatch,
) -> None:
    db_session = object()
    user = SimpleNamespace(id="user-id")
    persona = SimpleNamespace(
        replace_base_system_prompt=False,
        system_prompt="custom",
        tools=[object(), object()],
    )
    llm = SimpleNamespace(config=SimpleNamespace(max_input_tokens=8192))

    def get_llm_for_persona(*, persona, user, db_session=None, **_kwargs):
        assert persona is not None
        assert user.id == "user-id"
        assert db_session is not None
        return llm

    monkeypatch.setattr(chat_backend, "get_llm_for_persona", get_llm_for_persona)
    monkeypatch.setattr(chat_backend, "get_llm_token_counter", lambda _llm: len)
    monkeypatch.setattr(
        chat_backend,
        "get_default_base_system_prompt",
        lambda _db_session: "base",
    )

    result = chat_backend._get_available_tokens_for_persona(
        persona=persona,
        db_session=db_session,
        user=user,
    )

    assert result == 8192 - len("custom base") - 2 * 256 - 2000


def test_rename_chat_session_uses_user_llm_when_name_generated(monkeypatch) -> None:
    expected_db_session = object()
    user = SimpleNamespace(id="user-id")
    request = SimpleNamespace(headers={})
    rename_req = SimpleNamespace(name=None, chat_session_id="chat-id")
    expected_llm = SimpleNamespace(config=SimpleNamespace(api_key="sk-user"))

    def get_llm_for_persona(*, persona, user, db_session=None, **_kwargs):
        assert persona is None
        assert user.id == "user-id"
        assert db_session is expected_db_session
        return expected_llm

    monkeypatch.setattr(chat_backend, "get_llm_for_persona", get_llm_for_persona)
    monkeypatch.setattr(
        chat_backend,
        "check_llm_cost_limit_for_provider",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_backend,
        "create_chat_history_chain",
        lambda **_kwargs: ["hello"],
    )
    monkeypatch.setattr(chat_backend, "get_llm_token_counter", lambda _llm: len)
    monkeypatch.setattr(
        chat_backend,
        "convert_chat_history_basic",
        lambda **kwargs: kwargs["chat_history"],
    )

    def generate_chat_session_name(*, chat_history, llm):
        assert chat_history == ["hello"]
        assert llm is expected_llm
        return "generated name"

    monkeypatch.setattr(
        chat_backend,
        "generate_chat_session_name",
        generate_chat_session_name,
    )
    updates = []
    monkeypatch.setattr(
        chat_backend,
        "update_chat_session",
        lambda **kwargs: updates.append(kwargs),
    )

    response = chat_backend.rename_chat_session(
        rename_req=rename_req,
        request=request,
        user=user,
        db_session=expected_db_session,
    )

    assert response.new_name == "generated name"
    assert updates[0]["description"] == "generated name"
