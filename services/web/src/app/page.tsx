"use client";
import { Chat } from "@/components/Chat"; import { Shell } from "@/components/Shell"; import { useI18n } from "@/lib/i18n";
export default function Home(){const {locale,t}=useI18n();const examples=locale==="ru"?[
  ["Задачи","Создай важную задачу подготовить договор к завтра 18:00"],
  ["Календарь","Создай завтра в 15:00 встречу с Анной в Яндекс Телемосте на 45 минут"],
  ["Таймер","Поставь таймер «Фокус» на 25 минут"],
  ["Почта","Покажи три важных личных письма за сегодня"],
]:[
  ["Tasks","Create a high-priority task to prepare the contract by tomorrow at 6 PM"],
  ["Calendar","Schedule a 45-minute meeting with Anna tomorrow at 3 PM in Yandex Telemost"],
  ["Timer","Start a 25-minute timer named Focus"],
  ["Mail","Show three important personal emails from today"],
];return <Shell><div className="chatPage"><div className="grid chatGrid"><Chat/><aside className="panel commandExamples"><div><h2>{t("Примеры","Examples")}</h2></div>{examples.map(([group,command])=><a className="commandExample" href={`/?draft=${encodeURIComponent(command)}`} key={command}><span>{group}</span><strong>{command}</strong></a>)}</aside></div></div></Shell>}
