from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.sub2api import client as sub2api_client
from onyx.server.sub2api.client import exchange_sub2api_launch_token


def _exchange_payload() -> dict:
    return {
        "user_id": 42,
        "email": "user@example.com",
        "username": "Example User",
        "api_key_id": 7,
        "api_key": "sk-sub2api",
        "api_base_url": "https://sub2api.example.com/v1",
        "text_model_name": "gpt-5.5",
        "image_model_name": "gpt-image-2",
    }


@pytest.mark.asyncio
async def test_exchange_sub2api_launch_token_posts_token_with_shared_secret() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=_exchange_payload())

    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=response)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(sub2api_client.httpx, "AsyncClient", return_value=fake_client):
        result = await exchange_sub2api_launch_token(
            token="launch-token",
            base_url="https://sub2api.example.com/",
            exchange_secret="shared-secret",
        )

    fake_client.post.assert_awaited_once_with(
        "https://sub2api.example.com/api/v1/onyx/exchange",
        json={"token": "launch-token"},
        headers={"X-Sub2API-Onyx-Secret": "shared-secret"},
    )
    assert result.user.email == "user@example.com"
    assert result.credential.api_key == "sk-sub2api"
    assert result.credential.text_model_name == "gpt-5.5"
    assert result.credential.image_model_name == "gpt-image-2"


@pytest.mark.asyncio
async def test_exchange_sub2api_launch_token_rejects_missing_configuration() -> None:
    with pytest.raises(OnyxError) as exc:
        await exchange_sub2api_launch_token(
            token="launch-token",
            base_url="",
            exchange_secret="shared-secret",
        )

    assert exc.value.error_code == OnyxErrorCode.SERVICE_UNAVAILABLE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "reason", "expected_error_code", "expected_detail"),
    [
        (
            401,
            "ONYX_TOKEN_EXPIRED",
            OnyxErrorCode.INVALID_TOKEN,
            "Sub2API launch link is invalid or expired.",
        ),
        (
            409,
            "ONYX_NO_ELIGIBLE_API_KEY",
            OnyxErrorCode.CONFLICT,
            "Sub2API user does not have an eligible API key.",
        ),
        (
            503,
            "ONYX_NOT_CONFIGURED",
            OnyxErrorCode.SERVICE_UNAVAILABLE,
            "Sub2API integration is not configured.",
        ),
    ],
)
async def test_exchange_sub2api_launch_token_maps_upstream_status_error(
    status_code: int,
    reason: str,
    expected_error_code: OnyxErrorCode,
    expected_detail: str,
) -> None:
    request = httpx.Request("POST", "https://sub2api.example.com/api/v1/onyx/exchange")
    upstream_response = httpx.Response(
        status_code,
        request=request,
        json={"reason": reason, "message": "upstream message"},
    )

    response = MagicMock()
    response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "conflict",
            request=request,
            response=upstream_response,
        )
    )

    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=response)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(sub2api_client.httpx, "AsyncClient", return_value=fake_client):
        with pytest.raises(OnyxError) as exc:
            await exchange_sub2api_launch_token(
                token="launch-token",
                base_url="https://sub2api.example.com",
                exchange_secret="shared-secret",
            )

    assert exc.value.error_code == expected_error_code
    assert exc.value.status_code == expected_error_code.status_code
    assert exc.value.detail == expected_detail
