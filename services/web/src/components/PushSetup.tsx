"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

function decodeKey(value: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - value.length % 4) % 4);
  const binary = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function PushSetup() {
  const { t } = useI18n();
  const [state, setState] = useState<"idle" | "enabled" | "unsupported" | "denied" | "invalid" | "failed">("idle");
  const [busy, setBusy] = useState(false);
  const labels = {
    idle: t("Включить push-уведомления", "Enable push notifications"),
    enabled: t("Push-уведомления включены", "Push notifications enabled"),
    unsupported: t("Этот браузер не поддерживает Web Push", "This browser does not support Web Push"),
    denied: t("Доступ к уведомлениям не предоставлен", "Notification permission was not granted"),
    invalid: t("Браузер вернул неполную push-подписку", "The browser returned an incomplete push subscription"),
    failed: t("Не удалось включить уведомления", "Could not enable notifications"),
  };

  async function enable() {
    setBusy(true);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        setState("unsupported"); throw new Error("unsupported");
      }
      if (await Notification.requestPermission() !== "granted") {
        setState("denied"); throw new Error("denied");
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
        setState("invalid"); throw new Error("invalid");
      }
      await api("/push/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          endpoint: data.endpoint,
          p256dh: data.keys.p256dh,
          auth: data.keys.auth,
        }),
      });
      setState("enabled");
    } catch {
      setState((current) => current === "idle" ? "failed" : current);
    } finally {
      setBusy(false);
    }
  }

  return <section className="stack"><h2>{t("Уведомления", "Notifications")}</h2><p className="muted">{t("Напоминания приходят при закрытой PWA, если Android не ограничил браузер.", "Reminders arrive while the PWA is closed unless Android restricts the browser.")}</p><button className="button secondary" type="button" disabled={busy} onClick={enable}>{busy ? t("Подключаю...", "Enabling...") : labels[state]}</button></section>;
}
