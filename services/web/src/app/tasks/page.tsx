"use client";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Check, CheckCircle, Circle, MagnifyingGlass, PencilSimple, Plus, Trash } from "@phosphor-icons/react";
import { Shell } from "@/components/Shell";
import { ActionToast } from "@/components/ActionToast";
import { TaskCollaboration, type SharedTask } from "@/components/TaskCollaboration";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Status = "open" | "completed";
type Priority = "low" | "normal" | "high";
type Task = SharedTask & {
  id: string;
  title: string;
  description: string;
  due_at: string | null;
  timezone: string;
  priority: Priority;
  status: Status;
  created_at: string;
};
type Filter = "open" | "today" | "overdue" | "completed" | "shared" | "all";
const moscowDate = (value: string | Date) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
const localInput = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("sv-SE", {
        timeZone: "Europe/Moscow",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
        .format(new Date(value))
        .replace(" ", "T")
    : "";
const dueIso = (value: string) => (value ? `${value}:00+03:00` : null);

export default function Tasks() {
  const { locale, t } = useI18n();
  const [items, setItems] = useState<Task[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [filter, setFilter] = useState<Filter>("open");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Task | null>(null);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    api<Task[]>("/tasks")
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("edit");
    const task = items.find((item) => item.id === id);
    if (task) setEditing(task);
  }, [items]);
  const today = moscowDate(new Date());
  const isOverdue = (task: Task) =>
    task.status === "open" && !!task.due_at && moscowDate(task.due_at) < today;
  const isToday = (task: Task) =>
    task.status === "open" &&
    !!task.due_at &&
    moscowDate(task.due_at) === today;
  const counts = {
    open: items.filter((x) => x.status === "open").length,
    today: items.filter(isToday).length,
    overdue: items.filter(isOverdue).length,
    completed: items.filter((x) => x.status === "completed").length,
    shared: items.filter((x) => x.participants.length > 0).length,
    all: items.length,
  };
  const visible = useMemo(
    () =>
      items
        .filter((task) => {
          const matches =
            !query ||
            `${task.title} ${task.description}`
              .toLocaleLowerCase(locale)
              .includes(query.toLocaleLowerCase(locale));
          if (!matches) return false;
          if (filter === "all") return true;
          if (filter === "today") return isToday(task);
          if (filter === "overdue") return isOverdue(task);
          if (filter === "shared") return task.participants.length > 0;
          return task.status === filter;
        })
        .sort((a, b) => {
          if (a.status !== b.status) return a.status === "open" ? -1 : 1;
          if (a.due_at && b.due_at)
            return Date.parse(a.due_at) - Date.parse(b.due_at);
          if (a.due_at) return -1;
          if (b.due_at) return 1;
          return Date.parse(b.created_at) - Date.parse(a.created_at);
        }),
    [items, filter, query, locale],
  );
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy("new");
    setError("");
    try {
      const item = await api<Task>("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: data.get("title"),
          description: data.get("description"),
          due_at: dueIso(String(data.get("due_at") || "")),
          timezone: "Europe/Moscow",
          priority: data.get("priority"),
        }),
      });
      setItems((v) => [item, ...v]);
      form.reset();
      setNotice(
        t(`Задача «${item.title}» создана`, `Task “${item.title}” created`),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("Не удалось создать задачу", "Could not create task"),
      );
    } finally {
      setBusy("");
    }
  }
  async function update(id: string, changes: Partial<Task>) {
    setBusy(id);
    setError("");
    try {
      const item = await api<Task>(`/tasks/${id}`, {
        method: "PUT",
        body: JSON.stringify(changes),
      });
      setItems((v) => v.map((x) => (x.id === id ? item : x)));
      setEditing(null);
      setNotice(
        item.status === "completed"
          ? t(
              `Задача «${item.title}» выполнена`,
              `Task “${item.title}” completed`,
            )
          : t(`Задача «${item.title}» сохранена`, `Task “${item.title}” saved`),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("Не удалось изменить задачу", "Could not update task"),
      );
    } finally {
      setBusy("");
    }
  }
  async function remove(task: Task) {
    if (
      !confirm(
        t(`Удалить задачу «${task.title}»?`, `Delete task “${task.title}”?`),
      )
    )
      return;
    setBusy(task.id);
    try {
      await api<void>(`/tasks/${task.id}`, { method: "DELETE" });
      setItems((v) => v.filter((x) => x.id !== task.id));
      setNotice(
        t(`Задача «${task.title}» удалена`, `Task “${task.title}” deleted`),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("Не удалось удалить задачу", "Could not delete task"),
      );
    } finally {
      setBusy("");
    }
  }
  const due = (task: Task) =>
    !task.due_at
      ? t("Без срока", "No due date")
      : new Intl.DateTimeFormat(locale, {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Europe/Moscow",
        }).format(new Date(task.due_at));
  const filters: [Filter, string][] = [
    ["open", t("Открытые", "Open")],
    ["today", t("Сегодня", "Today")],
    ["overdue", t("Просроченные", "Overdue")],
    ["completed", t("Архив", "Archive")],
    ["shared", t("Совместные", "Shared")],
    ["all", t("Все", "All")],
  ];
  return (
    <Shell>
      <ActionToast message={notice} onDismiss={() => setNotice("")} />
      <header className="pageHead">
        <div>
          <h1>{t("Задачи", "Tasks")}</h1>
          <p className="muted">
            {t(
              "Планируйте, уточняйте сроки и закрывайте выполненное.",
              "Plan, set due dates, and complete your work.",
            )}
          </p>
        </div>
        <a
          className="button secondary"
          href={`/?draft=${encodeURIComponent(t("Создай задачу ", "Create a task "))}`}
        >
          {t("Создать голосом или в чате", "Create by voice or chat")}
        </a>
      </header>
      <section className="taskComposer">
        <form className="taskForm" onSubmit={add}>
          <label className="label taskTitleField">
            {t("Что нужно сделать", "What needs to be done")}
            <input
              className="field"
              name="title"
              required
              maxLength={300}
              placeholder={t(
                "Например: подготовить договор",
                "For example: prepare the contract",
              )}
            />
          </label>
          <label className="label">
            {t("Срок по Москве", "Due in Moscow")}
            <input className="field" name="due_at" type="datetime-local" />
          </label>
          <label className="label">
            {t("Приоритет", "Priority")}
            <select className="field" name="priority" defaultValue="normal">
              <option value="low">{t("Низкий", "Low")}</option>
              <option value="normal">{t("Обычный", "Normal")}</option>
              <option value="high">{t("Высокий", "High")}</option>
            </select>
          </label>
          <label className="label taskDescriptionField">
            {t("Описание", "Description")}
            <textarea
              className="field"
              name="description"
              rows={2}
              maxLength={5000}
            />
          </label>
          <button className="button taskAdd" disabled={busy === "new"}>
            <Plus size={19} />
            {t("Добавить задачу", "Add task")}
          </button>
        </form>
      </section>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <section className="taskToolbar">
        <div className="taskFilters" role="tablist">
          {filters.map(([value, label]) => (
            <button
              type="button"
              role="tab"
              aria-selected={filter === value}
              className={`taskFilter${filter === value ? " active" : ""}`}
              onClick={() => setFilter(value)}
              key={value}
            >
              {label}
              <span>{counts[value]}</span>
            </button>
          ))}
        </div>
        <label className="taskSearch">
          <MagnifyingGlass size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("Поиск задач", "Search tasks")}
            aria-label={t("Поиск задач", "Search tasks")}
          />
        </label>
      </section>
      <section className="taskList">
        {visible.length === 0 ? (
          <div className="taskEmpty">
            <CheckCircle size={34} />
            <strong>{t("Здесь пока пусто", "Nothing here yet")}</strong>
            <span className="muted">
              {t(
                "Создайте задачу выше или выберите другой фильтр.",
                "Create a task above or choose another filter.",
              )}
            </span>
          </div>
        ) : (
          visible.map((task) => (
            <article
              className={`taskItem${task.status === "completed" ? " completed" : ""}`}
              key={task.id}
            >
              {editing?.id === task.id ? (
                <EditTask
                  task={task}
                  locale={locale}
                  busy={busy === task.id}
                  onCancel={() => setEditing(null)}
                  onSave={update}
                />
              ) : (
                <>
                  <button
                    className="taskCheck"
                    disabled={busy === task.id}
                    onClick={() =>
                      update(task.id, {
                        status: task.status === "open" ? "completed" : "open",
                      })
                    }
                    aria-label={
                      task.status === "open"
                        ? t("Отметить выполненной", "Mark complete")
                        : t("Вернуть в работу", "Reopen")
                    }
                  >
                    {task.status === "open" ? (
                      <Circle size={24} />
                    ) : (
                      <CheckCircle size={24} weight="fill" />
                    )}
                  </button>
                  <div className="taskContent">
                    <strong>{task.title}</strong>
                    {task.description && <p>{task.description}</p>}
                    <div className="taskMeta">
                      <span className={isOverdue(task) ? "overdue" : ""}>
                        {due(task)}
                      </span>
                      <span className={`priority ${task.priority}`}>
                        {task.priority === "high"
                          ? t("Высокий", "High")
                          : task.priority === "low"
                            ? t("Низкий", "Low")
                            : t("Обычный", "Normal")}
                      </span>
                    </div>
                    <TaskCollaboration
                      task={task}
                      onChange={(updated) =>
                        setItems((rows) =>
                          rows.map((row) =>
                            row.id === task.id ? ({ ...row, ...updated } as Task) : row,
                          ),
                        )
                      }
                      onLeave={() => setItems((rows) => rows.filter((row) => row.id !== task.id))}
                    />
                  </div>
                  <div className="taskActions">
                    <button
                      className="iconAction"
                      onClick={() => setEditing(task)}
                      aria-label={t("Изменить", "Edit")}
                    >
                      <PencilSimple size={19} />
                    </button>
                    {task.is_owner && (
                      <button
                        className="iconAction danger"
                        onClick={() => remove(task)}
                        aria-label={t("Удалить", "Delete")}
                      >
                        <Trash size={19} />
                      </button>
                    )}
                  </div>
                </>
              )}
            </article>
          ))
        )}
      </section>
      {filter === "open" && counts.completed > 0 && (
        <button
          type="button"
          className="completedDisclosure"
          onClick={() => setFilter("completed")}
        >
          <CheckCircle size={20} />
          <span>
            {t("Архив выполненных задач", "Completed task archive")}
          </span>
          <strong>{counts.completed}</strong>
        </button>
      )}
    </Shell>
  );
}

function EditTask({
  task,
  locale,
  busy,
  onCancel,
  onSave,
}: {
  task: Task;
  locale: string;
  busy: boolean;
  onCancel: () => void;
  onSave: (id: string, changes: Partial<Task>) => void;
}) {
  const { t } = useI18n();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void onSave(task.id, {
      title: String(data.get("title")),
      description: String(data.get("description")),
      due_at: dueIso(String(data.get("due_at") || "")),
      timezone: "Europe/Moscow",
      priority: String(data.get("priority")) as Priority,
    });
  }
  return (
    <form className="taskEdit" onSubmit={submit}>
      <label className="label">
        {t("Название", "Title")}
        <input
          className="field"
          name="title"
          required
          maxLength={300}
          defaultValue={task.title}
        />
      </label>
      <label className="label">
        {t("Описание", "Description")}
        <textarea
          className="field"
          name="description"
          rows={3}
          maxLength={5000}
          defaultValue={task.description}
        />
      </label>
      <div className="taskEditRow">
        <label className="label">
          {t("Срок по Москве", "Due in Moscow")}
          <input
            className="field"
            name="due_at"
            type="datetime-local"
            defaultValue={localInput(task.due_at)}
          />
        </label>
        <label className="label">
          {t("Приоритет", "Priority")}
          <select
            className="field"
            name="priority"
            defaultValue={task.priority}
          >
            <option value="low">{t("Низкий", "Low")}</option>
            <option value="normal">{t("Обычный", "Normal")}</option>
            <option value="high">{t("Высокий", "High")}</option>
          </select>
        </label>
      </div>
      <div className="taskEditActions">
        <button className="button" disabled={busy}>
          <Check size={18} />
          {t("Сохранить", "Save")}
        </button>
        <button type="button" className="button secondary" onClick={onCancel}>
          {t("Отменить", "Cancel")}
        </button>
      </div>
      <input type="hidden" value={locale} readOnly />
    </form>
  );
}
