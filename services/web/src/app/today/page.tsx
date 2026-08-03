"use client";
import { useEffect, useState } from "react";
import { Agenda, AgendaItem } from "@/components/Agenda";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type TodayData={date:string;timezone:string;items:AgendaItem[]};
export default function Today(){
  const {t}=useI18n();const [data,setData]=useState<TodayData|null>(null);const [error,setError]=useState("");
  useEffect(()=>{api<TodayData>("/today").then(setData).catch(e=>setError(e.message));},[]);
  return <Shell><header className="pageHead"><div><h1>{t("Сегодня","Today")}</h1><p className="muted">{t("Время, участники, ссылки и источники в одной ленте.","Times, attendees, links, and sources in one timeline.")}</p></div></header>{error?<p className="error">{error}</p>:!data?<div className="panel">{t("Загрузка расписания...","Loading schedule...")}</div>:data.items.length===0?<div className="panel muted">{t("На сегодня ничего не запланировано.","Nothing scheduled for today.")}</div>:<Agenda items={data.items} timezone={data.timezone}/>}</Shell>;
}
