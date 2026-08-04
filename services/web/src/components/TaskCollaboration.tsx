"use client";

import { FormEvent, useState } from "react";
import { Plus, Trash, Users, X } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export type SharedTask = {
  id: string;
  is_owner: boolean;
  owner_email: string;
  viewer_participant_id: string | null;
  participants: { id: string; user_id: string; email: string }[];
  checklist: { id: string; text: string; completed: boolean; position: number }[];
  activity: {
    id: string;
    actor_email: string;
    action: string;
    details: Record<string, unknown>;
    created_at: string;
  }[];
};

export function TaskCollaboration({
  task,
  onChange,
  onLeave,
}: {
  task: SharedTask;
  onChange: (task: SharedTask) => void;
  onLeave: () => void;
}) {
  const { locale, t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function mutate(path: string, init: RequestInit) {
    setBusy(true);
    setError("");
    try {
      onChange(await api<SharedTask>(path, init));
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    } finally {
      setBusy(false);
    }
  }

  function addParticipant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const email = String(new FormData(form).get("email") || "");
    void mutate(`/tasks/${task.id}/participants`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }).then(() => form.reset());
  }

  function addItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const text = String(new FormData(form).get("text") || "");
    void mutate(`/tasks/${task.id}/checklist`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }).then(() => form.reset());
  }

  async function removeParticipant(id: string, self: boolean) {
    setBusy(true);
    setError("");
    try {
      const updated = await api<SharedTask>(`/tasks/${task.id}/participants/${id}`, {
        method: "DELETE",
      });
      if (self) onLeave();
      else onChange(updated);
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    } finally {
      setBusy(false);
    }
  }

  const shared = task.participants.length > 0;
  return (
    <div className="taskCollaboration">
      {(shared || !task.is_owner) && (
        <div className="taskSharedWith">
          <Users size={17} />
          <span>
            {task.is_owner
              ? task.participants.map((member) => member.email).join(", ")
              : t(`Владелец: ${task.owner_email}`, `Owner: ${task.owner_email}`)}
          </span>
        </div>
      )}

      <div className="taskChecklist">
        {task.checklist.map((item) => (
          <div className="taskChecklistItem" key={item.id}>
            <input
              type="checkbox"
              checked={item.completed}
              disabled={busy}
              aria-label={item.text}
              onChange={() =>
                void mutate(`/tasks/${task.id}/checklist/${item.id}`, {
                  method: "PUT",
                  body: JSON.stringify({ completed: !item.completed }),
                })
              }
            />
            <span className={item.completed ? "done" : ""}>{item.text}</span>
            <button
              className="bareIcon"
              type="button"
              disabled={busy}
              onClick={async () => {
                await api(`/tasks/${task.id}/checklist/${item.id}`, { method: "DELETE" });
                onChange({ ...task, checklist: task.checklist.filter((row) => row.id !== item.id) });
              }}
              aria-label={t("Удалить пункт", "Delete item")}
            >
              <X size={15} />
            </button>
          </div>
        ))}
        <form className="taskInlineForm" onSubmit={addItem}>
          <input name="text" required maxLength={500} placeholder={t("Добавить пункт", "Add item")} />
          <button type="submit" disabled={busy} aria-label={t("Добавить", "Add")}><Plus size={17} /></button>
        </form>
      </div>

      {task.is_owner ? (
        <details className="taskShareDetails">
          <summary>{t("Совместный доступ и история", "Sharing and activity")}</summary>
          <form className="taskInlineForm" onSubmit={addParticipant}>
            <input name="email" type="email" required placeholder={t("Email пользователя сервера", "Server user email")} />
            <button type="submit" disabled={busy}>{t("Добавить", "Add")}</button>
          </form>
          {task.participants.map((member) => (
            <div className="taskMember" key={member.id}>
              <span>{member.email}</span>
              <button type="button" disabled={busy} onClick={() => void removeParticipant(member.id, false)}><Trash size={15} /> {t("Закрыть доступ", "Remove")}</button>
            </div>
          ))}
          <Activity task={task} locale={locale} />
        </details>
      ) : (
        <details className="taskShareDetails">
          <summary>{t("История изменений", "Activity")}</summary>
          <button className="button secondary" type="button" disabled={busy || !task.viewer_participant_id} onClick={() => void removeParticipant(task.viewer_participant_id || "", true)}>{t("Покинуть задачу", "Leave task")}</button>
          <Activity task={task} locale={locale} />
        </details>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}

function Activity({ task, locale }: { task: SharedTask; locale: string }) {
  const labels: Record<string, [string, string]> = {
    created: ["создал(а) задачу", "created the task"],
    updated: ["изменил(а) задачу", "updated the task"],
    participant_added: ["добавил(а) участника", "added a participant"],
    participant_removed: ["удалил(а) участника", "removed a participant"],
    checklist_added: ["добавил(а) пункт", "added an item"],
    checklist_updated: ["изменил(а) пункт", "updated an item"],
    checklist_deleted: ["удалил(а) пункт", "deleted an item"],
  };
  return <div className="taskActivity">{task.activity.slice(0, 12).map((row) => <div key={row.id}><span>{row.actor_email} {locale.startsWith("ru") ? labels[row.action]?.[0] : labels[row.action]?.[1]}</span><time>{new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(row.created_at))}</time></div>)}</div>;
}
