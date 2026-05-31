from onyx.server.auth_check import PUBLIC_ENDPOINT_SPECS
from onyx.server.sub2api.api import legacy_router
from onyx.server.sub2api.api import router


def test_sub2api_callback_is_public_endpoint() -> None:
    assert ("/auth/sub2api/callback", {"GET"}) in PUBLIC_ENDPOINT_SPECS


def test_sub2api_legacy_exchange_is_public_endpoint() -> None:
    assert ("/sub2api/exchange", {"GET"}) in PUBLIC_ENDPOINT_SPECS


def test_sub2api_login_routes_match_supported_launch_urls() -> None:
    route_paths = {route.path for route in router.routes}
    legacy_route_paths = {route.path for route in legacy_router.routes}

    assert "/auth/sub2api/callback" in route_paths
    assert "/sub2api/exchange" in legacy_route_paths
