"use client";
import { useEffect, useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Item={id:string;kind:string;source:string;title:string;at:unknown;status:string};
type WeekData={start_date:string;end_date:string;timezone:string;items:Item[]};
function instant(value:unknown):string|null {
  if(typeof value==="string") return value;
  if(value&&typeof value==="object") {
    const row=value as {dateTime?:string;date?:string}; return row.dateTime??row.date??null;
  }
  return null;
}
export default function Week(){
  const {locale,t}=useI18n();const [data,setData]=useState<WeekData|null>(null);const [error,setError]=useState("");
  useEffect(()=>{api<WeekData>("/week").then(setData).catch(e=>setError(e.message));},[]);
  const groups=useMemo(()=>{const result=new Map<string,Item[]>();for(const item of data?.items??[]){const raw=instant(item.at);const key=raw?new Intl.DateTimeFormat("en-CA",{timeZone:data?.timezone,year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(raw)):"unscheduled";result.set(key,[...(result.get(key)??[]),item]);}return result;},[data]);
  return <Shell><header className="pageHead"><div><h1>{t("Неделя","Week")}</h1><p className="muted">{t("План на ближайшие семь дней.","Plan for the next seven days.")}</p></div></header>{error?<p className="error">{error}</p>:!data?<div className="panel">{t("Загрузка плана...","Loading plan...")}</div>:<section className="stack">{groups.size===0?<div className="panel muted">{t("На неделю ничего не запланировано.","Nothing scheduled this week.")}</div>:[...groups].map(([day,items])=><div className="panel timeline" key={day}><h2>{day==="unscheduled"?t("Без срока","No due date"):new Intl.DateTimeFormat(locale,{weekday:"long",day:"numeric",month:"long",timeZone:data.timezone}).format(new Date(`${day}T12:00:00Z`))}</h2>{items.map(item=><article className="timelineItem" key={`${item.source}-${item.id}`}><div className="row"><strong>{item.title}</strong><span className="status">{item.source}</span></div></article>)}</div>)}</section>}</Shell>}
