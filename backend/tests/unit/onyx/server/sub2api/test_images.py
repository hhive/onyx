import pytest

from onyx.server.sub2api.models import KeyModels


def test_image_catalog_includes_capability_and_known_names() -> None:
    result = KeyModels.model_validate(
        {
            "object": "list",
            "platform": "openai",
            "data": [
                {"id": "text"},
                {"id": "custom", "capabilities": {"image_generation": True}},
                {"id": "gpt-image-2"},
            ],
        }
    )
    assert [m.id for m in result.data] == ["text"]
    assert [(m.id, m.confirmed) for m in result.image_models] == [
        ("custom", True),
        ("gpt-image-2", True),
    ]


def test_image_wire_routes_bound_key_for_generation_and_edit(monkeypatch) -> None:
    import json

    import httpx
    from pydantic import SecretStr

    from onyx.image_gen.interfaces import ReferenceImage
    from onyx.server.sub2api import app_client, images

    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/credential"):
            assert request.headers["Authorization"] == "Bearer grant"
            assert request.headers["X-Sub2API-App-Secret"] == "secret"
            return httpx.Response(200, json={"api_key": "bound-key"})
        assert request.headers["Authorization"] == "Bearer bound-key"
        assert "X-Sub2API-App-Secret" not in request.headers
        return httpx.Response(200, json={"created": 1, "data": [{"b64_json": "eA=="}]})

    class Client(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(images.httpx, "Client", Client)
    monkeypatch.setattr(app_client, "SUB2API_BASE_URL", "https://relay.example")
    monkeypatch.setattr(app_client, "SUB2API_APP_ID", "onyx")
    monkeypatch.setattr(app_client, "SUB2API_APP_SECRET", "secret")
    monkeypatch.setattr(app_client, "SUB2API_INTEGRATION_ENABLED", True)
    provider = images.Sub2APIImageProvider(SecretStr("grant"), 27, "gpt-image-2")
    provider.generate_image("generate", "gpt-image-2", "1024x1024", 1)
    provider.generate_image(
        "edit",
        "gpt-image-2",
        "1024x1024",
        1,
        reference_images=[ReferenceImage(data=b"png", mime_type="image/png")],
    )
    assert [request.url.path for request in requests] == [
        "/api/v1/app-integrations/onyx/keys/27/credential",
        "/v1/images/generations",
        "/api/v1/app-integrations/onyx/keys/27/credential",
        "/v1/images/edits",
    ]
    assert json.loads(requests[1].content)["model"] == "gpt-image-2"
    assert b'name="image[]"' in requests[3].read()


@pytest.mark.asyncio
async def test_composite_catalog_adds_unconfirmed_image_candidates(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    import httpx
    from pydantic import SecretStr

    from onyx.server.sub2api import app_client

    monkeypatch.setattr(
        app_client,
        "_request",
        AsyncMock(
            return_value=httpx.Response(
                200,
                request=httpx.Request("GET", "https://relay.example"),
                headers={app_client.KEY_PLATFORM_HEADER: "composite"},
                json={"object": "list", "data": [{"id": "gpt-image-owned"}]},
            )
        ),
    )
    monkeypatch.setattr(
        app_client,
        "iter_image_generation_models",
        lambda _: ["gpt-image-owned", "gpt-image-fallback"],
    )
    models = await app_client.key_models(SecretStr("mock"), 1)
    assert [(model.id, model.confirmed) for model in models.image_models] == [
        ("gpt-image-owned", True),
        ("gpt-image-fallback", False),
    ]
