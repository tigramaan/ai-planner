"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Microphone, PaperPlaneRight, Stop } from "@phosphor-icons/react";
import { api, uploadAudio } from "@/lib/api";

type Message = { id?: string; role: "user" | "assistant"; text: string };
type Pending = { id: string; display_summary: string; status: string; result: { link?: string } };

export function Chat() {
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
      setError(value instanceof Error ? value.message : "Команда не выполнена");
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
      setMessages((items) => [...items, { role: "assistant", text: link ? `Готово. Ссылка на встречу: ${link}` : decision === "confirm" ? "Действие выполнено." : "Действие отменено." }]);
      loadPending();
    } catch (value) {
      setError(value instanceof Error ? value.message : "Не удалось обработать подтверждение");
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
          setError(value instanceof Error ? value.message : "Ошибка записи");
        } finally { setBusy(false); }
      };
      recorder.current = media;
      media.start();
      setRecording(true);
    } catch { setError("Разрешите доступ к микрофону в браузере."); }
  }

  return <section className="panel chat" aria-label="Чат с планировщиком">
    <div className="messages" aria-live="polite">
      {messages.length === 0 ? <p className="muted">Напишите команду или запишите голосовое сообщение.</p> : messages.map((message, index) => <div className={`message ${message.role}`} key={message.id ?? index}>{message.text}</div>)}
      {pending.filter((action) => action.status === "pending").map((action) => <div className="confirmation" key={action.id}><strong>Требуется подтверждение</strong><p>{action.display_summary}</p><div className="row"><button className="button" disabled={busy} onClick={() => decide(action.id, "confirm")}>Подтвердить</button><button className="button secondary" disabled={busy} onClick={() => decide(action.id, "cancel")}>Отменить</button></div></div>)}
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    <form className="composer" onSubmit={send}>
      <button type="button" className="button secondary iconButton" onClick={toggleRecording} aria-label={recording ? "Остановить запись" : "Записать голос"}>{recording ? <Stop size={21}/> : <Microphone size={21}/>}</button>
      <textarea className="field" rows={2} value={text} onChange={(event) => setText(event.target.value)} aria-label="Команда" placeholder="Например: поставь встречу завтра в 15:00"/>
      <button className="button iconButton" disabled={busy || !text.trim()} aria-label="Отправить"><PaperPlaneRight size={21}/></button>
    </form>
  </section>;
}
