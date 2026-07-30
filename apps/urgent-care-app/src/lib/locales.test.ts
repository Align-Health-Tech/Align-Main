import { describe, expect, it } from "vitest";
import { COPY } from "./locales";

describe("locale dictionaries", () => {
  it("keep exact key parity across en, ko, and zh", () => {
    const englishKeys = Object.keys(COPY.en).sort();
    expect(Object.keys(COPY.ko).sort()).toEqual(englishKeys);
    expect(Object.keys(COPY.zh).sort()).toEqual(englishKeys);
  });

  it("contains no Shorecare patient branding", () => {
    for (const locale of Object.values(COPY)) {
      expect(JSON.stringify(locale)).not.toMatch(/Shorecare/i);
    }
  });
});
