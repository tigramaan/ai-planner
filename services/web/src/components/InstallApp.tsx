"use client";
import { DownloadSimple, ShareNetwork } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";

interface InstallPrompt extends Event {prompt:()=>Promise<void>;userChoice:Promise<{outcome:string}>}
export function InstallApp({compact=false}:{compact?:boolean}){
  const {t}=useI18n();const [prompt,setPrompt]=useState<InstallPrompt|null>(null);const [help,setHelp]=useState(false);const [installed,setInstalled]=useState(false);
  useEffect(()=>{setInstalled(matchMedia("(display-mode: standalone)").matches);const handler=(event:Event)=>{event.preventDefault();setPrompt(event as InstallPrompt);};window.addEventListener("beforeinstallprompt",handler);return()=>window.removeEventListener("beforeinstallprompt",handler);},[]);
  if(installed)return null;
  async function install(){if(prompt){await prompt.prompt();const choice=await prompt.userChoice;if(choice.outcome==="accepted")setInstalled(true);setPrompt(null);}else setHelp(true);}
  return <><button className={compact?"navlink installNav":"button installButton"} type="button" onClick={install}><DownloadSimple size={compact?22:19} weight="duotone"/><span>{t("Установить","Install")}</span></button>{help&&<div className="installOverlay" role="dialog" aria-modal="true" aria-label={t("Установка приложения","Install app")}><div className="panel installDialog"><ShareNetwork size={30}/><h2>{t("Установить AI Planner","Install AI Planner")}</h2><p>{t("На iPhone откройте меню «Поделиться» в Safari и выберите «На экран Домой». На Android откройте меню браузера и выберите «Установить приложение» или «Добавить на главный экран».","On iPhone, open Share in Safari and choose Add to Home Screen. On Android, open the browser menu and choose Install app or Add to Home screen.")}</p><button className="button" onClick={()=>setHelp(false)}>{t("Понятно","Got it")}</button></div></div>}</>;
}
