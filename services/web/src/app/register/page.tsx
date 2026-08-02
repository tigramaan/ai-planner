"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");const data=new FormData(event.currentTarget);try{await api("/auth/register",{method:"POST",body:JSON.stringify({email:data.get("email"),password:data.get("password"),registration_code:data.get("code"),device_name:navigator.userAgent.slice(0,150)})});location.href="/";}catch(e){setError(e instanceof Error?e.message:"Ошибка регистрации");setBusy(false);}}
  return <main className="loginWrap"><section className="panel login"><h1>Вступить в семью</h1><p className="muted">Код приглашения выдаёт администратор семьи.</p><form className="form" onSubmit={submit}><label className="label">Email<input className="field" name="email" type="email" autoComplete="username" required/></label><label className="label">Пароль<input className="field" name="password" type="password" minLength={12} autoComplete="new-password" required/></label><label className="label">Код приглашения<input className="field" name="code" type="password" autoComplete="off" required/></label>{error&&<p className="error" role="alert">{error}</p>}<button className="button" disabled={busy}>{busy?"Создаю профиль...":"Создать профиль"}</button><a className="button secondary" href="/login">Вернуться ко входу</a></form></section></main>;
}
