import { describe, expect, it } from "vitest";
import { resolveAcceptLanguage, resolveBrowserLocale } from "./locale";

describe("request locale", () => {
  it("orders valid preferences by quality without prioritizing Russian over English", () => {
    expect(resolveAcceptLanguage("en-US;q=0.5,ru-RU;q=0.9")).toBe("ru");
    expect(resolveAcceptLanguage("ru;q=0.5,en;q=1")).toBe("en");
    expect(resolveAcceptLanguage("de-DE,ru;q=0.8,en;q=0.7")).toBe("ru");
    expect(resolveAcceptLanguage("en;q=0.8,ru;q=0.8")).toBe("en");
  });
  it("rejects invalid and disabled weights with deterministic English fallback", () => {
    for (const header of [null, "", "de", "ru;q=0,en", "ru;q=2,en", "ru;q=NaN,en", "ru;q=-1,en"]) {
      expect(resolveAcceptLanguage(header)).toBe("en");
    }
  });
  it("bounds untrusted preferences and normalizes language tags", () => {
    expect(resolveAcceptLanguage(Array(32).fill("de").join(",") + ",ru")).toBe("en");
    expect(resolveAcceptLanguage(" ".repeat(4096) + "ru")).toBe("en");
    expect(resolveBrowserLocale([" RU-ru ", "en"])).toBe("ru");
  });
});
