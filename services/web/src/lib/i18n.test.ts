import { describe, expect, it } from "vitest";
import { resolveBrowserLocale } from "./i18n";

describe("browser locale", () => {
  it("uses the first supported browser language", () => {
    expect(resolveBrowserLocale(["de-DE", "ru-RU", "en-US"])).toBe("ru");
    expect(resolveBrowserLocale(["en-GB", "ru-RU"])).toBe("en");
  });

  it("falls back to English for unsupported or empty preferences", () => {
    expect(resolveBrowserLocale(["de-DE"])).toBe("en");
    expect(resolveBrowserLocale([])).toBe("en");
  });
});
