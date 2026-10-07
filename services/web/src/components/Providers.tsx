"use client";

import { FluentProvider, webDarkTheme, webLightTheme } from "@fluentui/react-components";
import { useEffect, useState } from "react";
import { LocaleProvider } from "@/lib/i18n";
import type { Locale } from "@/lib/locale";

export function Providers({ children, initialLocale }: { children: React.ReactNode; initialLocale: Locale }) {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const update = () => setDark(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return <LocaleProvider initialLocale={initialLocale}><FluentProvider theme={dark ? webDarkTheme : webLightTheme}>{children}</FluentProvider></LocaleProvider>;
}
