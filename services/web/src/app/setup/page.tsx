"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";

type SetupStatus = { setup_required: boolean; owner_email: string };

export default function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
      setError(value instanceof Error ? value.message : "Не удалось завершить настройку");
      setBusy(false);
    }
  }

  return (
    <main className="loginWrap">
      <section className="panel login">
        <h1>Первый вход</h1>
        {status?.setup_required === false ? (
          <><p className="muted">Настройка уже завершена.</p><a className="button" href="/login">Войти</a></>
        ) : (
          <form className="form" onSubmit={submit}>
            <p className="muted">Создайте пароль администратора {status?.owner_email ?? "семьи"}.</p>
            <label className="label">Одноразовый код<input className="field" name="token" type="password" autoComplete="one-time-code" required minLength={32}/></label>
            <label className="label">Новый пароль<input className="field" name="password" type="password" autoComplete="new-password" required minLength={12}/></label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="button" disabled={busy}>{busy ? "Настраиваю..." : "Создать аккаунт"}</button>
          </form>
        )}
      </section>
    </main>
  );
}
