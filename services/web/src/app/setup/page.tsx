"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type SetupStatus = { setup_required: boolean };

export default function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { t } = useI18n();

  useEffect(() => {
    api<SetupStatus>("/auth/setup-status").then(setStatus).catch((value) => setError(value.message));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/setup", {
        method: "POST",
        body: JSON.stringify({
          setup_token: data.get("token"),
          password: data.get("password"),
          device_name: navigator.userAgent.slice(0, 150),
        }),
      });
      location.href = "/";
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось завершить настройку", "Setup failed"));
      setBusy(false);
    }
  }

  return (
    <main className="loginWrap">
      <section className="panel login">
        <h1>{t("Первый вход", "First sign-in")}</h1>
        {status?.setup_required === false ? (
          <><p className="muted">{t("Настройка уже завершена.", "Setup is already complete.")}</p><a className="button" href="/login">{t("Войти", "Sign in")}</a></>
        ) : (
          <form className="form" onSubmit={submit}>
            <p className="muted">{t("Создайте пароль администратора семьи.", "Create an administrator password for the family.")}</p>
            <label className="label">{t("Одноразовый код", "One-time code")}<input className="field" name="token" type="password" autoComplete="one-time-code" required minLength={32}/></label>
            <label className="label">{t("Новый пароль", "New password")}<input className="field" name="password" type="password" autoComplete="new-password" required minLength={12}/></label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="button" disabled={busy}>{busy ? t("Настраиваю...", "Setting up...") : t("Создать аккаунт", "Create account")}</button>
          </form>
        )}
      </section>
    </main>
  );
}
