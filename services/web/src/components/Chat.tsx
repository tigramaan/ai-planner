"use client";

import { FormEvent, KeyboardEvent, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Microphone, PaperPlaneRight, Stop } from "@phosphor-icons/react";
import { api, uploadAudio } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Message = { id?: string; role: "user" | "assistant"; text: string; created_at?: string };
type Pending = { id: string; display_summary: string; status: string; result: { report?: string } };
type Timer = { id: string; title: string; ends_at: string; status: string };
const appendMessage = (items: Message[], message: Message) => [...items, message].slice(-50);

export function shouldAutoSendTranscript(value: string) {
  const text = value.trim();
  const words = text.split(/\s+/u);
  const punctuation = text.match(/[.!?;,]/gu)?.length ?? 0;
  return Boolean(text) && text.length <= 110 && words.length <= 16 && punctuation <= 1 && !text.includes("\n");
}

export function shouldStopForSilence(hasSpeech: boolean, silenceMs: number, recordingMs: number) {
  return hasSpeech && silenceMs >= 1400 && recordingMs >= 1800;
}

function countdown(endsAt: string, now: number) {
  const seconds = Math.max(0, Math.ceil((new Date(endsAt).getTime() - now) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return hours ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}` : `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function MessageText({text}:{text:string}) {
  const parts=text.split(/(https:\/\/[^\s]+)/g);
  return <>{parts.map((part,index)=>part.startsWith("https://")?<a className="messageLink" href={part.replace(/[.,;]+$/,"")} target="_blank" rel="noreferrer" key={index}>{part.replace(/[.,;]+$/,"")}</a>:part)}</>;
}

export function Chat() {
  const { locale, t } = useI18n();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [timers, setTimers] = useState<Timer[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [replyPending, setReplyPending] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const waveform = useRef<HTMLCanvasElement | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const animationFrame = useRef<number | null>(null);
  const messageList = useRef<HTMLDivElement | null>(null);
  const composerInput = useRef<HTMLTextAreaElement | null>(null);
  const stickToBottom = useRef(true);
  const busyRef = useRef(false);
  const speechDetected = useRef(false);
  const silenceStarted = useRef<number | null>(null);
  const recordingStarted = useRef(0);

  async function syncMessages() {
    if (busyRef.current) return;
    const rows = await api<Message[]>("/chat/messages");
    setMessages(rows);
  }

  async function syncTimers() {
    setTimers(await api<Timer[]>("/timers"));
  }

  function loadPending() {
    api<Pending[]>("/pending-actions").then(setPending).catch((value) => setError(value.message));
  }

  useEffect(() => {
    const draft = new URLSearchParams(window.location.search).get("draft");
    if (draft) setText(draft);
    void syncMessages().catch((value) => setError(value.message));
    void syncTimers().catch((value) => setError(value.message));
    const poll = window.setInterval(() => {
      void syncMessages().catch(() => undefined);
      void syncTimers().catch(() => undefined);
    }, 5000);
    const ticker = window.setInterval(() => setNow(Date.now()), 1000);
    loadPending();
    return () => {
      window.clearInterval(poll);
      window.clearInterval(ticker);
      stopVisualization();
    };
  }, []);

  useLayoutEffect(() => {
    const list = messageList.current;
    if (list && stickToBottom.current) list.scrollTop = list.scrollHeight;
  }, [messages, pending, replyPending]);

  useLayoutEffect(() => {
    const input = composerInput.current;
    if (!input) return;
    input.style.height = "0px";
    input.style.height = `${Math.min(input.scrollHeight, 240)}px`;
  }, [text]);

  function composerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void send();
    }
  }

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
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 128;
    context.createMediaStreamSource(stream).connect(analyser);
    audioContext.current = context;
    const levels = new Uint8Array(analyser.frequencyBinCount);
    const samples = new Uint8Array(analyser.fftSize);
    speechDetected.current = false;
    silenceStarted.current = null;
    recordingStarted.current = performance.now();
    const draw = () => {
      analyser.getByteTimeDomainData(samples);
      const rms = Math.sqrt(samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / samples.length);
      const current = performance.now();
      if (rms >= 0.035) {
        speechDetected.current = true;
        silenceStarted.current = null;
      } else if (speechDetected.current) {
        silenceStarted.current ??= current;
        if (shouldStopForSilence(true, current - silenceStarted.current, current - recordingStarted.current)) {
          if (recorder.current?.state !== "inactive") recorder.current?.stop();
          return;
        }
      }
      const canvas = reduceMotion ? null : waveform.current;
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

  async function submit(value: string) {
    if (!value) return;
    const sentAt = new Date().toISOString();
    stickToBottom.current = true;
    setMessages((items) => appendMessage(items, { role: "user", text: value, created_at: sentAt }));
    setText("");
    setBusy(true);
    busyRef.current = true;
    setReplyPending(true);
    setError("");
    try {
      const result = await api<{ message: string; pending_action_id?: string }>("/chat/messages", {
        method: "POST",
        body: JSON.stringify({ text: value }),
      });
      setMessages((items) => appendMessage(items, { role: "assistant", text: result.message, created_at: new Date().toISOString() }));
      if (result.pending_action_id) loadPending();
      void syncTimers().catch(() => undefined);
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Команда не выполнена", "Command failed"));
    } finally {
      setReplyPending(false);
      setBusy(false);
      busyRef.current = false;
    }
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    await submit(value);
  }

  async function decide(id: string, decision: "confirm" | "cancel") {
    setBusy(true);
    busyRef.current = true;
    setError("");
    try {
      const result = await api<{ result?: { report?: string } }>(`/pending-actions/${id}/${decision}`, { method: "POST" });
      stickToBottom.current = true;
      setMessages((items) => appendMessage(items, { role: "assistant", text: decision === "confirm" ? result?.result?.report || t("Действие выполнено.", "Action completed.") : t("Действие отменено.", "Action cancelled."), created_at: new Date().toISOString() }));
      loadPending();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Не удалось обработать подтверждение", "Could not process confirmation"));
    } finally {
      setBusy(false);
      busyRef.current = false;
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
          const transcript = result.text.trim();
          if (shouldAutoSendTranscript(transcript)) {
            setBusy(false);
            setTranscribing(false);
            await submit(transcript);
          } else {
            setText(transcript);
          }
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
      {messages.length === 0 ? <p className="muted">{t("Напишите команду или запишите голосовое сообщение.", "Type a command or record a voice message.")}</p> : messages.map((message, index) => <div className={`message ${message.role}`} key={message.id ?? index}><MessageText text={message.text}/>{message.created_at && <time className="messageTime" dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}</time>}</div>)}
      {replyPending && <div className="message assistant typingIndicator" role="status" aria-label={t("Планировщик печатает", "Planner is typing")}><span>{t("Печатает", "Typing")}</span><i/><i/><i/></div>}
      {pending.filter((action) => action.status === "pending").map((action) => <div className="confirmation" key={action.id}><strong>{t("Требуется подтверждение", "Confirmation required")}</strong><p>{action.display_summary}</p><div className="row"><button className="button" disabled={busy} onClick={() => decide(action.id, "confirm")}>{t("Подтвердить", "Confirm")}</button><button className="button secondary" disabled={busy} onClick={() => decide(action.id, "cancel")}>{t("Отменить", "Cancel")}</button></div></div>)}
    </div>
    {timers.some((timer) => new Date(timer.ends_at).getTime() > now) && <div className="activeTimers" aria-label={t("Активные таймеры", "Active timers")}>
      {timers.filter((timer) => new Date(timer.ends_at).getTime() > now).map((timer) => <article className="activeTimer" role="timer" key={timer.id}>
        <strong>{timer.title}</strong>
        <span>{countdown(timer.ends_at, now)}</span>
        <small>{t("до", "until")} {new Date(timer.ends_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}</small>
      </article>)}
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
    {(recording || transcribing) && <div className="voiceStatus" role="status">
      <span>{recording ? t("Идёт запись", "Recording") : t("Распознаю запись", "Transcribing")}</span>
      {recording && <canvas ref={waveform} className="waveform" aria-hidden="true"/>}
    </div>}
    <form className="composer" onSubmit={send}>
      <textarea ref={composerInput} className="composerInput" lang={locale} rows={1} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={composerKeyDown} aria-label={t("Команда", "Command")} placeholder={t("Напишите команду планировщику", "Write a command to the planner")}/>
      <div className="composerActions">
        <button type="button" className={`composerButton voiceButton${recording ? " recordingButton" : ""}`} disabled={transcribing} onClick={toggleRecording} aria-pressed={recording} aria-label={recording ? t("Остановить запись", "Stop recording") : t("Записать голос", "Record voice")}>{recording ? <Stop size={25}/> : <Microphone size={25}/>}</button>
        <span className="composerHint">{t("Ctrl + Enter, чтобы отправить", "Ctrl + Enter to send")}</span>
        <button className="composerButton sendButton" disabled={busy || !text.trim()} aria-label={t("Отправить", "Send")}><PaperPlaneRight size={25} weight="bold"/></button>
      </div>
    </form>
  </section>;
}
