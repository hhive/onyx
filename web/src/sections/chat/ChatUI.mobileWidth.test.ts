import fs from "fs";
import path from "path";

describe("ChatUI mobile message width", () => {
  it("keeps normal chat messages within narrow mobile viewports", () => {
    const source = fs.readFileSync(path.join(__dirname, "ChatUI.tsx"), "utf8");

    const layout = fs.readFileSync(
      path.join(__dirname, "../../lib/chat/layout.ts"),
      "utf8"
    );
    expect(source).toContain("const msgWidth = CHAT_COLUMN_WIDTH;");
    expect(layout).toContain(
      '"md:max-w-[var(--app-chat-column-width,var(--width-chat-message-max))]"'
    );
  });
});
