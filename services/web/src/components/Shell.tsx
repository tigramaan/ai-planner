"use client";
import { CalendarBlank, ChatCircleDots, Gear, ListChecks } from "@phosphor-icons/react";

const links = [
  ["/", "Чат", ChatCircleDots], ["/today", "Сегодня", CalendarBlank],
  ["/tasks", "Задачи", ListChecks], ["/settings", "Настройки", Gear],
] as const;

export function Shell({children}:{children:React.ReactNode}) {
  return <div className="shell"><nav className="nav" aria-label="Основная навигация"><div className="brand">UMEC Planner</div><div className="navlinks">{links.map(([href,label,Icon])=><a className="navlink" href={href} key={href}><Icon size={22} weight="duotone"/><span>{label}</span></a>)}</div></nav><main className="content">{children}</main></div>;
}
