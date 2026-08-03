"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  const {t}=useI18n();
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");const data=new FormData(event.currentTarget);try{await api("/auth/login",{method:"POST",body:JSON.stringify({email:data.get("email"),password:data.get("password"),device_name:navigator.userAgent.slice(0,150)})});location.href="/";}catch(e){setError(e instanceof Error?e.message:t("Ошибка входа","Login failed"));setBusy(false);}}
  return <main className="loginWrap"><section className="panel login"><h1>{t("Семейный планировщик","Family planner")}</h1><p className="muted">{t("Личные данные и подключения каждого участника изолированы.","Each family member's data and integrations are isolated.")}</p><form className="form" onSubmit={submit}><label className="label">Email<input className="field" name="email" type="email" autoComplete="username" required/></label><label className="label">{t("Пароль","Password")}<input className="field" name="password" type="password" autoComplete="current-password" required/></label>{error&&<p className="error" role="alert">{error}</p>}<button className="button" disabled={busy}>{busy?t("Проверяю...","Signing in..."):t("Войти","Sign in")}</button><a className="button secondary" href="/register">{t("Вступить в семью","Join family")}</a></form></section></main>;
}
