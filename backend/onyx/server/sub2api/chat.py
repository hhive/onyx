from fastapi import Request

from onyx.configs.app_configs import SUB2API_APP_SECRET
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import User
from onyx.db.sub2api_user_credentials import get_sub2api_credential_for_user
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.llm.constants import LlmProviderNames
from onyx.llm.model_capabilities import parse_openai_gpt_version
from onyx.llm.multi_llm import LitellmLLM
from onyx.server.sub2api import app_client
from onyx.server.sub2api.app_api import require_grant
from onyx.server.sub2api.images import Sub2APIImageProvider
from onyx.server.sub2api.models import Sub2APISelection
from onyx.utils.logger import setup_logger

logger = setup_logger()


class Sub2APIChatLLM(LitellmLLM):
    _retry_first_chunk = False
    image_provider: Sub2APIImageProvider | None = None

    def _allow_chat_tools_reasoning_none(self) -> bool:
        version = parse_openai_gpt_version(self.config.model_name)
        return version is None or version < (6, 0)

    def redact_error(self, text: str) -> str:
        redacted = super().redact_error(text)
        secret = app_client.app_headers()[app_client.APP_SECRET_HEADER]
        return redacted.replace(secret, "[REDACTED]") if secret else redacted


def requires_sub2api_selection(user: User) -> bool:
    if not SUB2API_APP_SECRET or user.is_anonymous:
        return False
    with get_session_with_current_tenant() as db_session:
        binding = get_sub2api_credential_for_user(db_session, user.id)
        return binding is not None and binding.sub2api_user_id > 0


async def selected_chat_model(
    request: Request, user: User, selection: Sub2APISelection
) -> Sub2APIChatLLM:
    grant = await require_grant(request, user)
    models = await app_client.key_models(grant.grant_token, selection.key_id)
    if selection.model_id not in {model.id for model in models.data}:
        raise OnyxError(
            OnyxErrorCode.UNAUTHORIZED, "The Sub2API model is unavailable for this key."
        )

    headers = app_client.app_headers()
    headers[app_client.KEY_ID_HEADER] = str(selection.key_id)
    logger.info(
        "Sub2API selected chat model key_id=%d platform=%s",
        selection.key_id,
        models.platform,
    )
    llm = Sub2APIChatLLM(
        model_provider=LlmProviderNames.OPENAI_COMPATIBLE,
        model_name=selection.model_id,
        api_key=grant.grant_token.get_secret_value(),
        max_input_tokens=8192,
        model_kwargs={"base_url": app_client.app_endpoint(), "num_retries": 0},
        extra_headers=headers,
        supports_images=False,
    )
    if selection.image_model_id:
        if selection.image_model_id not in {model.id for model in models.image_models}:
            raise OnyxError(
                OnyxErrorCode.UNAUTHORIZED,
                "The Sub2API image model is unavailable for this key.",
            )
        llm.image_provider = Sub2APIImageProvider(
            grant.grant_token, selection.key_id, selection.image_model_id
        )
    return llm
