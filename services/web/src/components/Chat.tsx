"use client";

import { FormEvent, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Microphone, PaperPlaneRight, Stop } from "@phosphor-icons/react";
import { api, uploadAudio } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Message = { id?: string; role: "user" | "assistant"; text: string };
type Pending = { id: string; display_summary: string; status: string; result: { link?: string } };
const appendMessage = (items: Message[], message: Message) => [...items, message].slice(-50);

export function Chat() {
  const { locale, t } = useI18n();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const waveform = useRef<HTMLCanvasElement | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const animationFrame = useRef<number | null>(null);
  const messageList = useRef<HTMLDivElement | null>(null);
  const stickToBottom = useRef(true);

  function loadPending() {
    api<Pending[]>("/pending-actions").then(setPending).catch((value) => setError(value.message));
  }

  useEffect(() => {
    api<Message[]>("/chat/messages").then(setMessages).catch((value) => setError(value.message));
    loadPending();
    return () => stopVisualization();
  }, []);

  useLayoutEffect(() => {
    const list = messageList.current;
    if (list && stickToBottom.current) list.scrollTop = list.scrollHeight;
  }, [messages, pending]);

  function trackScroll() {
    const list = messageList.current;
    if (!list) return;
    stickToBottom.current = list.scrollHeight - list.scrollTop - list.clientHeight < 80;
  }

  function stopVisualization() {
    if (animationFrame.current !== null) cancelAnimationFrame(animationFrame.current);
    animationFrame.current = null;
    if (audioContext.current) void audioContext.current.close();
    audioContext.current = null;
  }

  function startVisualization(stream: MediaStream) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 128;
    context.createMediaStreamSource(stream).connect(analyser);
    audioContext.current = context;
    const levels = new Uint8Array(analyser.frequencyBinCount);
    const draw = () => {
      const canvas = waveform.current;
      if (canvas) {
        const ratio = window.devicePixelRatio || 1;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
          canvas.width = width * ratio;
          canvas.height = height * ratio;
        }
        const paint = canvas.getContext("2d");
        if (paint) {
          analyser.getByteFrequencyData(levels);
          paint.setTransform(ratio, 0, 0, ratio, 0, 0);
          paint.clearRect(0, 0, width, height);
          paint.fillStyle = getComputedStyle(canvas).color;
          const bars = 22;
          const gap = 3;
          const barWidth = Math.max(2, (width - gap * (bars - 1)) / bars);
          for (let index = 0; index < bars; index += 1) {
            const value = levels[Math.floor(index * levels.length / bars)] / 255;
            const barHeight = Math.max(3, value * height);
            paint.fillRect(index * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);
          }
        }
      }
      animationFrame.current = requestAnimationFrame(draw);
    };
    draw();
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    stickToBottom.current = true;
    setMessages((items) => appendMessage(items, { role: "user", text: value }));
    setText("");
    setBusy(true);
    setError("");
    try {
      const result = await api<{ message: string; pending_action_id?: string }>("/chat/messages", {
        method: "POST",
        body: JSON.stringify({ text: value }),
      });
      setMessages((items) => appendMessage(items, { role: "assistant", text: result.message }));
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
      stickToBottom.current = true;
      setMessages((items) => appendMessage(items, { role: "assistant", text: link ? `${t("Готово. Ссылка на встречу:", "Done. Meeting link:")} ${link}` : decision === "confirm" ? t("Действие выполнено.", "Action completed.") : t("Действие отменено.", "Action cancelled.") }));
      loadPending();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось обработать подтверждение", "Could not process confirmation"));
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (recording) {
      setRecording(false);
      stopVisualization();
      if (recorder.current?.state !== "inactive") recorder.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const supportedType = ["audio/webm;codecs=opus", "audio/mp4;codecs=mp4a.40.2", "audio/mp4", "audio/webm"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      const media = new MediaRecorder(stream, supportedType ? { mimeType: supportedType } : undefined);
      chunks.current = [];
      media.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      media.onstop = async () => {
        setRecording(false);
        stopVisualization();
        stream.getTracks().forEach((track) => track.stop());
        setBusy(true);
        setTranscribing(true);
        try {
          const type = media.mimeType || chunks.current[0]?.type || "application/octet-stream";
          const result = await uploadAudio(new Blob(chunks.current, { type }));
          setText(result.text);
        } catch (value) {
          setError(value instanceof Error ? value.message : t("Ошибка записи", "Recording failed"));
        } finally { setBusy(false); setTranscribing(false); }
      };
      recorder.current = media;
      media.start();
      setRecording(true);
      startVisualization(stream);
    } catch { setError(t("Разрешите доступ к микрофону в браузере.", "Allow microphone access in your browser.")); }
  }

  return <section className="panel chat" aria-label={t("Чат с планировщиком", "Planner chat")}>
    <div className="messages" ref={messageList} onScroll={trackScroll} aria-live="polite">
      {messages.length === 0 ? <p className="muted">{t("Напишите команду или запишите голосовое сообщение.", "Type a command or record a voice message.")}</p> : messages.map((message, index) => <div className={`message ${message.role}`} key={message.id ?? index}>{message.text}</div>)}
      {pending.filter((action) => action.status === "pending").map((action) => <div className="confirmation" key={action.id}><strong>{t("Требуется подтверждение", "Confirmation required")}</strong><p>{action.display_summary}</p><div className="row"><button className="button" disabled={busy} onClick={() => decide(action.id, "confirm")}>{t("Подтвердить", "Confirm")}</button><button className="button secondary" disabled={busy} onClick={() => decide(action.id, "cancel")}>{t("Отменить", "Cancel")}</button></div></div>)}
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    {(recording || transcribing) && <div className="voiceStatus" role="status">
      <span>{recording ? t("Идёт запись", "Recording") : t("Распознаю запись", "Transcribing")}</span>
      {recording && <canvas ref={waveform} className="waveform" aria-hidden="true"/>}
    </div>}
    <form className="composer" onSubmit={send}>
      <button type="button" className={`button secondary iconButton${recording ? " recordingButton" : ""}`} disabled={transcribing} onClick={toggleRecording} aria-pressed={recording} aria-label={recording ? t("Остановить запись", "Stop recording") : t("Записать голос", "Record voice")}>{recording ? <Stop size={21}/> : <Microphone size={21}/>}</button>
      <textarea className="field" lang={locale} rows={2} value={text} onChange={(event) => setText(event.target.value)} aria-label={t("Команда", "Command")} placeholder={t("Например: поставь встречу завтра в 15:00", "For example: schedule a meeting tomorrow at 3 PM")}/>
      <button className="button iconButton" disabled={busy || !text.trim()} aria-label={t("Отправить", "Send")}><PaperPlaneRight size={21}/></button>
    </form>
  </section>;
}
