import { render, screen } from "@tests/setup/test-utils";
import { FoldableLogo, Logo, SidebarWordmark } from "./Logo";

const mockSettings = jest.fn();

jest.mock("@/lib/settings/hooks", () => ({
  useSettings: () => mockSettings(),
}));

it("uses the local brand by default", () => {
  mockSettings.mockReturnValue({});
  render(
    <>
      <Logo />
      <FoldableLogo />
      <SidebarWordmark />
    </>
  );
  expect(screen.getAllByText("小逆talk")).toHaveLength(2);
  for (const image of screen.getAllByRole("img")) {
    expect(image).toHaveAttribute("src", "/xiaoni-talk.ico");
  }
  expect(screen.queryByText("Powered by Onyx")).not.toBeInTheDocument();
});

it("retains a custom theme's name and logo display style", () => {
  mockSettings.mockReturnValue({
    enterprise: {
      application_name: "Team Chat",
      logo_display_style: "name_only",
    },
    logoUrl: "/api/enterprise-settings/logo",
  });
  render(<FoldableLogo />);
  expect(screen.getByText("Team Chat")).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
