"use client";

import { Text } from "@opal/components";
import { useTranslations } from "next-intl";
import { useSettings } from "@/lib/settings/hooks";
import {
  APP_DISPLAY_NAME,
  APP_LOGO_URL,
  DEFAULT_LOGO_SIZE_PX,
} from "@/lib/constants";
import { Section } from "@opal/layouts";
import { cn } from "@opal/utils";
import { SvgOnyxLogo, SvgOnyxLogoWordmark } from "@opal/logos";
import { IconProps } from "@opal/types";

export interface LogoProps extends IconProps {
  // Always render the real Onyx mark, ignoring the enterprise custom logo.
  // Used by Onyx-branded surfaces like Craft.
  onyxBranded?: boolean;
}

/**
 * The configured logo or the default workspace mark.
 */
export function Logo({ size, className, style, onyxBranded }: LogoProps) {
  const t = useTranslations("common");
  const resolvedSize = size ?? DEFAULT_LOGO_SIZE_PX;
  const { logoUrl } = useSettings();

  if (onyxBranded) {
    return (
      <SvgOnyxLogo
        size={resolvedSize}
        className={cn("shrink-0", className)}
        style={style}
      />
    );
  }

  return (
    <div
      className={cn(
        "aspect-square rounded-full overflow-hidden relative shrink-0",
        className
      )}
      style={{ height: resolvedSize, ...style }}
    >
      <img
        alt={t("logo.image.alt")}
        src={logoUrl || APP_LOGO_URL}
        className="object-cover object-center w-full h-full"
      />
    </div>
  );
}

export interface FoldableLogoProps extends LogoProps {
  folded?: boolean;
}

/**
 * The brand block follows the workspace's logo display style.
 */
export function FoldableLogo({
  folded,
  size,
  className,
  onyxBranded,
}: FoldableLogoProps) {
  const resolvedSize = size ?? DEFAULT_LOGO_SIZE_PX;
  const { enterprise } = useSettings();
  const logoDisplayStyle = enterprise?.logo_display_style;
  const applicationName =
    enterprise?.application_name?.trim() || APP_DISPLAY_NAME;

  if (onyxBranded) {
    return folded ? (
      <Logo onyxBranded size={resolvedSize} className={className} />
    ) : (
      <SvgOnyxLogoWordmark size={resolvedSize} className={className} />
    );
  }

  const logo = <Logo size={resolvedSize} className={className} />;

  const renderBrand = (opts: {
    includeLogo: boolean;
    includeName: boolean;
  }) => {
    return (
      <Section
        flexDirection="row"
        alignItems="start"
        gap={2}
        className="min-w-0"
      >
        {opts.includeLogo && logo}
        {!folded && (
          /* H3 text is 4px larger (28px) than the Logo icon (24px), so negative margin hack. */
          <Section
            flexDirection="column"
            alignItems="start"
            className="flex-1 -mt-0.5"
          >
            {opts.includeName && (
              <Text
                maxLines={1}
                overflowTooltip
                as="p"
                textPosition="text-start"
                font="heading-section"
                color="text-05"
              >
                {applicationName}
              </Text>
            )}
          </Section>
        )}
      </Section>
    );
  };

  return renderBrand({
    includeLogo: logoDisplayStyle !== "name_only",
    includeName: logoDisplayStyle !== "logo_only",
  });
}

/**
 * The sidebar logo follows the workspace's logo display style.
 */
export function SidebarLogoMark({ size }: { size: number }) {
  const { enterprise } = useSettings();
  if (
    enterprise?.application_name &&
    enterprise.logo_display_style === "name_only"
  ) {
    return null;
  }
  return <Logo size={size} />;
}

/**
 * The sidebar wordmark displays the workspace name.
 */
export function SidebarWordmark() {
  const { enterprise } = useSettings();
  const logoDisplayStyle = enterprise?.logo_display_style;
  const applicationName =
    enterprise?.application_name?.trim() || APP_DISPLAY_NAME;

  return (
    <Section
      flexDirection="column"
      alignItems="start"
      justifyContent="start"
      gap={0}
      height="fit"
      className="min-w-0 flex-1"
    >
      {logoDisplayStyle !== "logo_only" && (
        <Text
          maxLines={1}
          overflowTooltip
          as="p"
          textPosition="text-start"
          font="heading-section"
          color="text-05"
        >
          {applicationName}
        </Text>
      )}
    </Section>
  );
}
