from typing import Any

import httpx
from pydantic import ValidationError

from onyx.configs.app_configs import SUB2API_BASE_URL
from onyx.configs.app_configs import SUB2API_EXCHANGE_SECRET
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.sub2api.models import Sub2APILaunchExchangeResponse

SUB2API_EXCHANGE_SECRET_HEADER = "X-Sub2API-Onyx-Secret"
SUB2API_EXCHANGE_PATH = "/api/v1/onyx/exchange"


async def exchange_sub2api_launch_token(
    token: str,
    *,
    base_url: str | None = None,
    exchange_secret: str | None = None,
) -> Sub2APILaunchExchangeResponse:
    resolved_base_url = (base_url if base_url is not None else SUB2API_BASE_URL).strip()
    resolved_secret = (
        exchange_secret if exchange_secret is not None else SUB2API_EXCHANGE_SECRET
    ).strip()
    if not resolved_base_url or not resolved_secret:
        raise OnyxError(
            OnyxErrorCode.SERVICE_UNAVAILABLE,
            "Sub2API integration is not configured.",
        )

    exchange_url = f"{resolved_base_url.rstrip('/')}{SUB2API_EXCHANGE_PATH}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                exchange_url,
                json={"token": token},
                headers={SUB2API_EXCHANGE_SECRET_HEADER: resolved_secret},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as e:
        raise _upstream_error(e.response) from e
    except httpx.HTTPError as e:
        raise OnyxError(
            OnyxErrorCode.BAD_GATEWAY,
            f"Failed to call Sub2API exchange endpoint: {e}",
        ) from e

    try:
        return Sub2APILaunchExchangeResponse.from_sub2api_payload(
            _extract_exchange_payload(payload)
        )
    except (KeyError, TypeError, ValidationError) as e:
        raise OnyxError(
            OnyxErrorCode.BAD_GATEWAY,
            "Sub2API exchange endpoint returned an invalid payload.",
        ) from e


def _extract_exchange_payload(payload: dict) -> dict:
    if "data" in payload:
        data = payload["data"]
        if not isinstance(data, dict):
            raise TypeError("Sub2API exchange response data must be an object.")
        return data
    return payload


def _upstream_error(response: httpx.Response) -> OnyxError:
    reason = _extract_upstream_reason(response)
    if response.status_code == 401:
        return OnyxError(
            OnyxErrorCode.INVALID_TOKEN,
            "Sub2API launch link is invalid or expired.",
        )
    if response.status_code == 409 or reason == "ONYX_NO_ELIGIBLE_API_KEY":
        return OnyxError(
            OnyxErrorCode.CONFLICT,
            "Sub2API user does not have an eligible API key.",
        )
    if response.status_code == 503:
        return OnyxError(
            OnyxErrorCode.SERVICE_UNAVAILABLE,
            "Sub2API integration is not configured.",
        )

    detail = _extract_upstream_detail(response)
    return OnyxError(
        OnyxErrorCode.BAD_GATEWAY,
        detail,
        status_code_override=response.status_code,
    )


def _extract_upstream_reason(response: httpx.Response) -> str | None:
    try:
        payload: Any = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        reason = payload.get("reason") or payload.get("error_code")
        if reason:
            return str(reason)
    return None


def _extract_upstream_detail(response: httpx.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        return response.text or "Sub2API exchange request failed."

    if isinstance(payload, dict):
        reason = payload.get("reason") or payload.get("error_code")
        message = payload.get("message") or payload.get("detail")
        if reason and message:
            return f"{reason}: {message}"
        if reason:
            return str(reason)
        if message:
            return str(message)
    return "Sub2API exchange request failed."
