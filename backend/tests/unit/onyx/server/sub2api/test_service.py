from onyx.auth.schemas import UserRole
from onyx.server.sub2api.models import Sub2APIModel
from onyx.server.sub2api.service import build_sub2api_runtime_provider
from onyx.server.sub2api.service import map_sub2api_role_to_onyx_role
from onyx.server.sub2api.service import filter_providers_by_sub2api_model_ids
from onyx.server.sub2api.service import find_provider_model_for_default
from onyx.server.sub2api.service import is_sub2api_runtime_provider_name
from onyx.server.sub2api.service import SUB2API_RUNTIME_PROVIDER_NAME
from onyx.server.sub2api.service import update_user_role_from_sub2api


def test_map_sub2api_role_to_onyx_role_preserves_admin() -> None:
    assert map_sub2api_role_to_onyx_role("admin") == UserRole.ADMIN


def test_map_sub2api_role_to_onyx_role_defaults_to_basic_for_member() -> None:
    assert map_sub2api_role_to_onyx_role("member") == UserRole.BASIC


def test_map_sub2api_role_to_onyx_role_does_not_create_non_web_login_roles() -> None:
    assert map_sub2api_role_to_onyx_role("slack_user") == UserRole.BASIC
    assert map_sub2api_role_to_onyx_role("ext_perm_user") == UserRole.BASIC


class FakeUser:
    def __init__(self, role: UserRole) -> None:
        self.role = role


def test_update_user_role_from_sub2api_mutates_user_when_role_changes() -> None:
    user = FakeUser(UserRole.BASIC)

    assert update_user_role_from_sub2api(user, "admin") is True
    assert user.role == UserRole.ADMIN


def test_update_user_role_from_sub2api_skips_when_role_unchanged() -> None:
    user = FakeUser(UserRole.BASIC)

    assert update_user_role_from_sub2api(user, "member") is False
    assert user.role == UserRole.BASIC


class FakeModelConfiguration:
    def __init__(self, name: str, is_visible: bool = True) -> None:
        self.name = name
        self.is_visible = is_visible


class FakeProviderDescriptor:
    def __init__(self, names: list[str]) -> None:
        self.model_configurations = [FakeModelConfiguration(name) for name in names]


def test_filter_providers_by_sub2api_model_ids_keeps_intersection() -> None:
    provider = FakeProviderDescriptor(["gpt-5.5", "blocked-model"])

    filtered = filter_providers_by_sub2api_model_ids([provider], {"gpt-5.5"})

    assert filtered == [provider]
    assert [model.name for model in provider.model_configurations] == ["gpt-5.5"]


def test_filter_providers_by_sub2api_model_ids_drops_empty_providers() -> None:
    provider = FakeProviderDescriptor(["blocked-model"])

    assert filter_providers_by_sub2api_model_ids([provider], {"gpt-5.5"}) == []


def test_find_provider_model_for_default_returns_matching_provider_and_model() -> None:
    provider = FakeProviderDescriptor(["gpt-5.5", "gpt-image-2"])
    provider.id = 9

    match = find_provider_model_for_default([provider], "gpt-image-2")

    assert match == (9, "gpt-image-2")


def test_find_provider_model_for_default_ignores_blank_or_missing_model() -> None:
    provider = FakeProviderDescriptor(["gpt-5.5"])
    provider.id = 9

    assert find_provider_model_for_default([provider], "") is None
    assert find_provider_model_for_default([provider], "missing") is None


def test_build_sub2api_runtime_provider_exposes_text_models_only(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "onyx.server.sub2api.service.SUB2API_DEFAULT_IMAGE_MODEL",
        "gpt-image-2",
    )

    provider = build_sub2api_runtime_provider(
        [
            Sub2APIModel(id="gpt-5.5", display_name="GPT 5.5"),
            Sub2APIModel(id="gpt-image-2"),
        ]
    )

    assert provider is not None
    assert provider.name == SUB2API_RUNTIME_PROVIDER_NAME
    assert provider.provider == "openai"
    assert provider.provider_display_name == "Sub2API"
    assert [model.name for model in provider.model_configurations] == ["gpt-5.5"]
    assert provider.model_configurations[0].display_name == "GPT 5.5"


def test_build_sub2api_runtime_provider_drops_image_only_catalog(monkeypatch) -> None:
    monkeypatch.setattr(
        "onyx.server.sub2api.service.SUB2API_DEFAULT_IMAGE_MODEL",
        "gpt-image-2",
    )

    assert (
        build_sub2api_runtime_provider(
            [Sub2APIModel(id="gpt-image-2")]
        )
        is None
    )


def test_is_sub2api_runtime_provider_name_matches_only_runtime_name() -> None:
    assert is_sub2api_runtime_provider_name("sub2api") is True
    assert is_sub2api_runtime_provider_name("openai") is False
    assert is_sub2api_runtime_provider_name(None) is False
