import { browserLocale } from "./i18n";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { credentials: "include", ...init, headers: { "Content-Type": "application/json", "Accept-Language": browserLocale(), ...(init?.headers ?? {}) } });
  if (response.status === 401 && typeof window !== "undefined" && !location.pathname.startsWith("/login")) location.href = "/login";
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail ?? `Ошибка API (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function uploadAudio(blob: Blob): Promise<{text:string}> {
  const form = new FormData();
  form.append("audio", blob, "voice.webm");
  const response = await fetch("/api/v1/voice/transcribe", { method:"POST", credentials:"include", headers:{"Accept-Language":browserLocale()}, body:form });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? "Не удалось распознать голос");
  return response.json();
}
