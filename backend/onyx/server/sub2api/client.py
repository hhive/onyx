from typing import Any

import httpx

from onyx.configs.app_configs import SUB2API_API_BASE_URL
from onyx.configs.app_configs import SUB2API_BASE_URL
from onyx.configs.app_configs import SUB2API_EXCHANGE_SECRET
from onyx.server.sub2api.models import Sub2APIExchangePayload
from onyx.server.sub2api.models import Sub2APIModel

DEFAULT_SUB2API_BASE_URL = SUB2API_BASE_URL
DEFAULT_SUB2API_API_BASE_URL = SUB2API_API_BASE_URL


def _strip_trailing_slash(value: str) -> str:
    return value.strip().rstrip("/")


def resolve_sub2api_api_base_url() -> str:
    return _strip_trailing_slash(SUB2API_API_BASE_URL)


class Sub2APIClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        exchange_secret: str | None = None,
        api_base_url: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = _strip_trailing_slash(base_url or DEFAULT_SUB2API_BASE_URL)
        self._exchange_secret = exchange_secret or SUB2API_EXCHANGE_SECRET
        self._api_base_url = _strip_trailing_slash(
            api_base_url or resolve_sub2api_api_base_url()
        )
        self._http_client = http_client or httpx.Client(timeout=10, trust_env=False)

    def exchange_launch_token(self, token: str) -> Sub2APIExchangePayload:
        response = self._http_client.post(
            f"{self._base_url}/api/v1/onyx/exchange",
            headers={"x-sub2api-onyx-secret": self._exchange_secret},
            json={"token": token},
        )
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("data"), dict):
            body = body["data"]
        return Sub2APIExchangePayload.model_validate(body)

    def get_models(self, api_key: str) -> list[Sub2APIModel]:
        response = self._http_client.get(
            f"{self._api_base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        raw_models = body.get("data", [])
        if not isinstance(raw_models, list):
            return []

        return [Sub2APIModel.model_validate(model) for model in raw_models]
