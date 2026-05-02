from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi_users import exceptions
from starlette.requests import Request

from onyx.db.enums import AccountType
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.auth_check import is_route_in_spec_list
from onyx.server.auth_check import PUBLIC_ENDPOINT_SPECS
from onyx.server.sub2api import api as sub2api_api
from onyx.server.sub2api.api import sub2api_exchange
from onyx.server.sub2api.api import upsert_onyx_user_from_sub2api
from onyx.server.sub2api.models import Sub2APICredentialPayload
from onyx.server.sub2api.models import Sub2APIExchangeUser
from onyx.server.sub2api.models import Sub2APILaunchExchangeResponse


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/sub2api/exchange",
            "headers": [],
            "query_string": b"token=launch-token",
        }
    )


def _exchange_response() -> Sub2APILaunchExchangeResponse:
    return Sub2APILaunchExchangeResponse(
        user=Sub2APIExchangeUser(
            id=42,
            email="user@example.com",
            username="Example User",
        ),
        credential=Sub2APICredentialPayload(
            api_key_id=7,
            api_key="sk-sub2api",
            api_base_url="https://sub2api.example.com/v1",
            text_model_name="gpt-5.5",
            image_model_name="gpt-image-2",
        ),
    )


def test_sub2api_exchange_route_is_marked_public() -> None:
    route = next(
        route
        for route in sub2api_api.router.routes
        if getattr(route, "path", "") == "/sub2api/exchange"
    )

    assert is_route_in_spec_list(route, PUBLIC_ENDPOINT_SPECS)


@pytest.mark.asyncio
async def test_sub2api_exchange_consumes_token_saves_credential_and_redirects() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_active=True,
        account_type=AccountType.STANDARD,
    )
    login_response = MagicMock()
    login_response.headers = {"set-cookie": "auth-cookie=value; Path=/"}
    user_manager = MagicMock()
    user_manager.on_after_login = AsyncMock()
    strategy = MagicMock()
    db_session = MagicMock()

    with (
        patch.object(sub2api_api, "SUB2API_INTEGRATION_ENABLED", True),
        patch.object(
            sub2api_api,
            "exchange_sub2api_launch_token",
            AsyncMock(return_value=_exchange_response()),
        ) as exchange_mock,
        patch.object(
            sub2api_api,
            "upsert_onyx_user_from_sub2api",
            AsyncMock(return_value=user),
        ) as user_mock,
        patch.object(sub2api_api, "upsert_sub2api_credential_for_user") as cred_mock,
        patch.object(sub2api_api.auth_backend, "login", AsyncMock(return_value=login_response)),
    ):
        response = await sub2api_exchange(
            request=_request(),
            token=" launch-token ",
            strategy=strategy,
            user_manager=user_manager,
            db_session=db_session,
        )

    exchange_mock.assert_awaited_once_with("launch-token")
    user_mock.assert_awaited_once_with(
        email="user@example.com",
        username="Example User",
        user_manager=user_manager,
    )
    cred_mock.assert_called_once()
    assert cred_mock.call_args.kwargs["sub2api_user_id"] == 42
    db_session.commit.assert_called_once()
    user_manager.on_after_login.assert_awaited_once()
    assert response.status_code == 302
    assert response.headers["location"] == "/chat"
    assert response.headers["set-cookie"] == "auth-cookie=value; Path=/"


@pytest.mark.asyncio
async def test_sub2api_exchange_rejects_disabled_integration() -> None:
    with patch.object(sub2api_api, "SUB2API_INTEGRATION_ENABLED", False):
        with pytest.raises(OnyxError) as exc:
            await sub2api_exchange(
                request=_request(),
                token="launch-token",
                strategy=MagicMock(),
                user_manager=MagicMock(),
                db_session=MagicMock(),
            )

    assert exc.value.error_code == OnyxErrorCode.SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_sub2api_exchange_rejects_empty_token() -> None:
    with patch.object(sub2api_api, "SUB2API_INTEGRATION_ENABLED", True):
        with pytest.raises(OnyxError) as exc:
            await sub2api_exchange(
                request=_request(),
                token=" ",
                strategy=MagicMock(),
                user_manager=MagicMock(),
                db_session=MagicMock(),
            )

    assert exc.value.error_code == OnyxErrorCode.MISSING_REQUIRED_FIELD


@pytest.mark.asyncio
async def test_sub2api_exchange_rejects_inactive_user_without_saving_credential() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_active=False,
        account_type=AccountType.STANDARD,
    )
    db_session = MagicMock()

    with (
        patch.object(sub2api_api, "SUB2API_INTEGRATION_ENABLED", True),
        patch.object(
            sub2api_api,
            "exchange_sub2api_launch_token",
            AsyncMock(return_value=_exchange_response()),
        ),
        patch.object(
            sub2api_api,
            "upsert_onyx_user_from_sub2api",
            AsyncMock(return_value=user),
        ),
        patch.object(sub2api_api, "upsert_sub2api_credential_for_user") as cred_mock,
    ):
        with pytest.raises(OnyxError) as exc:
            await sub2api_exchange(
                request=_request(),
                token="launch-token",
                strategy=MagicMock(),
                user_manager=MagicMock(),
                db_session=db_session,
            )

    assert exc.value.error_code == OnyxErrorCode.UNAUTHENTICATED
    cred_mock.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_sub2api_exchange_rejects_non_web_user_without_saving_credential() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_active=True,
        account_type=AccountType.BOT,
    )
    db_session = MagicMock()

    with (
        patch.object(sub2api_api, "SUB2API_INTEGRATION_ENABLED", True),
        patch.object(
            sub2api_api,
            "exchange_sub2api_launch_token",
            AsyncMock(return_value=_exchange_response()),
        ),
        patch.object(
            sub2api_api,
            "upsert_onyx_user_from_sub2api",
            AsyncMock(return_value=user),
        ),
        patch.object(sub2api_api, "upsert_sub2api_credential_for_user") as cred_mock,
    ):
        with pytest.raises(OnyxError) as exc:
            await sub2api_exchange(
                request=_request(),
                token="launch-token",
                strategy=MagicMock(),
                user_manager=MagicMock(),
                db_session=db_session,
            )

    assert exc.value.error_code == OnyxErrorCode.UNAUTHORIZED
    cred_mock.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_onyx_user_from_sub2api_reuses_existing_web_user() -> None:
    existing_user = SimpleNamespace(
        email="user@example.com",
        account_type=AccountType.STANDARD,
    )
    user_manager = MagicMock()
    user_manager.get_by_email = AsyncMock(return_value=existing_user)
    user_manager.create = AsyncMock()

    result = await upsert_onyx_user_from_sub2api(
        email=" USER@EXAMPLE.COM ",
        username="Example User",
        user_manager=user_manager,
    )

    assert result is existing_user
    user_manager.get_by_email.assert_awaited_once_with("user@example.com")
    user_manager.create.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_onyx_user_from_sub2api_creates_missing_web_user() -> None:
    created_user = SimpleNamespace(
        email="user@example.com",
        account_type=AccountType.STANDARD,
    )
    user_manager = MagicMock()
    user_manager.get_by_email = AsyncMock(side_effect=exceptions.UserNotExists())
    user_manager.create = AsyncMock(return_value=created_user)

    result = await upsert_onyx_user_from_sub2api(
        email="user@example.com",
        username="Example User",
        user_manager=user_manager,
    )

    assert result is created_user
    user_manager.create.assert_awaited_once()
    created_payload = user_manager.create.await_args.args[0]
    assert created_payload.email == "user@example.com"
    assert created_payload.role == "basic"
    assert created_payload.account_type == AccountType.STANDARD
    assert created_payload.is_verified is True


@pytest.mark.asyncio
async def test_upsert_onyx_user_from_sub2api_rejects_existing_non_web_user() -> None:
    existing_user = SimpleNamespace(
        email="user@example.com",
        account_type=AccountType.BOT,
    )
    user_manager = MagicMock()
    user_manager.get_by_email = AsyncMock(return_value=existing_user)

    with pytest.raises(OnyxError) as exc:
        await upsert_onyx_user_from_sub2api(
            email="user@example.com",
            username="Example User",
            user_manager=user_manager,
        )

    assert exc.value.error_code == OnyxErrorCode.UNAUTHORIZED


@pytest.mark.asyncio
async def test_upsert_onyx_user_from_sub2api_rejects_missing_email() -> None:
    user_manager = MagicMock()

    with pytest.raises(OnyxError) as exc:
        await upsert_onyx_user_from_sub2api(
            email=" ",
            username="Example User",
            user_manager=user_manager,
        )

    assert exc.value.error_code == OnyxErrorCode.INVALID_INPUT
