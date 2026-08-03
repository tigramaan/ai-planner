"use client";

import { useEffect, useState } from "react";

export type Locale = "ru" | "en";

export function resolveBrowserLocale(languages: readonly string[]): Locale {
  for (const language of languages) {
    const primary = language.toLowerCase().split("-")[0];
    if (primary === "ru" || primary === "en") return primary;
  }
  return "en";
}

export function browserLocale(): Locale {
  return typeof navigator === "undefined" ? "en" : resolveBrowserLocale(navigator.languages);
}

export function useI18n() {
  const [locale] = useState<Locale>(() =>
    browserLocale()
  );

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return {
    locale,
    t: (ru: string, en: string) => locale === "ru" ? ru : en,
  };
}
