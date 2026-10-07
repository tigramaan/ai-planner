export type Locale = "ru" | "en";

export function resolveBrowserLocale(languages: readonly string[]): Locale {
  for (const language of languages) {
    const primary = language.trim().toLowerCase().split("-")[0];
    if (primary === "ru" || primary === "en") return primary;
  }
  return "en";
}

export function resolveAcceptLanguage(header: string | null): Locale {
  const preferences = (header ?? "").slice(0, 4096).split(",").slice(0, 32)
    .map((range) => {
      const [language, ...parameters] = range.trim().split(";");
      const weight = parameters.map((value) => value.trim())
        .find((value) => value.startsWith("q="))?.slice(2);
      const quality = weight === undefined ? 1
        : /^(?:0(?:\.\d{0,3})?|1(?:\.0{0,3})?)$/.test(weight) ? Number(weight) : 0;
      return { language, quality };
    })
    .filter(({ quality }) => quality > 0)
    .sort((left, right) => right.quality - left.quality);
  return resolveBrowserLocale(preferences.map(({ language }) => language));
}
