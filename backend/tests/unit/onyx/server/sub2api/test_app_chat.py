import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from starlette.requests import Request

from onyx.error_handling.exceptions import OnyxError
from onyx.llm.model_request import UserMessage
from onyx.server.sub2api import app_client, chat
from onyx.server.sub2api.app_api import valid_origin
from onyx.server.sub2api.models import AppGrant, KeyModels, ModelEntry, Sub2APISelection


def test_origin_is_exact_https_and_same_site() -> None:
    source = "https://portal.example.com"
    target = "https://chat.portal.example.com"
    assert valid_origin([source], source, target)
    assert not valid_origin([source, source], source, target)
    assert not valid_origin(["https://evil.portal.example.com"], source, target)
    assert not valid_origin([source], source, "https://chat.example.net")
    assert not valid_origin([source], source, "http://chat.portal.example.com")


@pytest.mark.asyncio
async def test_same_model_stream_routes_to_selected_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[str, str | None, str | None, str | None, str]] = []

    class FakeGateway(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(
                (
                    self.path,
                    self.headers.get("Authorization"),
                    self.headers.get(app_client.APP_SECRET_HEADER),
                    self.headers.get(app_client.KEY_ID_HEADER),
                    body["model"],
                )
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(
                b'data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":1,'
                b'"model":"same","choices":[{"index":0,"delta":{"content":"hello"},'
                b'"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
            )

    with ThreadingHTTPServer(("127.0.0.1", 0), FakeGateway) as gateway:
        thread = Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setattr(
                app_client,
                "SUB2API_BASE_URL",
                f"http://127.0.0.1:{gateway.server_port}",
            )
            monkeypatch.setattr(app_client, "SUB2API_APP_ID", "onyx")
            monkeypatch.setattr(app_client, "SUB2API_APP_SECRET", "test-secret")
            monkeypatch.setattr(app_client, "SUB2API_INTEGRATION_ENABLED", True)
            monkeypatch.setattr(
                chat,
                "require_grant",
                AsyncMock(
                    return_value=AppGrant(
                        user_id=1, grant_token=SecretStr("test-grant")
                    )
                ),
            )
            monkeypatch.setattr(
                app_client,
                "key_models",
                AsyncMock(
                    return_value=KeyModels(
                        object="list", platform="openai", data=[ModelEntry(id="same")]
                    )
                ),
            )
            request = Request({"type": "http"})
            for key_id in (10, 20):
                model = await chat.selected_chat_model(
                    request,
                    MagicMock(),
                    Sub2APISelection(key_id=key_id, model_id="same"),
                )
                assert list(model.stream_raw([UserMessage(content="hello")]))
            with pytest.raises(OnyxError):
                await chat.selected_chat_model(
                    request,
                    MagicMock(),
                    Sub2APISelection(key_id=10, model_id="another"),
                )
        finally:
            gateway.shutdown()
            thread.join()
    assert received == [
        (
            "/api/v1/app-integrations/onyx/chat/completions",
            "Bearer test-grant",
            "test-secret",
            str(key_id),
            "same",
        )
        for key_id in (10, 20)
    ]
