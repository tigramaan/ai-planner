"use client";

import { FormEvent, useEffect, useState } from "react";
import { PushSetup } from "@/components/PushSetup";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Integration = { provider: string; status: string; account_email?: string; scopes: string[]; configured?: boolean; source?: string };

export default function Settings() {
  const { t } = useI18n();
  const [items, setItems] = useState<Integration[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const state = (provider: string) => items.find((item) => item.provider === provider);
  const providerState = (provider: string) => {
    const item = state(provider);
    return item?.account_email || (item?.status === "connected" ? t("Подключено", "Connected") : "");
  };
  function load() { api<Integration[]>("/integrations").then(setItems).catch((value) => setError(value.message)); }
  useEffect(load, []);

  async function connect(provider: string, scopes: string[]) {
    setError("");
    try {
      const result = await api<{ authorization_url: string }>(`/integrations/${provider}/oauth/start`, { method: "POST", body: JSON.stringify({ scopes }) });
      location.href = result.authorization_url;
    } catch (value) { setError(value instanceof Error ? value.message : t("Ошибка OAuth", "OAuth error")); }
  }

  async function saveAI(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/integrations/openai", { method: "POST", body: JSON.stringify({ api_key: data.get("api_key"), model: data.get("model"), transcription_model: "whisper-1" }) });
      setNotice(t("OpenAI подключён. Ключ сохранён в зашифрованном виде.", "OpenAI connected. The key is stored encrypted."));
      load();
    } catch (value) { setError(value instanceof Error ? value.message : t("Ошибка", "Error")); }
  }

  async function password(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: data.get("current"), new_password: data.get("next") }) });
      location.href = "/login";
    } catch (value) { setError(value instanceof Error ? value.message : t("Ошибка", "Error")); }
  }

  const disconnected = t("Не подключено", "Not connected");
  return <Shell><header className="pageHead"><div><h1>{t("Настройки", "Settings")}</h1><p className="muted">{t("Секреты после сохранения нельзя прочитать обратно.", "Saved secrets cannot be read back.")}</p></div></header>{notice && <p>{notice}</p>}{error && <p className="error" role="alert">{error}</p>}<div className="grid"><section className="panel stack"><h2>{t("Интеграции", "Integrations")}</h2><div className="integration stack"><div><strong>Google Calendar & Contacts</strong><div className="status">{providerState("google") || disconnected}</div></div><button className="button secondary" onClick={() => connect("google", ["identity", "calendar.read", "calendar.write", "contacts.read"])}>{t("Авторизовать календарь", "Authorize calendar")}</button><button className="button secondary" onClick={() => connect("google", ["identity", "gmail.read", "gmail.compose", "gmail.send"])}>{t("Авторизовать Gmail", "Authorize Gmail")}</button></div><div className="integration stack"><div><strong>Microsoft 365 & Teams</strong><div className="status">{providerState("microsoft") || disconnected}</div></div><button className="button secondary" onClick={() => connect("microsoft", ["identity", "calendar", "contacts", "teams", "mail.read", "mail.write"])}>{t("Авторизовать Teams", "Authorize Teams")}</button></div><form className="form" onSubmit={saveAI}><h2>OpenAI</h2>{state("openai")?.configured && <p className="status">{t("Ключ из Telegram-бота подключён на сервере.", "The key from the Telegram bot is configured on the server.")}</p>}<label className="label">API key<input className="field" name="api_key" type="password" autoComplete="off" required/></label><label className="label">{t("Модель", "Model")}<input className="field" name="model" defaultValue="gpt-5-mini" required/></label><button className="button">{t("Заменить ключ OpenAI", "Replace OpenAI key")}</button></form></section><section className="panel stack"><PushSetup/><form className="form" onSubmit={password}><h2>{t("Смена пароля", "Change password")}</h2><label className="label">{t("Текущий пароль", "Current password")}<input className="field" name="current" type="password" autoComplete="current-password" required/></label><label className="label">{t("Новый пароль", "New password")}<input className="field" name="next" type="password" minLength={12} autoComplete="new-password" required/></label><button className="button">{t("Сменить пароль", "Change password")}</button></form></section></div></Shell>;
}
