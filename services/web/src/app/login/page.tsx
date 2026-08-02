"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");const data=new FormData(event.currentTarget);try{await api("/auth/login",{method:"POST",body:JSON.stringify({email:data.get("email"),password:data.get("password"),device_name:navigator.userAgent.slice(0,150)})});location.href="/";}catch(e){setError(e instanceof Error?e.message:"Ошибка входа");setBusy(false);}}
  return <main className="loginWrap"><section className="panel login"><h1>Семейный планировщик</h1><p className="muted">Личные данные и подключения каждого участника изолированы.</p><form className="form" onSubmit={submit}><label className="label">Email<input className="field" name="email" type="email" autoComplete="username" required/></label><label className="label">Пароль<input className="field" name="password" type="password" autoComplete="current-password" required/></label>{error&&<p className="error" role="alert">{error}</p>}<button className="button" disabled={busy}>{busy?"Проверяю...":"Войти"}</button><a className="button secondary" href="/register">Вступить в семью</a></form></section></main>;
}
