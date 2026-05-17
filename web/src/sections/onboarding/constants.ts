import { OnboardingStep, FinalStepItemProps } from "@/interfaces/onboarding";
import { SvgGlobe, SvgImage, SvgUsers } from "@opal/icons";

type StepConfig = {
  index: number;
  title: string;
  buttonText: string;
  iconPercentage: number;
};

export const STEP_CONFIG: Record<OnboardingStep, StepConfig> = {
  [OnboardingStep.Welcome]: {
    index: 0,
    title: "花一点时间完成设置。",
    buttonText: "开始",
    iconPercentage: 10,
  },
  [OnboardingStep.Name]: {
    index: 1,
    title: "花一点时间完成设置。",
    buttonText: "下一步",
    iconPercentage: 40,
  },
  [OnboardingStep.LlmSetup]: {
    index: 2,
    title: "快完成了！连接模型后即可开始聊天。",
    buttonText: "下一步",
    iconPercentage: 70,
  },
  [OnboardingStep.Complete]: {
    index: 3,
    title: "设置已完成，可检查可选设置或直接完成。",
    buttonText: "完成设置",
    iconPercentage: 100,
  },
} as const;

export const TOTAL_STEPS = 3;

export const STEP_NAVIGATION: Record<
  OnboardingStep,
  { next?: OnboardingStep; prev?: OnboardingStep }
> = {
  [OnboardingStep.Welcome]: { next: OnboardingStep.Name },
  [OnboardingStep.Name]: {
    next: OnboardingStep.LlmSetup,
    prev: OnboardingStep.Welcome,
  },
  [OnboardingStep.LlmSetup]: {
    next: OnboardingStep.Complete,
    prev: OnboardingStep.Name,
  },
  [OnboardingStep.Complete]: { prev: OnboardingStep.LlmSetup },
};

export const FINAL_SETUP_CONFIG: FinalStepItemProps[] = [
  {
    title: "选择网页搜索服务",
    description: "允许小逆talk联网搜索信息。",
    icon: SvgGlobe,
    buttonText: "网页搜索",
    buttonHref: "/admin/configuration/web-search",
  },
  {
    title: "启用图片生成",
    description: "设置可在聊天中创建图片的模型。",
    icon: SvgImage,
    buttonText: "图片生成",
    buttonHref: "/admin/configuration/image-generation",
  },
  {
    title: "邀请团队",
    description: "管理团队用户和权限",
    icon: SvgUsers,
    buttonText: "管理用户",
    buttonHref: "/admin/users",
  },
];
