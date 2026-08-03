"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Microphone, PaperPlaneRight, Stop } from "@phosphor-icons/react";
import { api, uploadAudio } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Message = { id?: string; role: "user" | "assistant"; text: string };
type Pending = { id: string; display_summary: string; status: string; result: { link?: string } };

export function Chat() {
  const { locale, t } = useI18n();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  function loadPending() {
    api<Pending[]>("/pending-actions").then(setPending).catch((value) => setError(value.message));
  }

  useEffect(() => {
    api<Message[]>("/chat/messages").then(setMessages).catch((value) => setError(value.message));
    loadPending();
  }, []);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setMessages((items) => [...items, { role: "user", text: value }]);
    setText("");
    setBusy(true);
    setError("");
    try {
      const result = await api<{ message: string; pending_action_id?: string }>("/chat/messages", {
        method: "POST",
        body: JSON.stringify({ text: value }),
      });
      setMessages((items) => [...items, { role: "assistant", text: result.message }]);
      if (result.pending_action_id) loadPending();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Команда не выполнена", "Command failed"));
    } finally {
      setBusy(false);
    }
  }

  async function decide(id: string, decision: "confirm" | "cancel") {
    setBusy(true);
    setError("");
    try {
      const result = await api<{ result?: { link?: string } }>(`/pending-actions/${id}/${decision}`, { method: "POST" });
      const link = result?.result?.link;
      setMessages((items) => [...items, { role: "assistant", text: link ? `${t("Готово. Ссылка на встречу:", "Done. Meeting link:")} ${link}` : decision === "confirm" ? t("Действие выполнено.", "Action completed.") : t("Действие отменено.", "Action cancelled.") }]);
      loadPending();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось обработать подтверждение", "Could not process confirmation"));
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (recording) { recorder.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const media = new MediaRecorder(stream);
      chunks.current = [];
      media.ondataavailable = (event) => chunks.current.push(event.data);
      media.onstop = async () => {
        setRecording(false);
        stream.getTracks().forEach((track) => track.stop());
        setBusy(true);
        try {
          const result = await uploadAudio(new Blob(chunks.current, { type: media.mimeType }));
          setText(result.text);
        } catch (value) {
          setError(value instanceof Error ? value.message : t("Ошибка записи", "Recording failed"));
        } finally { setBusy(false); }
      };
      recorder.current = media;
      media.start();
      setRecording(true);
    } catch { setError(t("Разрешите доступ к микрофону в браузере.", "Allow microphone access in your browser.")); }
  }

  return <section className="panel chat" aria-label={t("Чат с планировщиком", "Planner chat")}>
    <div className="messages" aria-live="polite">
      {messages.length === 0 ? <p className="muted">{t("Напишите команду или запишите голосовое сообщение.", "Type a command or record a voice message.")}</p> : messages.map((message, index) => <div className={`message ${message.role}`} key={message.id ?? index}>{message.text}</div>)}
      {pending.filter((action) => action.status === "pending").map((action) => <div className="confirmation" key={action.id}><strong>{t("Требуется подтверждение", "Confirmation required")}</strong><p>{action.display_summary}</p><div className="row"><button className="button" disabled={busy} onClick={() => decide(action.id, "confirm")}>{t("Подтвердить", "Confirm")}</button><button className="button secondary" disabled={busy} onClick={() => decide(action.id, "cancel")}>{t("Отменить", "Cancel")}</button></div></div>)}
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    <form className="composer" onSubmit={send}>
      <button type="button" className="button secondary iconButton" onClick={toggleRecording} aria-label={recording ? t("Остановить запись", "Stop recording") : t("Записать голос", "Record voice")}>{recording ? <Stop size={21}/> : <Microphone size={21}/>}</button>
      <textarea className="field" lang={locale} rows={2} value={text} onChange={(event) => setText(event.target.value)} aria-label={t("Команда", "Command")} placeholder={t("Например: поставь встречу завтра в 15:00", "For example: schedule a meeting tomorrow at 3 PM")}/>
      <button className="button iconButton" disabled={busy || !text.trim()} aria-label={t("Отправить", "Send")}><PaperPlaneRight size={21}/></button>
    </form>
  </section>;
}
