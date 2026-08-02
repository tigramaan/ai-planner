"use client";

import { FluentProvider, webDarkTheme, webLightTheme } from "@fluentui/react-components";
import { useEffect, useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const update = () => setDark(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return <FluentProvider theme={dark ? webDarkTheme : webLightTheme}>{children}</FluentProvider>;
}
