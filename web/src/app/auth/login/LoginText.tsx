"use client";

import React, { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import Text from "@/refresh-components/texts/Text";
import { APP_DISPLAY_NAME } from "@/lib/constants";

export default function LoginText() {
  const settings = useContext(SettingsContext);
  return (
    <div className="w-full flex flex-col ">
      <Text as="p" headingH2 text05>
        Welcome to{" "}
        {(settings && settings?.enterpriseSettings?.application_name) ||
          APP_DISPLAY_NAME}
      </Text>
      <Text as="p" text03 mainUiMuted>
        Your open source AI platform for work
      </Text>
    </div>
  );
}
