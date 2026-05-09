import fs from "fs";
import path from "path";

describe("AppInputBar mobile controls layout", () => {
  it("keeps bottom controls from forcing horizontal page overflow", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "AppInputBar.tsx"),
      "utf8"
    );

    expect(source).toContain(
      '"flex justify-between items-center w-full min-w-0 gap-1 overflow-hidden"'
    );
    expect(source).toContain('"flex min-w-0 flex-1 flex-row items-center"');
    expect(source).toContain('"flex min-w-0 flex-row items-center overflow-hidden"');
    expect(source).toContain('"flex shrink-0 flex-row items-center gap-1"');
  });

  it("keeps the text input row shrinkable on narrow screens", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "AppInputBar.tsx"),
      "utf8"
    );

    expect(source).toContain('"flex flex-row items-center w-full min-w-0"');
    expect(source).toContain('"px-3 py-2 flex-1 min-w-0 flex h-[2.75rem]"');
  });
});
