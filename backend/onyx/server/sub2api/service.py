from onyx.auth.schemas import UserRole
from onyx.configs.app_configs import SUB2API_DEFAULT_IMAGE_MODEL
from onyx.db.models import User
from onyx.server.manage.llm.models import LLMProviderDescriptor
from onyx.server.manage.llm.models import ModelConfigurationView
from onyx.server.sub2api.models import Sub2APIModel


SUB2API_RUNTIME_PROVIDER_ID = -20001
SUB2API_RUNTIME_PROVIDER_NAME = "sub2api"
SUB2API_RUNTIME_PROVIDER_TYPE = "openai"
SUB2API_RUNTIME_PROVIDER_DISPLAY_NAME = "Sub2API"


_SUB2API_ROLE_ALIASES: dict[str, UserRole] = {
    "admin": UserRole.ADMIN,
    "administrator": UserRole.ADMIN,
    "owner": UserRole.ADMIN,
    "basic": UserRole.BASIC,
    "member": UserRole.BASIC,
    "user": UserRole.BASIC,
    "curator": UserRole.CURATOR,
    "global_curator": UserRole.GLOBAL_CURATOR,
    "limited": UserRole.LIMITED,
}


def map_sub2api_role_to_onyx_role(role: str | None) -> UserRole:
    if not role:
        return UserRole.BASIC

    mapped_role = _SUB2API_ROLE_ALIASES.get(role.strip().lower())
    if mapped_role is None or not mapped_role.is_web_login():
        return UserRole.BASIC
    return mapped_role


def update_user_role_from_sub2api(user: User | object, role: str | None) -> bool:
    new_role = map_sub2api_role_to_onyx_role(role)
    if getattr(user, "role") == new_role:
        return False

    setattr(user, "role", new_role)
    return True


def filter_providers_by_sub2api_model_ids(
    providers: list[LLMProviderDescriptor] | list[object],
    allowed_model_ids: set[str],
) -> list[LLMProviderDescriptor] | list[object]:
    if not allowed_model_ids:
        return []

    filtered_providers = []
    for provider in providers:
        provider.model_configurations = [
            model_config
            for model_config in provider.model_configurations
            if model_config.is_visible and model_config.name in allowed_model_ids
        ]
        if provider.model_configurations:
            filtered_providers.append(provider)

    return filtered_providers


def find_provider_model_for_default(
    providers: list[LLMProviderDescriptor] | list[object],
    model_name: str,
) -> tuple[int, str] | None:
    if not model_name:
        return None

    for provider in providers:
        for model_config in provider.model_configurations:
            if model_config.is_visible and model_config.name == model_name:
                return provider.id, model_config.name

    return None


def is_sub2api_runtime_provider_name(provider_name: str | None) -> bool:
    return provider_name == SUB2API_RUNTIME_PROVIDER_NAME


def is_sub2api_text_model(model: Sub2APIModel) -> bool:
    if SUB2API_DEFAULT_IMAGE_MODEL and model.id == SUB2API_DEFAULT_IMAGE_MODEL:
        return False
    return (model.type or "").strip().lower() != "image"


def is_sub2api_image_model(model: Sub2APIModel) -> bool:
    if SUB2API_DEFAULT_IMAGE_MODEL and model.id == SUB2API_DEFAULT_IMAGE_MODEL:
        return True
    return (model.type or "").strip().lower() == "image"


def build_sub2api_runtime_provider(
    models: list[Sub2APIModel],
) -> LLMProviderDescriptor | None:
    model_configurations = [
        ModelConfigurationView(
            id=None,
            name=model.id,
            is_visible=True,
            max_input_tokens=None,
            supports_image_input=False,
            supports_reasoning=False,
            display_name=model.display_name or model.id,
            custom_display_name=None,
            provider_display_name=SUB2API_RUNTIME_PROVIDER_DISPLAY_NAME,
            vendor=None,
            version=None,
            region=None,
        )
        for model in models
        if is_sub2api_text_model(model)
    ]

    if not model_configurations:
        return None

    return LLMProviderDescriptor(
        id=SUB2API_RUNTIME_PROVIDER_ID,
        name=SUB2API_RUNTIME_PROVIDER_NAME,
        provider=SUB2API_RUNTIME_PROVIDER_TYPE,
        provider_display_name=SUB2API_RUNTIME_PROVIDER_DISPLAY_NAME,
        model_configurations=model_configurations,
    )


def sub2api_model_ids(models: list[Sub2APIModel]) -> set[str]:
    return {model.id for model in models}
