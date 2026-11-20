import re

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

from onyx.configs.app_configs import (
    SUB2API_APP_ID,
    SUB2API_APP_SECRET,
    SUB2API_BASE_URL,
    SUB2API_INTEGRATION_ENABLED,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.llm.model_catalog import iter_image_generation_models
from onyx.server.sub2api.models import (
    AppExchange,
    ImageCredential,
    ImageModelEntry,
    KeyModels,
    KeyPage,
)

APP_SECRET_HEADER = "X-Sub2API-App-Secret"
KEY_ID_HEADER = "X-Sub2API-Key-ID"
KEY_PLATFORM_HEADER = "X-Sub2API-Key-Platform"
DIRECTORY_TIMEOUT = 10.0


def app_endpoint() -> str:
    if (
        not SUB2API_INTEGRATION_ENABLED
        or not SUB2API_APP_SECRET
        or not SUB2API_BASE_URL
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", SUB2API_APP_ID)
    ):
        raise OnyxError(OnyxErrorCode.SERVICE_UNAVAILABLE, "Sub2API is unavailable.")
    return f"{SUB2API_BASE_URL.rstrip('/')}/api/v1/app-integrations/{SUB2API_APP_ID}"


def app_headers(grant: SecretStr | None = None) -> dict[str, str]:
    headers = {APP_SECRET_HEADER: SUB2API_APP_SECRET}
    if grant is not None:
        headers["Authorization"] = f"Bearer {grant.get_secret_value()}"
    return headers


def validate_response[T: BaseModel](response: httpx.Response, schema: type[T]) -> T:
    try:
        response.raise_for_status()
        payload = response.json()
        if schema is KeyModels and isinstance(payload, dict):
            payload["platform"] = response.headers.get(
                KEY_PLATFORM_HEADER
            ) or payload.get("platform")
        return schema.model_validate(payload)
    except httpx.HTTPStatusError:
        status = response.status_code
        if status == 401:
            raise OnyxError(
                OnyxErrorCode.UNAUTHENTICATED, "Sub2API authorization expired."
            ) from None
        if status == 403:
            raise OnyxError(
                OnyxErrorCode.UNAUTHORIZED, "Sub2API access denied."
            ) from None
        if status == 409:
            raise OnyxError(
                OnyxErrorCode.CONFLICT, "The Sub2API key is unavailable."
            ) from None
        raise OnyxError(OnyxErrorCode.BAD_GATEWAY, "Sub2API request failed.") from None
    except (ValueError, ValidationError):
        raise OnyxError(
            OnyxErrorCode.BAD_GATEWAY, "Sub2API returned an invalid response."
        ) from None


async def _request(
    method: str,
    path: str,
    grant: SecretStr | None = None,
    *,
    body: dict[str, str] | None = None,
    params: dict[str, int] | None = None,
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=DIRECTORY_TIMEOUT) as client:
            return await client.request(
                method,
                f"{app_endpoint()}{path}",
                headers=app_headers(grant),
                json=body,
                params=params,
            )
    except httpx.RequestError:
        raise OnyxError(OnyxErrorCode.BAD_GATEWAY, "Sub2API is unavailable.") from None


async def exchange(ticket: str) -> AppExchange:
    return validate_response(
        await _request("POST", "/exchange", body={"ticket": ticket}), AppExchange
    )


async def list_keys(grant: SecretStr, page: int, page_size: int) -> KeyPage:
    return validate_response(
        await _request(
            "GET", "/keys", grant, params={"page": page, "page_size": page_size}
        ),
        KeyPage,
    )


async def key_models(grant: SecretStr, key_id: int) -> KeyModels:
    catalog = validate_response(
        await _request("GET", f"/keys/{key_id}/models", grant), KeyModels
    )
    if catalog.platform.lower() in {"openai", "composite"}:
        known_ids = {model.id for model in catalog.image_models}
        catalog.image_models.extend(
            ImageModelEntry(id=model_id, confirmed=False)
            for model_id in iter_image_generation_models("openai")
            if model_id not in known_ids
        )
    return catalog


async def revoke(grant: SecretStr) -> None:
    response = await _request("POST", "/revoke", grant)
    if response.status_code not in (200, 204, 401):
        raise OnyxError(OnyxErrorCode.BAD_GATEWAY, "Sub2API logout failed.")


def image_credential(client: httpx.Client, grant: SecretStr, key_id: int) -> SecretStr:
    try:
        response = client.post(
            f"{app_endpoint()}/keys/{key_id}/credential",
            headers=app_headers(grant),
            timeout=DIRECTORY_TIMEOUT,
        )
    except httpx.RequestError:
        raise OnyxError(
            OnyxErrorCode.BAD_GATEWAY, "Sub2API image credentials are unavailable."
        ) from None
    return validate_response(response, ImageCredential).api_key
