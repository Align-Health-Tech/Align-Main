import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { BODY_DIAGRAMS } from "./body-regions";

describe("body diagram assets", () => {
  it("contains an SVG for every interactive backend-compatible diagram entry", () => {
    const publicRoot = resolve(process.cwd(), "public/bodydiagram");
    const missing = BODY_DIAGRAMS.map((entry) => entry.file).filter(
      (file) => !existsSync(resolve(publicRoot, file)),
    );
    expect(missing).toEqual([]);
    expect(BODY_DIAGRAMS.length).toBeGreaterThanOrEqual(13);
  });
});
