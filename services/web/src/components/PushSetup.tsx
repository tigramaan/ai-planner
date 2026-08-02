"use client";

import { useState } from "react";
import { api } from "@/lib/api";

function decodeKey(value: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - value.length % 4) % 4);
  const binary = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function PushSetup() {
  const [label, setLabel] = useState("Включить push-уведомления");
  const [busy, setBusy] = useState(false);

  async function enable() {
    setBusy(true);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        throw new Error("Этот браузер не поддерживает Web Push");
      }
      if (await Notification.requestPermission() !== "granted") {
        throw new Error("Доступ к уведомлениям не предоставлен");
      }
      const { public_key } = await api<{ public_key: string }>("/push/public-key");
      const registration = await navigator.serviceWorker.ready;
      const current = await registration.pushManager.getSubscription();
      const subscription = current ?? await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: decodeKey(public_key),
      });
      const data = subscription.toJSON();
      if (!data.endpoint || !data.keys?.p256dh || !data.keys?.auth) {
        throw new Error("Браузер вернул неполную push-подписку");
      }
      await api("/push/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          endpoint: data.endpoint,
          p256dh: data.keys.p256dh,
          auth: data.keys.auth,
        }),
      });
      setLabel("Push-уведомления включены");
    } catch (value) {
      setLabel(value instanceof Error ? value.message : "Не удалось включить уведомления");
    } finally {
      setBusy(false);
    }
  }

  return <section className="stack"><h2>Уведомления</h2><p className="muted">Напоминания приходят при закрытой PWA, если Android не ограничил браузер.</p><button className="button secondary" type="button" disabled={busy} onClick={enable}>{busy ? "Подключаю..." : label}</button></section>;
}
