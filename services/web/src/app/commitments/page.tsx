"use client";

import { ArrowRight, CheckCircle, Scan, WarningCircle } from "@phosphor-icons/react";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Category = "mine" | "awaiting_me" | "awaiting_other";
type Item = {
  source: "incoming" | "sent";
  category: Category;
  title: string;
  counterparty: string;
  evidence: string;
  deadline: string | null;
  suggested_action: string;
  covered: boolean;
  confidence: "high" | "medium";
  message_id: string;
  received_at: string;
};
type Result = { window_days: number; items: Item[] };

export default function CommitmentsPage() {
  const { t } = useI18n();
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function analyze() {
    setBusy(true);
    setError("");
    try {
      setResult(await api<Result>("/commitments/analyze", { method: "POST" }));
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось выполнить проверку", "Analysis failed"));
    } finally {
      setBusy(false);
    }
  }
  const groups: [Category, string, string][] = [
    ["mine", t("Я обещал", "I committed"), t("Обязательства, которые вы взяли на себя.", "Commitments you made.")],
    ["awaiting_me", t("Ждут от меня", "Waiting on me"), t("Вопросы и просьбы, где нужен ваш следующий шаг.", "Requests that need your next step.")],
    ["awaiting_other", t("Жду я", "Waiting on others"), t("Ваши запросы, на которые ещё нужен ответ.", "Your requests still awaiting a response.")],
  ];
  return <Shell><div className="commitmentPage">
    <header className="pageHead"><div><h1>{t("Контур обязательств", "Commitment radar")}</h1><p className="muted">{t("Проверяет последние 30 дней почты и сверяет договорённости с задачами и календарём.", "Checks 30 days of mail against your tasks and calendar.")}</p></div><button className="button primary" type="button" disabled={busy} onClick={analyze}><Scan size={20}/>{busy ? t("Проверяю…", "Checking…") : t("Что зависло?", "What is stuck?")}</button></header>
    <div className="commitmentNotice"><WarningCircle size={22}/><span>{t("AI показывает только явно найденные договорённости. Ничего не создаётся и не отправляется без вашего подтверждения.", "AI shows only explicit commitments. Nothing is created or sent without your confirmation.")}</span></div>
    {error && <p className="error" role="alert">{error}</p>}
    {busy && <div className="commitmentLoading" aria-label={t("Анализ почты", "Analyzing mail")}><i/><i/><i/></div>}
    {!busy && result && result.items.length === 0 && <div className="panel commitmentEmpty"><CheckCircle size={38} weight="duotone"/><strong>{t("Явных зависших обязательств не найдено", "No explicit stuck commitments found")}</strong><span className="muted">{t("Это не гарантирует отсутствие договорённостей — AI намеренно не додумывает их.", "This does not guarantee there are none—the AI intentionally avoids guessing.")}</span></div>}
    {!busy && result && result.items.length > 0 && <div className="commitmentGroups">{groups.map(([category, title, description]) => {
      const items = result.items.filter((item) => item.category === category);
      if (!items.length) return null;
      return <section className="commitmentGroup" key={category}><header><div><h2>{title}</h2><p className="muted">{description}</p></div><span>{items.length}</span></header><div className="commitmentList">{items.map((item, index) => <article className="commitmentItem" key={`${item.message_id}-${index}`}><div className="commitmentMain"><div className="commitmentFlags"><span>{item.counterparty}</span>{item.deadline && <span>{item.deadline}</span>}{!item.covered && <span className="risk">{t("Нет в плане", "Not planned")}</span>}</div><h3>{item.title}</h3><p>{item.evidence}</p><small className="muted">{item.suggested_action}</small></div><a className="button subtle" href={`/?draft=${encodeURIComponent(actionDraft(item, t))}`}>{t("Разобрать", "Handle")}<ArrowRight size={17}/></a></article>)}</div></section>;
    })}</div>}
    {!busy && !result && <div className="panel commitmentEmpty"><Scan size={42} weight="duotone"/><strong>{t("Договорённости между приложениями", "Commitments across apps")}</strong><span className="muted">{t("Запустите проверку, чтобы найти обещания, запросы без ответа и риски срыва.", "Run a check to find promises, unanswered requests, and delivery risks.")}</span></div>}
  </div></Shell>;
}

function actionDraft(item: Item, t: (ru: string, en: string) => string) {
  if (item.category === "awaiting_other") return t(`Подготовь вежливый follow-up: ${item.title}. Контекст: ${item.evidence}`, `Draft a polite follow-up: ${item.title}. Context: ${item.evidence}`);
  return t(`Помоги разобрать обязательство «${item.title}». Предложи задачу со сроком, но сначала покажи мне проект. Контекст: ${item.evidence}`, `Help handle “${item.title}”. Propose a dated task but show me the draft first. Context: ${item.evidence}`);
}
