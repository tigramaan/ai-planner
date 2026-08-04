"use client";
import { useState } from "react";
import {
  Alarm,
  ArrowSquareOut,
  ChatCircleDots,
  Check,
  Clock,
  MapPin,
  Trash,
  UsersThree,
  VideoCamera,
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ActionToast } from "@/components/ActionToast";

export type AgendaItem = {
  id: string;
  kind: string;
  source: string;
  title: string;
  start: unknown;
  end: unknown;
  status: string;
  description?: string;
  priority?: string;
  channel?: string;
  attendees?: string[];
  location?: string;
  join_url?: string;
  edit_url?: string;
  reminder_minutes?: number;
};
export function instant(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const row = value as {
      dateTime?: string;
      date?: string;
      timeZone?: string;
    };
    if (
      row.dateTime &&
      row.timeZone === "UTC" &&
      !/[zZ]|[+-]\d\d:\d\d$/.test(row.dateTime)
    )
      return `${row.dateTime}Z`;
    return row.dateTime ?? row.date ?? null;
  }
  return null;
}
const safeUrl = (value?: string) =>
  value?.startsWith("https://") ? value : undefined;
export function Agenda({
  items,
  timezone,
}: {
  items: AgendaItem[];
  timezone: string;
}) {
  const { locale, t } = useI18n();
  const [rows, setRows] = useState(items);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const format = (value: unknown, withDate = false) => {
    const raw = instant(value);
    return raw
      ? new Intl.DateTimeFormat(locale, {
          ...(withDate
            ? { weekday: "short", day: "numeric", month: "short" }
            : {}),
          hour: "2-digit",
          minute: "2-digit",
          timeZone: timezone,
        }).format(new Date(raw))
      : t("Без времени", "No time");
  };
  const kind = (value: string) =>
    ({
      event: t("Событие", "Event"),
      task: t("Задача", "Task"),
      reminder: t("Напоминание", "Reminder"),
    })[value] ?? value;
  const ordered = [...rows].sort(
    (a, b) =>
      (Date.parse(instant(a.start) ?? "") || Number.MAX_SAFE_INTEGER) -
      (Date.parse(instant(b.start) ?? "") || Number.MAX_SAFE_INTEGER),
  );
  async function removeLocal(item: AgendaItem) {
    if (!confirm(t(`Удалить «${item.title}»?`, `Delete “${item.title}”?`)))
      return;
    setBusy(item.id);
    setError("");
    try {
      await api<void>(`/tasks/${item.id}`, { method: "DELETE" });
      setRows((value) => value.filter((row) => row.id !== item.id));
      setNotice(t(`«${item.title}» удалено`, `“${item.title}” deleted`));
    } catch (value) {
      setError(
        value instanceof Error
          ? value.message
          : t("Не удалось удалить", "Could not delete"),
      );
    } finally {
      setBusy("");
    }
  }
  async function completeTask(item: AgendaItem) {
    setBusy(item.id);
    setError("");
    try {
      await api(`/tasks/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({ status: "completed" }),
      });
      setRows((value) => value.filter((row) => row.id !== item.id));
      setNotice(
        t(`Задача «${item.title}» выполнена`, `Task “${item.title}” completed`),
      );
    } catch (value) {
      setError(
        value instanceof Error
          ? value.message
          : t("Не удалось завершить задачу", "Could not complete task"),
      );
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <ActionToast message={notice} onDismiss={() => setNotice("")} />
      <div className="agenda">
        {ordered.map((item) => {
          const join = safeUrl(item.join_url);
          const edit = safeUrl(item.edit_url);
          const change = encodeURIComponent(
            `${t("Измени событие", "Change event")} «${item.title}» ${format(item.start, true)}. `,
          );
          const cancel = encodeURIComponent(
            `${t("Отмени событие", "Cancel event")} «${item.title}» ${format(item.start, true)}.`,
          );
          return (
            <article className="agendaItem" key={`${item.source}-${item.id}`}>
              <div className="agendaTime">
                <Clock size={18} />
                <span>{format(item.start)}</span>
                {instant(item.end) && (
                  <span className="muted">
                    {t("до", "to")} {format(item.end)}
                  </span>
                )}
              </div>
              <div className="agendaBody">
                <div className="agendaTitle">
                  <strong>{item.title}</strong>
                  <span className="status">
                    {kind(item.kind)} · {item.source}
                  </span>
                </div>
                {item.description && <p>{item.description}</p>}
                <div className="agendaMeta">
                  {typeof item.reminder_minutes === "number" && (
                    <span>
                      <Alarm size={16} />
                      {t("Напоминание за", "Reminder")} {item.reminder_minutes}{" "}
                      {t("минут", "minutes")}
                    </span>
                  )}
                  {item.attendees?.length ? (
                    <span>
                      <UsersThree size={16} />
                      {item.attendees.join(", ")}
                    </span>
                  ) : null}
                  {item.location && !join ? (
                    <span>
                      <MapPin size={16} />
                      {item.location}
                    </span>
                  ) : null}
                </div>
                <div className="agendaActions">
                  {join && (
                    <a
                      className="button"
                      href={join}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <VideoCamera size={18} />
                      {t("Войти во встречу", "Join meeting")}
                    </a>
                  )}
                  {edit && (
                    <a
                      className="button secondary"
                      href={edit}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ArrowSquareOut size={18} />
                      {t("Открыть в календаре", "Open in calendar")}
                    </a>
                  )}
                  {item.kind === "event" && (
                    <>
                      <a
                        className="button secondary"
                        href={`/?draft=${change}`}
                      >
                        <ChatCircleDots size={18} />
                        {t("Изменить", "Change")}
                      </a>
                      <a
                        className="button secondary danger"
                        href={`/?draft=${cancel}`}
                      >
                        <Trash size={18} />
                        {t("Отменить", "Cancel")}
                      </a>
                    </>
                  )}
                  {item.kind === "task" && (
                    <>
                      <button
                        className="button secondary"
                        disabled={busy === item.id}
                        onClick={() => completeTask(item)}
                      >
                        <Check size={18} />
                        {t("Выполнено", "Complete")}
                      </button>
                      <a
                        className="button secondary"
                        href={`/tasks?edit=${item.id}`}
                      >
                        <ChatCircleDots size={18} />
                        {t("Изменить", "Change")}
                      </a>
                      <button
                        className="button secondary danger"
                        disabled={busy === item.id}
                        onClick={() => removeLocal(item)}
                      >
                        <Trash size={18} />
                        {t("Удалить", "Delete")}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
