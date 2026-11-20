from typing import Any

from pydantic import BaseModel, Field, SecretStr, model_validator


class Sub2APIExchangeUser(BaseModel):
    id: int
    email: str
    username: str


class Sub2APICredentialPayload(BaseModel):
    api_key_id: int
    api_key: str
    api_base_url: str
    text_model_name: str
    image_model_name: str


class Sub2APILaunchExchangeResponse(BaseModel):
    user: Sub2APIExchangeUser
    credential: Sub2APICredentialPayload

    @classmethod
    def from_sub2api_payload(
        cls,
        payload: dict,
    ) -> "Sub2APILaunchExchangeResponse":
        return cls(
            user=Sub2APIExchangeUser(
                id=payload["user_id"],
                email=payload["email"],
                username=payload["username"],
            ),
            credential=Sub2APICredentialPayload(
                api_key_id=payload["api_key_id"],
                api_key=payload["api_key"],
                api_base_url=payload["api_base_url"],
                text_model_name=payload["text_model_name"],
                image_model_name=payload["image_model_name"],
            ),
        )


class AppExchange(BaseModel):
    user_id: int = Field(gt=0)
    email: str
    username: str
    grant_token: SecretStr
    expires_in: int = Field(gt=0, le=28800)
    scopes: list[str]


class AppGrant(BaseModel):
    user_id: int = Field(gt=0)
    grant_token: SecretStr


class KeyEntry(BaseModel):
    id: int
    name: str
    mask: str
    group_id: int | None
    group_name: str | None
    platform: str | None
    status: str
    selectable: bool


class KeyPage(BaseModel):
    items: list[KeyEntry]
    page: int
    page_size: int
    total: int


class ModelEntry(BaseModel):
    id: str
    object: str = "model"
    owned_by: str | None = None
    display_name: str | None = None
    created: int | str | None = None
    type: str | None = None
    capabilities: list[str] | dict[str, bool] | str | None = None
    model_config = {"extra": "ignore"}


def _is_sub2api_embedding_model(model_id: str, model_type: str | None = None) -> bool:
    """Filter embedding models without importing LiteLLM on the Sub2API list path."""
    if isinstance(model_type, str) and model_type.lower() == "embedding":
        return True

    model_id_lower = model_id.lower()
    return any(
        pattern in model_id_lower
        for pattern in (
            "embed",
            "embedding",
            "bge-",
            "e5-",
            "jina-embeddings",
            "mxbai-embed",
            "text-similarity",
            "text-search",
            "voyage-",
        )
    )


def _model_capability_values(item: dict[str, Any]) -> set[str]:
    capabilities = item.get("capabilities") or item.get("capability") or []
    if isinstance(capabilities, str):
        capabilities = [capabilities]
    if isinstance(capabilities, dict):
        capabilities = [
            key for key, enabled in capabilities.items() if enabled is not False
        ]
    if not isinstance(capabilities, list):
        return set()

    return {str(capability).lower().replace("-", "_") for capability in capabilities}


def _is_sub2api_image_generation_model(
    model_id: str,
    model_type: str | None = None,
    item: dict[str, Any] | None = None,
) -> bool:
    """Filter image generation models out of the chat model selector."""
    type_value = (
        model_type.lower().replace("-", "_") if isinstance(model_type, str) else ""
    )
    if type_value in {
        "image",
        "images",
        "image_generation",
        "image_generation_model",
    }:
        return True

    if item is not None:
        capabilities = _model_capability_values(item)
        if capabilities.intersection(
            {
                "image_generation",
                "generate_image",
                "image_output",
                "text_to_image",
            }
        ):
            return True

    model_id_lower = model_id.lower()
    return any(
        pattern in model_id_lower
        for pattern in (
            "gpt-image",
            "dall-e",
            "imagen",
            "flux",
            "stable-diffusion",
            "sdxl",
            "midjourney",
            "recraft",
            "ideogram",
            "seedream",
            "kolors",
            "wanx",
        )
    )


class ImageModelEntry(ModelEntry):
    confirmed: bool


class ImageCredential(BaseModel):
    api_key: SecretStr


class KeyModels(BaseModel):
    object: str
    data: list[ModelEntry]
    platform: str
    image_models: list[ImageModelEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def chat_models(self) -> "KeyModels":
        self.image_models.extend(
            ImageModelEntry(**model.model_dump(), confirmed=True)
            for model in self.data
            if _is_sub2api_image_generation_model(
                model.id, model.type, model.model_dump()
            )
        )
        image_ids = {model.id for model in self.image_models}
        self.data = [
            model
            for model in self.data
            if not _is_sub2api_embedding_model(model.id, model.type)
            and model.id not in image_ids
            and model.type
            not in {"video", "audio", "transcription", "moderation", "rerank"}
        ]
        return self


class Sub2APISelection(BaseModel):
    key_id: int = Field(gt=0)
    model_id: str = Field(min_length=1, max_length=300)
    image_model_id: str | None = Field(default=None, min_length=1, max_length=300)
