import fs from "fs";
import path from "path";

describe("ChatUI mobile message width", () => {
  it("keeps normal chat messages within narrow mobile viewports", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "ChatUI.tsx"),
      "utf8"
    );

    expect(source).toContain(
      'const MSG_MAX_W = "max-w-[720px] min-w-0 sm:min-w-[400px]"'
    );
  });
});
