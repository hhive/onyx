import httpx
import pytest

import onyx.server.sub2api.client as sub2api_client
from onyx.server.sub2api.client import Sub2APIClient


def test_resolve_sub2api_api_base_url_prefers_explicit_api_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sub2api_client, "SUB2API_API_BASE_URL", "http://sub2api.internal:8080/v1/"
    )

    assert sub2api_client.resolve_sub2api_api_base_url() == (
        "http://sub2api.internal:8080/v1"
    )


def test_resolve_sub2api_api_base_url_uses_configured_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sub2api_client, "SUB2API_API_BASE_URL", "http://127.0.0.1:8080/v1"
    )

    assert sub2api_client.resolve_sub2api_api_base_url() == "http://127.0.0.1:8080/v1"


def test_exchange_launch_token_posts_to_sub2api_exchange_endpoint() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "success",
                "data": {
                    "user_id": 7,
                    "email": "admin@example.com",
                    "role": "admin",
                    "api_key": "sk-test",
                    "api_base_url": "http://127.0.0.1:8080/v1",
                    "text_model_name": "gpt-5.5",
                    "image_model_name": "gpt-image-2",
                },
            },
        )

    client = Sub2APIClient(
        base_url="http://127.0.0.1:8080",
        exchange_secret="shared-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    payload = client.exchange_launch_token("launch-token")

    assert payload.email == "admin@example.com"
    assert payload.role == "admin"
    assert payload.api_key == "sk-test"
    assert not hasattr(payload, "default_text_model")
    assert not hasattr(payload, "default_image_model")
    assert seen_requests[0].url == httpx.URL(
        "http://127.0.0.1:8080/api/v1/onyx/exchange"
    )
    assert seen_requests[0].headers["x-sub2api-onyx-secret"] == "shared-secret"
    assert seen_requests[0].read() == b'{"token":"launch-token"}'


def test_get_models_fetches_openai_compatible_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("http://127.0.0.1:8080/v1/models")
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-5.5"},
                    {"id": "gpt-image-2", "type": "image"},
                ]
            },
        )

    client = Sub2APIClient(
        base_url="http://127.0.0.1:8080",
        exchange_secret="shared-secret",
        api_base_url="http://127.0.0.1:8080/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    models = client.get_models("sk-test")

    assert [model.id for model in models] == ["gpt-5.5", "gpt-image-2"]


def test_default_http_client_ignores_environment_proxy_settings() -> None:
    client = Sub2APIClient()

    assert client._http_client.trust_env is False
