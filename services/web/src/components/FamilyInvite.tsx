"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Invite = { invite_url: string; expires_at: string };

export function FamilyInvite() {
  const { t } = useI18n();
  const [invite, setInvite] = useState<Invite | null>(null);
  const [error, setError] = useState("");
  async function create() {
    setError("");
    try {
      const created = await api<Invite>("/family/invites", { method: "POST" });
      setInvite(created);
      await navigator.clipboard?.writeText(created.invite_url).catch(() => undefined);
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось создать приглашение", "Could not create invitation"));
    }
  }

  return <section className="stack">
    <h2>{t("Пригласить близкого", "Invite family or friend")}</h2>
    <p className="muted">{t("Можно создавать сколько угодно приглашений. Каждая ссылка одноразовая, действует 7 дней и создаёт отдельный личный аккаунт.", "Create as many invitations as needed. Each link is single-use, valid for 7 days, and creates a separate private account.")}</p>
    <button className="button" type="button" onClick={create}>{t("Создать и скопировать ссылку", "Create and copy link")}</button>
    {invite && <><input className="field" value={invite.invite_url} readOnly aria-label={t("Ссылка-приглашение", "Invitation link")}/><button className="button secondary" type="button" onClick={() => navigator.clipboard?.writeText(invite.invite_url)}>{t("Скопировать ещё раз", "Copy again")}</button></>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
