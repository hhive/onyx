from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from onyx.server.auth_check import check_router_auth
from onyx.server.sub2api import app_api


def make_request(path: str, origin: str) -> Request:
    return Request(
        {
            "type": "http",
            "path": path,
            "headers": [(b"origin", origin.encode())],
        }
    )


@pytest.mark.asyncio
async def test_cross_site_launch_posts_same_ticket_from_onyx_before_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_api, "SUB2API_LAUNCH_ORIGIN", "https://primary.test,https://alias.test"
    )
    monkeypatch.setattr(app_api, "WEB_DOMAIN", "https://chat.primary.test")
    complete = AsyncMock()
    monkeypatch.setattr(app_api, "_complete_launch", complete, raising=False)

    response = await app_api.launch(
        make_request("/sub2api/launch", "https://alias.test"),
        'test-ticket"><img>',
        None,
        None,
        None,
    )
    complete.assert_not_awaited()
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "same-origin"
    assert b'action="/api/sub2api/launch/finish"' in response.body
    assert b"test-ticket&quot;&gt;&lt;img&gt;" in response.body
    assert b'test-ticket"><img>' not in response.body

    await app_api.finish_launch(
        make_request("/sub2api/launch/finish", "https://chat.primary.test"),
        "test-ticket",
        None,
        None,
        None,
    )
    complete.assert_awaited_once()


def test_sub2api_router_passes_startup_auth_check() -> None:
    app = FastAPI(openapi_url=None)
    app.include_router(app_api.router)
    check_router_auth(app)


@pytest.mark.parametrize(
    ("referer", "expected_site"),
    [
        ("https://primary.test/", "primary.test"),
        ("https://alias.test/keys?page=2", "alias.test"),
        ("https://alias.test.evil.test/", "primary.test"),
        ("https://alias.test@evil.test/", "primary.test"),
        (None, "primary.test"),
    ],
)
def test_legacy_launch_returns_to_sub2api_without_forwarding_token(
    monkeypatch: pytest.MonkeyPatch, referer: str | None, expected_site: str
) -> None:
    monkeypatch.setattr(
        app_api, "SUB2API_LAUNCH_ORIGIN", "https://primary.test,https://alias.test"
    )
    complete = AsyncMock()
    monkeypatch.setattr(app_api, "_complete_launch", complete)
    app = FastAPI()
    app.include_router(app_api.router)
    headers = {"Referer": referer} if referer is not None else {}

    with TestClient(app) as client:
        for _ in range(2):
            response = client.get(
                "/sub2api/launch?token=legacy-ticket",
                headers=headers,
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == f"https://{expected_site}/keys"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert "set-cookie" not in response.headers
            assert "legacy-ticket" not in response.text
    complete.assert_not_called()


def test_legacy_launch_requires_a_configured_sub2api_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_api, "SUB2API_LAUNCH_ORIGIN", "")
    app = FastAPI()
    app.include_router(app_api.router)

    with TestClient(app) as client:
        response = client.get("/sub2api/launch", follow_redirects=False)

    assert response.status_code == 404
    assert "location" not in response.headers
