"use client";

import { Bell, BellSlash, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

import { ActionToast } from "@/components/ActionToast";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type PushState =
  | "checking"
  | "idle"
  | "enabled"
  | "unsupported"
  | "denied"
  | "invalid"
  | "failed";

function decodeKey(value: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export function PushSetup({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n();
  const [state, setState] = useState<PushState>("checking");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const labels: Record<PushState, string> = {
    checking: t("Проверяю уведомления…", "Checking notifications…"),
    idle: t("Уведомления выключены", "Notifications are off"),
    enabled: t("Уведомления включены", "Notifications are on"),
    unsupported: t("Push не поддерживается", "Push is not supported"),
    denied: t("Уведомления заблокированы", "Notifications are blocked"),
    invalid: t("Push-подписка повреждена", "Push subscription is invalid"),
    failed: t("Не удалось проверить уведомления", "Could not check notifications"),
  };

  useEffect(() => {
    let active = true;
    async function inspect() {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        if (active) setState("unsupported");
        return;
      }
      if (Notification.permission === "denied") {
        if (active) setState("denied");
        return;
      }
      try {
        const [{ configured }, registration] = await Promise.all([
          api<{ configured: boolean }>("/push/status"),
          navigator.serviceWorker.ready,
        ]);
        const subscription = await registration.pushManager.getSubscription();
        if (active) setState(configured && subscription ? "enabled" : "idle");
      } catch {
        if (active) setState("failed");
      }
    }
    void inspect();
    return () => {
      active = false;
    };
  }, []);

  async function enable() {
    if (state === "denied") {
      setNotice(
        t(
          "Разрешите уведомления в настройках сайта браузера, затем обновите страницу.",
          "Allow notifications in the browser site settings, then reload the page.",
        ),
      );
      return;
    }
    setBusy(true);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        setState("unsupported");
        return;
      }
      if ((await Notification.requestPermission()) !== "granted") {
        setState(Notification.permission === "denied" ? "denied" : "idle");
        return;
      }
      const { public_key } = await api<{ public_key: string }>("/push/public-key");
      const registration = await navigator.serviceWorker.ready;
      const current = await registration.pushManager.getSubscription();
      const subscription =
        current ??
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: decodeKey(public_key),
        }));
      const data = subscription.toJSON();
      if (!data.endpoint || !data.keys?.p256dh || !data.keys?.auth) {
        setState("invalid");
        return;
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
      setNotice(t("Уведомления включены", "Notifications enabled"));
    } catch {
      setState("failed");
    } finally {
      setBusy(false);
    }
  }

  async function testDelivery() {
    setBusy(true);
    try {
      const created = await api<{ id: string }>("/push/test", { method: "POST" });
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        const result = await api<{ status: string }>(`/push/test/${created.id}`);
        if (result.status === "delivered") {
          setNotice(
            t(
              "Тестовое уведомление отправлено на это устройство.",
              "Test notification sent to this device.",
            ),
          );
          return;
        }
        if (result.status === "failed") {
          setNotice(
            t(
              "Тест не доставлен. Переподключите уведомления или проверьте ограничения батареи.",
              "Test was not delivered. Reconnect notifications or check battery restrictions.",
            ),
          );
          return;
        }
      }
      setNotice(
        t(
          "Тест отправлен, но подтверждение задерживается. Проверьте системную шторку.",
          "Test sent, but confirmation is delayed. Check system notifications.",
        ),
      );
    } catch {
      setNotice(t("Не удалось отправить тестовое уведомление.", "Could not send test notification."));
    } finally {
      setBusy(false);
    }
  }

  const Icon = state === "enabled" ? Bell : state === "idle" ? BellSlash : WarningCircle;
  const actionLabel = state === "denied"
    ? t("Как разрешить", "How to allow")
    : t("Включить", "Enable");

  if (compact) {
    if (state === "checking" || state === "enabled") return null;
    return (
      <aside className={`notificationBanner ${state}`} role="status" aria-live="polite">
        <Icon size={22} weight="duotone" />
        <div>
          <strong>{labels[state]}</strong>
          <span>{t("Таймеры и задачи не смогут прислать сигнал.", "Timers and tasks cannot alert you.")}</span>
        </div>
        {state !== "unsupported" && (
          <button className="button secondary" type="button" disabled={busy} onClick={enable}>
            {busy ? t("Подключаю…", "Enabling…") : actionLabel}
          </button>
        )}
        <ActionToast message={notice} onDismiss={() => setNotice("")} />
      </aside>
    );
  }

  return (
    <section className="stack">
      <ActionToast message={notice} onDismiss={() => setNotice("")} />
      <h2>{t("Уведомления", "Notifications")}</h2>
      <p className="muted">
        {t(
          "Статус проверяется для этого браузера. Напоминания приходят при закрытой PWA, если система не ограничила браузер.",
          "Status is checked for this browser. Alerts arrive while the PWA is closed unless the system restricts the browser.",
        )}
      </p>
      <div className={`notificationSetting ${state}`} role="status">
        <Icon size={24} weight="duotone" />
        <strong>{labels[state]}</strong>
      </div>
      {state !== "enabled" && state !== "checking" && state !== "unsupported" && (
        <button className="button secondary" type="button" disabled={busy} onClick={enable}>
          {busy ? t("Подключаю…", "Enabling…") : actionLabel}
        </button>
      )}
      {state === "enabled" && (
        <button className="button secondary" type="button" disabled={busy} onClick={testDelivery}>
          {busy ? t("Проверяю…", "Testing…") : t("Проверить уведомление", "Test notification")}
        </button>
      )}
    </section>
  );
}
