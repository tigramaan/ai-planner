"use client";

import { createContext, createElement, useContext, useEffect, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { resolveBrowserLocale } from "./locale";
import type { Locale } from "./locale";

export { resolveBrowserLocale } from "./locale";
export type { Locale } from "./locale";

const LocaleContext = createContext<Locale>("en");

export function browserLocale(): Locale {
  if (typeof navigator === "undefined") return "en";
  const languages = navigator.languages?.length
    ? navigator.languages : [navigator.language];
  return resolveBrowserLocale(languages);
}

function subscribeToLanguageChanges(update: () => void) {
  window.addEventListener("languagechange", update);
  return () => window.removeEventListener("languagechange", update);
}

export function LocaleProvider({ initialLocale, children }: {
  initialLocale: Locale;
  children: ReactNode;
}) {
  const locale = useSyncExternalStore(subscribeToLanguageChanges, browserLocale, () => initialLocale);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  return createElement(LocaleContext.Provider, { value: locale }, children);
}

export function useI18n() {
  const locale = useContext(LocaleContext);
  return {
    locale,
    t: (ru: string, en: string) => locale === "ru" ? ru : en,
  };
}
