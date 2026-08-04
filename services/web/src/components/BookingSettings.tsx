"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type KeyMeta = { id: string; name: string; prefix: string; revoked_at?: string };
type Policy = {
  enabled: boolean;
  duration_minutes: number;
  workdays: number[];
  work_start: string;
  work_end: string;
  minimum_notice_minutes: number;
  horizon_days: number;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  max_per_day: number;
  title_template: string;
  keys: KeyMeta[];
};

const initial: Policy = {
  enabled: false,
  duration_minutes: 30,
  workdays: [0, 1, 2, 3, 4],
  work_start: "09:00",
  work_end: "18:00",
  minimum_notice_minutes: 120,
  horizon_days: 30,
  buffer_before_minutes: 0,
  buffer_after_minutes: 15,
  max_per_day: 5,
  title_template: "Звонок: {name}",
  keys: [],
};

export function BookingSettings() {
  const { t } = useI18n();
  const [policy, setPolicy] = useState(initial);
  const [newKey, setNewKey] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  function load() {
    api<Policy>("/booking/settings").then(setPolicy).catch((value) => setError(value.message));
  }
  useEffect(load, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const saved = await api<Policy>("/booking/settings", {
        method: "PUT",
        body: JSON.stringify({ ...policy, keys: undefined }),
      });
      setPolicy({ ...saved, keys: policy.keys });
      setNotice(t("Настройки API записи сохранены.", "Booking API settings saved."));
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    }
  }

  async function createKey() {
    setError("");
    try {
      const result = await api<{ api_key: string }>("/booking/keys", {
        method: "POST",
        body: JSON.stringify({ name: "Website" }),
      });
      setNewKey(result.api_key);
      load();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    }
  }

  async function revoke(id: string) {
    await api(`/booking/keys/${id}`, { method: "DELETE" });
    load();
  }

  const number = (field: keyof Policy, value: number) => setPolicy({ ...policy, [field]: value });
  return (
    <section className="stack">
      <form className="form" onSubmit={save}>
        <h2>{t("API записи на встречи", "Meeting booking API")}</h2>
        <p className="muted">
          {t("Сайт сам показывает форму и обращается к API только со своего сервера.", "Your site owns the form and calls this API only from its server.")}
        </p>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="status">{notice}</p>}
        <label className="label">
          <span><input type="checkbox" checked={policy.enabled} onChange={(event) => setPolicy({ ...policy, enabled: event.target.checked })} /> {t("Включить API записи", "Enable booking API")}</span>
        </label>
        <label className="label">{t("Длительность, минут", "Duration, minutes")}<input className="field" type="number" min="15" max="240" step="5" value={policy.duration_minutes} onChange={(event) => number("duration_minutes", Number(event.target.value))} /></label>
        <label className="label">{t("Рабочие дни (0=Пн … 6=Вс)", "Workdays (0=Mon … 6=Sun)")}<input className="field" value={policy.workdays.join(",")} onChange={(event) => setPolicy({ ...policy, workdays: event.target.value.split(",").map(Number) })} /></label>
        <div className="fieldRow">
          <label className="label">{t("С", "From")}<input className="field" type="time" value={policy.work_start} onChange={(event) => setPolicy({ ...policy, work_start: event.target.value })} /></label>
          <label className="label">{t("До", "To")}<input className="field" type="time" value={policy.work_end} onChange={(event) => setPolicy({ ...policy, work_end: event.target.value })} /></label>
        </div>
        <label className="label">{t("Минимум до встречи, минут", "Minimum notice, minutes")}<input className="field" type="number" min="0" max="43200" value={policy.minimum_notice_minutes} onChange={(event) => number("minimum_notice_minutes", Number(event.target.value))} /></label>
        <label className="label">{t("Горизонт записи, дней", "Booking horizon, days")}<input className="field" type="number" min="1" max="90" value={policy.horizon_days} onChange={(event) => number("horizon_days", Number(event.target.value))} /></label>
        <div className="fieldRow">
          <label className="label">{t("Буфер до", "Buffer before")}<input className="field" type="number" min="0" max="240" value={policy.buffer_before_minutes} onChange={(event) => number("buffer_before_minutes", Number(event.target.value))} /></label>
          <label className="label">{t("Буфер после", "Buffer after")}<input className="field" type="number" min="0" max="240" value={policy.buffer_after_minutes} onChange={(event) => number("buffer_after_minutes", Number(event.target.value))} /></label>
        </div>
        <label className="label">{t("Максимум встреч в день", "Maximum meetings per day")}<input className="field" type="number" min="1" max="50" value={policy.max_per_day} onChange={(event) => number("max_per_day", Number(event.target.value))} /></label>
        <label className="label">{t("Название встречи", "Meeting title")}<input className="field" value={policy.title_template} onChange={(event) => setPolicy({ ...policy, title_template: event.target.value })} /></label>
        <button className="button">{t("Сохранить API записи", "Save booking API")}</button>
      </form>
      <div className="form">
        <h3>{t("Ключи сайта", "Website keys")}</h3>
        <button className="button secondary" type="button" onClick={createKey}>{t("Создать новый ключ", "Create new key")}</button>
        {newKey && <label className="label">{t("Скопируйте сейчас — ключ больше не будет показан", "Copy now — the key will not be shown again")}<input className="field" readOnly value={newKey} onFocus={(event) => event.currentTarget.select()} /></label>}
        {policy.keys.filter((key) => !key.revoked_at).map((key) => <div className="integration" key={key.id}><span>{key.name}: {key.prefix}…</span><button className="button secondary" type="button" onClick={() => revoke(key.id)}>{t("Отозвать", "Revoke")}</button></div>)}
      </div>
    </section>
  );
}
