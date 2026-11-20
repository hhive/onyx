from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from onyx.db.models import User
from onyx.server.sub2api import app_session
from onyx.server.sub2api.models import AppGrant, KeyModels, ModelEntry


@pytest.mark.asyncio
async def test_grant_isolated_by_user_and_session_and_revoked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values: dict[str, bytes] = {}

    class Redis:
        async def set(self, name: str, value: bytes, *, ex: int) -> None:
            assert ex == 60
            values[name] = value

        async def get(self, name: str) -> bytes | None:
            return values.get(name)

        async def getdel(self, name: str) -> bytes | None:
            return values.pop(name, None)

    monkeypatch.setattr(
        app_session, "get_async_redis_connection", AsyncMock(return_value=Redis())
    )
    revoke = AsyncMock()
    monkeypatch.setattr(app_session.app_client, "revoke", revoke)
    first_user, second_user = User(id=uuid4()), User(id=uuid4())
    grant = AppGrant(user_id=42, grant_token=SecretStr("test-grant"))
    await app_session.save_grant(first_user, "session-one", grant, 60)
    assert await app_session.get_grant(first_user, "session-one") == grant
    assert await app_session.get_grant(second_user, "session-one") is None
    assert await app_session.get_grant(first_user, "session-two") is None
    await app_session.revoke_session_grant(first_user, "session-one")
    assert await app_session.get_grant(first_user, "session-one") is None
    await app_session.revoke_session_grant(first_user, "session-one")
    revoke.assert_awaited_once_with(grant.grant_token)


def test_catalog_only_includes_chat_models() -> None:
    catalog = KeyModels(
        object="list",
        platform="openai",
        data=[
            ModelEntry(id="chat"),
            ModelEntry(id="gpt-image-2"),
            ModelEntry(id="custom-image", capabilities={"image_generation": True}),
            ModelEntry(id="opaque-id", type="embedding"),
            ModelEntry(id="video", type="video"),
        ],
    )
    assert [model.id for model in catalog.data] == ["chat"]
