"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function RegisterPage() {
  const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  const {t}=useI18n();
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");const data=new FormData(event.currentTarget);try{await api("/auth/register",{method:"POST",body:JSON.stringify({email:data.get("email"),password:data.get("password"),registration_code:data.get("code"),device_name:navigator.userAgent.slice(0,150)})});location.href="/";}catch(e){setError(e instanceof Error?e.message:t("Ошибка регистрации","Registration failed"));setBusy(false);}}
  return <main className="loginWrap"><section className="panel login"><h1>{t("Вступить в семью","Join family")}</h1><p className="muted">{t("Код приглашения выдаёт администратор семьи.","The family administrator provides the invitation code.")}</p><form className="form" onSubmit={submit}><label className="label">Email<input className="field" name="email" type="email" autoComplete="username" required/></label><label className="label">{t("Пароль","Password")}<input className="field" name="password" type="password" minLength={12} autoComplete="new-password" required/></label><label className="label">{t("Код приглашения","Invitation code")}<input className="field" name="code" type="password" autoComplete="off" required/></label>{error&&<p className="error" role="alert">{error}</p>}<button className="button" disabled={busy}>{busy?t("Создаю профиль...","Creating profile..."):t("Создать профиль","Create profile")}</button><a className="button secondary" href="/login">{t("Вернуться ко входу","Back to sign in")}</a></form></section></main>;
}
