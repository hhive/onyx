from onyx.configs.app_configs import SUB2API_DEFAULT_IMAGE_MODEL
from onyx.configs.app_configs import SUB2API_INTEGRATION_ENABLED
from onyx.image_gen.interfaces import ImageGenerationProviderCredentials
from onyx.server.sub2api.client import resolve_sub2api_api_base_url


def is_sub2api_image_generation_configured() -> bool:
    return SUB2API_INTEGRATION_ENABLED and bool(SUB2API_DEFAULT_IMAGE_MODEL)


def build_sub2api_image_credentials(credential: object) -> ImageGenerationProviderCredentials:
    return ImageGenerationProviderCredentials(
        api_key=credential.api_key.get_value(apply_mask=False),
        api_base=resolve_sub2api_api_base_url(),
    )
