from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.image_gen.interfaces import ReferenceImage
from onyx.image_gen.providers.openai_img_gen import OpenAIImageGenerationProvider
from onyx.llm.cancellation import check_cancelled
from onyx.server.sub2api import app_client
from onyx.tracing.flows import LLMFlow
from onyx.tracing.llm_utils import traced_llm_call

if TYPE_CHECKING:
    from litellm.types.utils import ImageResponse


class Sub2APIImageProvider(OpenAIImageGenerationProvider):
    def __init__(self, grant: SecretStr, key_id: int, model: str) -> None:
        self._grant = grant
        self._key_id = key_id
        self.model = model
        base = urlsplit(app_client.SUB2API_BASE_URL)
        if (
            base.scheme != "https"
            or not base.hostname
            or base.username is not None
            or base.password is not None
            or base.path not in ("", "/")
            or base.query
            or base.fragment
        ):
            raise OnyxError(
                OnyxErrorCode.SERVICE_UNAVAILABLE,
                "Sub2API image gateway requires an HTTPS origin.",
            )
        self._gateway = f"https://{base.netloc}/v1/images"

    def generate_image(
        self,
        prompt: str,
        model: str,
        size: str,
        n: int,
        quality: str | None = None,
        reference_images: list[ReferenceImage] | None = None,
        **kwargs: Any,
    ) -> "ImageResponse":
        from litellm.types.utils import ImageResponse

        if model != self.model:
            raise ValueError("Image model does not match the Sub2API turn selection.")
        payload = {"model": model, "prompt": prompt, "size": size, "n": str(n)}
        if quality:
            payload["quality"] = quality
        if kwargs.get("response_format") == "b64_json":
            payload["response_format"] = "b64_json"
        check_cancelled()
        with httpx.Client(
            follow_redirects=False, trust_env=False, timeout=120.0
        ) as client:
            key = app_client.image_credential(client, self._grant, self._key_id)
            check_cancelled()
            headers = {"Authorization": f"Bearer {key.get_secret_value()}"}
            try:
                with traced_llm_call(
                    flow=LLMFlow.IMAGE_EDIT
                    if reference_images
                    else LLMFlow.IMAGE_GENERATION,
                    model=self.model,
                    provider="openai",
                    image_count=n,
                ):
                    if reference_images:
                        files = [
                            (
                                "image[]",
                                (f"reference-{index}", image.data, image.mime_type),
                            )
                            for index, image in enumerate(reference_images)
                        ]
                        response = client.post(
                            f"{self._gateway}/edits",
                            headers=headers,
                            data=payload,
                            files=files,
                        )
                    else:
                        response = client.post(
                            f"{self._gateway}/generations",
                            headers=headers,
                            json={**payload, "n": n},
                        )
                    response.raise_for_status()
                    return ImageResponse.model_validate(response.json())
            except httpx.HTTPStatusError:
                raise RuntimeError("Sub2API rejected the image request.") from None
            except (httpx.HTTPError, ValueError):
                raise RuntimeError(
                    "The Sub2API image result could not be confirmed. Check usage before trying again."
                ) from None
