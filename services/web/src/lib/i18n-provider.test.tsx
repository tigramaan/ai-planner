import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { hydrateRoot } from "react-dom/client";
import { LocaleProvider, browserLocale, useI18n } from "./i18n";

function Probe({ id = "label" }: { id?: string }) {
  const { locale, t } = useI18n();
  return <span data-testid={id} lang={locale}>{t("Русский", "English")}</span>;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  document.documentElement.lang = "en";
});

describe("shared browser locale", () => {
  it("updates every consumer and html.lang when browser preferences change", () => {
    const languages = vi.spyOn(navigator, "languages", "get").mockReturnValue(["ru-RU", "en"]);
    render(<LocaleProvider initialLocale="ru"><Probe /><Probe id="second" /></LocaleProvider>);
    expect(screen.getByTestId("label")).toHaveTextContent("Русский");
    expect(document.documentElement.lang).toBe("ru");
    languages.mockReturnValue(["en-US", "ru"]);
    act(() => window.dispatchEvent(new Event("languagechange")));
    expect(screen.getByTestId("label")).toHaveTextContent("English");
    expect(screen.getByTestId("second")).toHaveTextContent("English");
    expect(document.documentElement.lang).toBe("en");
  });
  it("uses navigator.language when navigator.languages is empty", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue([]);
    vi.spyOn(navigator, "language", "get").mockReturnValue("ru-RU");
    expect(browserLocale()).toBe("ru");
  });
  it("hydrates the server locale before adopting different browser preferences", async () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["en-US"]);
    const tree = <LocaleProvider initialLocale="ru"><Probe /></LocaleProvider>;
    const container = document.createElement("div");
    container.innerHTML = renderToString(tree);
    expect(container.textContent).toBe("Русский");
    const onRecoverableError = vi.fn();
    let root: ReturnType<typeof hydrateRoot>;
    await act(async () => { root = hydrateRoot(container, tree, { onRecoverableError }); });
    expect(container.textContent).toBe("English");
    expect(onRecoverableError).not.toHaveBeenCalled();
    act(() => root.unmount());
  });
});
