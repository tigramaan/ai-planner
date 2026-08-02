"use client";

import { FormEvent, useEffect, useState } from "react";
import { PushSetup } from "@/components/PushSetup";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

type Integration = { provider: string; status: string; account_email?: string; scopes: string[] };

export default function Settings() {
  const [items, setItems] = useState<Integration[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const state = (provider: string) => items.find((item) => item.provider === provider);
  function load() { api<Integration[]>("/integrations").then(setItems).catch((value) => setError(value.message)); }
  useEffect(load, []);

  async function connect(provider: string, scopes: string[]) {
    setError("");
    try {
      const result = await api<{ authorization_url: string }>(`/integrations/${provider}/oauth/start`, { method: "POST", body: JSON.stringify({ scopes }) });
      location.href = result.authorization_url;
    } catch (value) { setError(value instanceof Error ? value.message : "Ошибка OAuth"); }
  }

  async function saveAI(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/integrations/openai", { method: "POST", body: JSON.stringify({ api_key: data.get("api_key"), model: data.get("model"), transcription_model: "whisper-1" }) });
      setNotice("OpenAI подключён. Ключ сохранён в зашифрованном виде.");
      load();
    } catch (value) { setError(value instanceof Error ? value.message : "Ошибка"); }
  }

  async function password(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: data.get("current"), new_password: data.get("next") }) });
      location.href = "/login";
    } catch (value) { setError(value instanceof Error ? value.message : "Ошибка"); }
  }

  return <Shell><header className="pageHead"><div><h1>Настройки</h1><p className="muted">Секреты после сохранения нельзя прочитать обратно.</p></div></header>{notice && <p>{notice}</p>}{error && <p className="error" role="alert">{error}</p>}<div className="grid"><section className="panel stack"><h2>Интеграции</h2><div className="integration stack"><div><strong>Google Calendar и Contacts</strong><div className="status">{state("google")?.account_email || state("google")?.status || "Не подключено"}</div></div><button className="button secondary" onClick={() => connect("google", ["identity", "calendar.read", "calendar.write", "contacts.read"])}>Авторизовать календарь</button><button className="button secondary" onClick={() => connect("google", ["identity", "gmail.read", "gmail.compose", "gmail.send"])}>Авторизовать Gmail</button></div><div className="integration stack"><div><strong>Microsoft 365 и Teams</strong><div className="status">{state("microsoft")?.account_email || state("microsoft")?.status || "Не подключено"}</div></div><button className="button secondary" onClick={() => connect("microsoft", ["identity", "calendar", "contacts", "teams", "mail.read", "mail.write"])}>Авторизовать Teams</button></div><form className="form" onSubmit={saveAI}><h2>OpenAI</h2><label className="label">API key<input className="field" name="api_key" type="password" autoComplete="off" required/></label><label className="label">Модель<input className="field" name="model" defaultValue="gpt-5-mini" required/></label><button className="button">Сохранить AI</button></form></section><section className="panel stack"><PushSetup/><form className="form" onSubmit={password}><h2>Смена пароля</h2><label className="label">Текущий пароль<input className="field" name="current" type="password" autoComplete="current-password" required/></label><label className="label">Новый пароль<input className="field" name="next" type="password" minLength={12} autoComplete="new-password" required/></label><button className="button">Сменить пароль</button></form></section></div></Shell>;
}
