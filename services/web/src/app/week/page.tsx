"use client";
import { useEffect, useMemo, useState } from "react";
import { Agenda, AgendaItem, instant } from "@/components/Agenda";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type WeekData={start_date:string;end_date:string;timezone:string;items:AgendaItem[]};
function dateKey(value:unknown,timezone:string):string {const raw=instant(value);if(!raw)return "unscheduled";const parts=new Intl.DateTimeFormat("en",{timeZone:timezone,year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(raw));const get=(type:string)=>parts.find(x=>x.type===type)?.value;return `${get("year")}-${get("month")}-${get("day")}`;}
export default function Week(){
  const {locale,t}=useI18n();const [data,setData]=useState<WeekData|null>(null);const [error,setError]=useState("");
  useEffect(()=>{api<WeekData>("/week").then(setData).catch(e=>setError(e.message));},[]);
  const groups=useMemo(()=>{const result=new Map<string,AgendaItem[]>();for(const item of data?.items??[]){const key=dateKey(item.start,data?.timezone??"Europe/Moscow");result.set(key,[...(result.get(key)??[]),item]);}return result;},[data]);
  return <Shell><header className="pageHead"><div><h1>{t("Неделя","Week")}</h1><p className="muted">{t("Подробный план на ближайшие семь дней.","Detailed plan for the next seven days.")}</p></div></header>{error?<p className="error">{error}</p>:!data?<div className="panel">{t("Загрузка плана...","Loading plan...")}</div>:<section className="stack">{groups.size===0?<div className="panel muted">{t("На неделю ничего не запланировано.","Nothing scheduled this week.")}</div>:[...groups].map(([day,items])=><section key={day}><h2 className="dayTitle">{day==="unscheduled"?t("Без срока","No due date"):new Intl.DateTimeFormat(locale,{weekday:"long",day:"numeric",month:"long",timeZone:data.timezone}).format(new Date(`${day}T12:00:00Z`))}</h2><Agenda items={items} timezone={data.timezone}/></section>)}</section>}</Shell>;
}
