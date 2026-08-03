import { browserLocale } from "./i18n";

let refreshPromise: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "Accept-Language": browserLocale() },
    }).then((response) => response.ok).catch(() => false).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function authenticatedFetch(path: string, init: RequestInit): Promise<Response> {
  let response = await fetch(path, init);
  if (response.status === 401 && path !== "/api/v1/auth/refresh" && await refreshSession()) {
    response = await fetch(path, init);
  }
  if (response.status === 401 && typeof window !== "undefined" && !location.pathname.startsWith("/login")) {
    location.href = "/login";
  }
  return response;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`/api/v1${path}`, { credentials: "include", ...init, headers: { "Content-Type": "application/json", "Accept-Language": browserLocale(), ...(init?.headers ?? {}) } });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail ?? `Ошибка API (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function audioFilename(contentType: string): string {
  const type = contentType.split(";", 1)[0].toLowerCase();
  const extension = type === "audio/ogg" ? "ogg"
    : type === "audio/mpeg" ? "mp3"
    : type === "audio/wav" ? "wav"
    : type === "audio/mp4" || type === "audio/x-m4a" || type === "video/mp4" ? "m4a"
    : "webm";
  return `voice.${extension}`;
}

export async function uploadAudio(blob: Blob): Promise<{text:string}> {
  const form = new FormData();
  form.append("audio", blob, audioFilename(blob.type));
  const response = await authenticatedFetch("/api/v1/voice/transcribe", { method:"POST", credentials:"include", headers:{"Accept-Language":browserLocale()}, body:form });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? "Не удалось распознать голос");
  return response.json();
}
