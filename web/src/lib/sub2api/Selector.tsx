"use client";

import { Button, InputSingleSelect, Text } from "@opal/components";
import { Section } from "@opal/layouts";
import { useTranslations } from "next-intl";
import type { Sub2APISelectorState } from "@/lib/sub2api/hooks";

export function Sub2APISelector({ state }: { state: Sub2APISelectorState }) {
  const t = useTranslations("sub2apiSelector");

  function platformName(platform: string) {
    return platform === "composite" ? t("composite") : platform;
  }

  function keyStatus(status: string) {
    switch (status) {
      case "disabled":
      case "expired":
      case "quota_exhausted":
      case "group_unavailable":
      case "ip_restricted":
        return t(`status.${status}`);
      default:
        return t("unavailableKey");
    }
  }
  return (
    <Section alignItems="stretch" gap={2} width="full">
      {state.authorized && (
        <>
          <InputSingleSelect
            search
            value={state.keyID === null ? "" : String(state.keyID)}
            onValueChange={state.selectKey}
            placeholder={t("key")}
            options={state.keys.map((key) => ({
              value: String(key.id),
              title: key.name || key.mask,
              description: [
                key.mask,
                key.group_name,
                platformName(key.platform),
              ]
                .filter(Boolean)
                .join(" · "),
              suffix: key.selectable ? undefined : keyStatus(key.status),
              disabled: !key.selectable,
            }))}
          />
          {state.keyID !== null && (
            <>
              {state.platform && (
                <Text as="p">
                  {t("platform", { platform: platformName(state.platform) })}
                </Text>
              )}
              <InputSingleSelect
                search
                value={state.modelID}
                onValueChange={state.selectModel}
                placeholder={t("model")}
                options={state.models.map((model) => ({
                  value: model.id,
                  title: model.id,
                }))}
              />
            </>
          )}
        </>
      )}
      {state.loading && <Text as="p">{t("loading")}</Text>}
      {!state.loading &&
        !state.error &&
        state.authorized &&
        state.keys.length === 0 && <Text as="p">{t("empty")}</Text>}
      {!state.loading && !state.error && !state.authorized && (
        <Text as="p">{t("signIn")}</Text>
      )}
      {state.error && (
        <>
          <Text as="p">{t("failed")}</Text>
          <Button onClick={state.retry}>{t("retry")}</Button>
        </>
      )}
    </Section>
  );
}
