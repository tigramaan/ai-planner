"use client";
import { useEffect, useState } from "react";
import { CalendarBlank, CalendarDots, CaretLeft, CaretRight, ChatCircleDots, Gear, ListChecks, Scan, SignOut } from "@phosphor-icons/react";
import { useI18n } from "@/lib/i18n";
import { InstallApp } from "@/components/InstallApp";
import { PushSetup } from "@/components/PushSetup";
import { api } from "@/lib/api";

const links = [
  ["/", "Чат", "Chat", ChatCircleDots], ["/today", "Сегодня", "Today", CalendarBlank],
  ["/week", "Неделя", "Week", CalendarDots],
  ["/tasks", "Задачи", "Tasks", ListChecks], ["/commitments", "Контур", "Radar", Scan],
  ["/settings", "Настройки", "Settings", Gear],
] as const;

export function Shell({children}:{children:React.ReactNode}) {
  const { locale, t } = useI18n();
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => setCollapsed(localStorage.getItem("planner-nav-collapsed") === "true"), []);
  function toggleNavigation() {
    setCollapsed((value) => {
      localStorage.setItem("planner-nav-collapsed", String(!value));
      return !value;
    });
  }
  async function logout() { await api("/auth/logout", {method:"POST"}).catch(() => undefined); location.href="/login"; }
  return <div className={`shell${collapsed ? " navCollapsed" : ""}`}><nav className="nav" aria-label={t("Основная навигация", "Main navigation")}><div className="navTop"><a className="brand" href="/" aria-label="UMEC"><img className="brandLogo" src="/umec-space-logo.png" alt="UMEC"/></a><button className="navCollapse" type="button" onClick={toggleNavigation} aria-label={collapsed ? t("Развернуть меню", "Expand menu") : t("Свернуть меню", "Collapse menu")}>{collapsed ? <CaretRight size={19}/> : <CaretLeft size={19}/>}</button></div><div className="navlinks">{links.map(([href,ru,en,Icon])=><a className="navlink" href={href} title={collapsed ? (locale === "ru" ? ru : en) : undefined} key={href}><Icon size={22} weight="duotone"/><span>{locale === "ru" ? ru : en}</span></a>)}<InstallApp compact/><button className="navlink installNav" type="button" onClick={logout} title={collapsed ? t("Выйти", "Sign out") : undefined}><SignOut size={22} weight="duotone"/><span>{t("Выйти", "Sign out")}</span></button></div></nav><main className="content"><PushSetup compact/>{children}</main></div>;
}
