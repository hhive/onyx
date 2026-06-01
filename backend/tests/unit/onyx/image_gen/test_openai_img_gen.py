from unittest.mock import patch

from onyx.image_gen.interfaces import ImageGenerationProviderCredentials
from onyx.image_gen.providers.openai_img_gen import OpenAIImageGenerationProvider


def test_openai_image_generation_provider_forwards_additional_headers() -> None:
    provider = OpenAIImageGenerationProvider.build_from_credentials(
        ImageGenerationProviderCredentials(
            api_key="sk-test",
            api_base="http://127.0.0.1:8080/v1",
            additional_headers={"User-Agent": "Mozilla/5.0"},
        )
    )

    with patch("litellm.image_generation") as mock_image_generation:
        mock_image_generation.return_value.data = []
        provider.generate_image(
            prompt="draw a cat",
            model="gpt-image-2",
            size="1024x1024",
            n=1,
        )

    assert mock_image_generation.call_args.kwargs["extra_headers"] == {
        "User-Agent": "Mozilla/5.0"
    }
