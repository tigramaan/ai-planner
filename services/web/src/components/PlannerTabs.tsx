"use client";
import { useI18n } from "@/lib/i18n";

export function PlannerTabs({ active }: { active: "tasks" | "reminders" }) {
  const { t } = useI18n();
  return <nav className="plannerTabs" aria-label={t("Раздел планирования", "Planning section")}>
    <a className={active === "tasks" ? "active" : ""} href="/tasks">{t("Задачи", "Tasks")}</a>
    <a className={active === "reminders" ? "active" : ""} href="/reminders">{t("Напоминания", "Reminders")}</a>
  </nav>;
}
