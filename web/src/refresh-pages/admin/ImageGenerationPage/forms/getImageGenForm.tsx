import React from "react";
import { ImageGenFormBaseProps } from "@/refresh-pages/admin/ImageGenerationPage/forms/types";
import { OpenAIImageGenForm } from "@/refresh-pages/admin/ImageGenerationPage/forms/OpenAIImageGenForm";
import { OpenAICompatibleImageGenForm } from "@/refresh-pages/admin/ImageGenerationPage/forms/OpenAICompatibleImageGenForm";
import { AzureImageGenForm } from "@/refresh-pages/admin/ImageGenerationPage/forms/AzureImageGenForm";
import { VertexImageGenForm } from "@/refresh-pages/admin/ImageGenerationPage/forms/VertexImageGenForm";

const OPENAI_COMPATIBLE_IMAGE_PROVIDER_ID = "openai_compatible_custom";

/**
 * Factory function that routes to the correct provider-specific form
 * based on the imageProvider.provider_name.
 */
export function getImageGenForm(props: ImageGenFormBaseProps): React.ReactNode {
  if (
    props.imageProvider.image_provider_id === OPENAI_COMPATIBLE_IMAGE_PROVIDER_ID
  ) {
    return <OpenAICompatibleImageGenForm {...props} />;
  }

  const providerName = props.imageProvider.provider_name;

  switch (providerName) {
    case "openai":
      return <OpenAIImageGenForm {...props} />;
    case "azure":
      return <AzureImageGenForm {...props} />;
    case "vertex_ai":
      return <VertexImageGenForm {...props} />;
    default:
      // Fallback to OpenAI form for unknown providers
      console.warn(
        `Unknown image provider: ${providerName}, falling back to OpenAI form`
      );
      return <OpenAIImageGenForm {...props} />;
  }
}
