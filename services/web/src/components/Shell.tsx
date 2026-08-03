"use client";
import { CalendarBlank, CalendarDots, ChatCircleDots, Gear, ListChecks } from "@phosphor-icons/react";
import { useI18n } from "@/lib/i18n";

const links = [
  ["/", "Чат", "Chat", ChatCircleDots], ["/today", "Сегодня", "Today", CalendarBlank],
  ["/week", "Неделя", "Week", CalendarDots],
  ["/tasks", "Задачи", "Tasks", ListChecks], ["/settings", "Настройки", "Settings", Gear],
] as const;

export function Shell({children}:{children:React.ReactNode}) {
  const { locale, t } = useI18n();
  return <div className="shell"><nav className="nav" aria-label={t("Основная навигация", "Main navigation")}><div className="brand">UMEC Planner</div><div className="navlinks">{links.map(([href,ru,en,Icon])=><a className="navlink" href={href} key={href}><Icon size={22} weight="duotone"/><span>{locale === "ru" ? ru : en}</span></a>)}</div></nav><main className="content">{children}</main></div>;
}
