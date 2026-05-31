"use client";

import React, { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import Text from "@/refresh-components/texts/Text";

export default function LoginText() {
  const settings = useContext(SettingsContext);
  return (
    <div className="w-full flex flex-col ">
      <Text as="p" headingH2 text05>
        欢迎使用{" "}
        {(settings && settings?.enterpriseSettings?.application_name) ||
          "小逆talk"}
      </Text>
      <Text as="p" text03 mainUiMuted>
        连接你的知识、模型和创作工具
      </Text>
    </div>
  );
}
