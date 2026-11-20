"use client";

import React from "react";
import { useTranslations } from "next-intl";
import * as Yup from "yup";
import { FormikField } from "@/refresh-components/form/FormikField";
import { FormField } from "@/refresh-components/form/FormField";
import { InputTypeIn, InputPasswordTypeIn } from "@opal/components";
import { ImageGenFormWrapper } from "@/views/admin/ImageGenerationPage/forms/ImageGenFormWrapper";
import {
  ImageGenFormBaseProps,
  ImageGenFormChildProps,
  ImageGenSubmitPayload,
} from "@/views/admin/ImageGenerationPage/forms/types";
import { ImageGenerationCredentials } from "@/views/admin/ImageGenerationPage/svc";
import { ImageProvider } from "@/views/admin/ImageGenerationPage/constants";

interface OpenAICompatibleFormValues {
  model_name: string;
  api_base: string;
  api_key: string;
}

const initialValues: OpenAICompatibleFormValues = {
  model_name: "",
  api_base: "",
  api_key: "",
};

const validationSchema = Yup.object().shape({
  model_name: Yup.string().required("Model Name is required"),
  api_base: Yup.string()
    .url("Base URL must be a valid URL")
    .required("Base URL is required"),
  api_key: Yup.string().required("API Key is required"),
});

function OpenAICompatibleFormFields(
  props: ImageGenFormChildProps<OpenAICompatibleFormValues>
) {
  const t = useTranslations("admin.imageGeneration");
  const {
    apiStatus,
    showApiMessage,
    errorMessage,
    disabled,
    isLoadingCredentials,
    resetApiState,
    imageProvider,
  } = props;

  return (
    <>
      <FormikField<string>
        name="model_name"
        render={(field, _helper, meta, state) => (
          <FormField name="model_name" state={state} className="w-full">
            <FormField.Label>{t("form.customModelName.label")}</FormField.Label>
            <FormField.Control>
              <InputTypeIn
                {...field}
                onChange={(e) => {
                  field.onChange(e);
                  resetApiState();
                }}
                placeholder={
                  isLoadingCredentials ? "Loading..." : "Enter image model name"
                }
                variant={disabled ? "disabled" : undefined}
              />
            </FormField.Control>
            <FormField.Message
              messages={{
                idle: "Enter the model name expected by your OpenAI-compatible image endpoint.",
                error: meta.error,
              }}
            />
          </FormField>
        )}
      />

      <FormikField<string>
        name="api_base"
        render={(field, _helper, meta, state) => (
          <FormField name="api_base" state={state} className="w-full">
            <FormField.Label>{t("form.customBaseURL.label")}</FormField.Label>
            <FormField.Control>
              <InputTypeIn
                {...field}
                onChange={(e) => {
                  field.onChange(e);
                  resetApiState();
                }}
                placeholder={
                  isLoadingCredentials
                    ? "Loading..."
                    : "https://your-image-gateway.example.com/v1"
                }
                variant={disabled ? "disabled" : undefined}
              />
            </FormField.Control>
            <FormField.Message
              messages={{
                idle: "Enter the base URL for an endpoint compatible with OpenAI Images API.",
                error: meta.error,
              }}
            />
          </FormField>
        )}
      />

      <FormikField<string>
        name="api_key"
        render={(field, _helper, meta, state) => (
          <FormField
            name="api_key"
            state={apiStatus === "error" ? "error" : state}
            className="w-full"
          >
            <FormField.Label>{t("form.apiKey.label")}</FormField.Label>
            <FormField.Control>
              <InputPasswordTypeIn
                {...field}
                onChange={(e) => {
                  field.onChange(e);
                  resetApiState();
                }}
                placeholder={
                  isLoadingCredentials ? "Loading..." : "Enter your API key"
                }
                disabled={disabled}
                error={apiStatus === "error"}
              />
            </FormField.Control>
            {showApiMessage ? (
              <FormField.APIMessage
                state={apiStatus}
                messages={{
                  loading: `Testing API key with ${imageProvider.title}...`,
                  success: "API key is valid. Configuration saved.",
                  error: errorMessage || "Invalid API key",
                }}
              />
            ) : (
              <FormField.Message
                messages={{
                  idle: "Enter the API key for your OpenAI-compatible endpoint.",
                  error: meta.error,
                }}
              />
            )}
          </FormField>
        )}
      />
    </>
  );
}

function getInitialValuesFromCredentials(
  credentials: ImageGenerationCredentials,
  imageProvider: ImageProvider,
  existingConfigModelName?: string
): Partial<OpenAICompatibleFormValues> {
  return {
    model_name: existingConfigModelName || imageProvider.model_name || "",
    api_base: credentials.api_base || "",
    api_key: credentials.api_key || "",
  };
}

function transformValues(
  values: OpenAICompatibleFormValues
): ImageGenSubmitPayload {
  return {
    modelName: values.model_name,
    provider: "openai",
    apiKey: values.api_key,
    apiBase: values.api_base,
  };
}

export function OpenAICompatibleImageGenForm(props: ImageGenFormBaseProps) {
  const { imageProvider, existingConfig } = props;
  const t = useTranslations("admin.imageGeneration");

  return (
    <ImageGenFormWrapper<OpenAICompatibleFormValues>
      {...props}
      title={
        existingConfig
          ? `Edit ${imageProvider.title}`
          : `Connect ${imageProvider.title}`
      }
      description={t(imageProvider.descriptionKey)}
      initialValues={initialValues}
      validationSchema={validationSchema}
      getInitialValuesFromCredentials={(credentials) =>
        getInitialValuesFromCredentials(
          credentials,
          imageProvider,
          existingConfig?.model_name
        )
      }
      transformValues={transformValues}
    >
      {(childProps) => <OpenAICompatibleFormFields {...childProps} />}
    </ImageGenFormWrapper>
  );
}
