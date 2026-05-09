import fs from "fs";
import path from "path";

describe("AppPage mobile new-session model selector layout", () => {
  it("keeps the welcome-row model selector desktop-only", () => {
    const source = fs.readFileSync(path.join(__dirname, "AppPage.tsx"), "utf8");

    expect(source).toContain('className="hidden sm:block"');
  });

  it("shows the input-area model selector on chat sessions and mobile new sessions", () => {
    const source = fs.readFileSync(path.join(__dirname, "AppPage.tsx"), "utf8");

    expect(source).toContain("(appFocus.isChat() || appFocus.isNewSession())");
    expect(source).toContain('"pb-1"');
    expect(source).toContain('appFocus.isNewSession() && "sm:hidden"');
  });
});

describe("ModelSelector mobile width behavior", () => {
  it("allows model pills to shrink instead of forcing horizontal overflow", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "../refresh-components/popovers/ModelSelector.tsx"),
      "utf8"
    );

    expect(source).toContain(
      'className="flex min-w-0 max-w-full items-center justify-end gap-1 p-1"'
    );
    expect(source).toContain(
      'className="flex min-w-0 items-center overflow-hidden"'
    );
    expect(source).toContain(
      'className="flex min-w-0 max-w-[12rem] items-center overflow-hidden"'
    );
    expect(source).toContain('width="full"');
  });
});
