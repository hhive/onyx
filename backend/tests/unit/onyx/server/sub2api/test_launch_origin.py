from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

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
    monkeypatch.setattr(app_api, "SUB2API_LAUNCH_ORIGIN", "https://primary.test,https://alias.test")
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
    assert b'test-ticket&quot;&gt;&lt;img&gt;' in response.body
    assert b'test-ticket"><img>' not in response.body

    await app_api.finish_launch(
        make_request("/sub2api/launch/finish", "https://chat.primary.test"),
        "test-ticket",
        None,
        None,
        None,
    )
    complete.assert_awaited_once()
