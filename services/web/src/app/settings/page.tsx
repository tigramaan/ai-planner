"use client";

import { FormEvent, useEffect, useState } from "react";
import { PushSetup } from "@/components/PushSetup";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Integration = {
  provider: string;
  status: string;
  account_email?: string;
  scopes: string[];
  configured?: boolean;
  source?: string;
};
type Preferences = {
  default_calendar: string;
  default_mail: string;
  default_conference: string;
  fallback_teams_url: string;
  fallback_telemost_url: string;
};

export default function Settings() {
  const { t } = useI18n();
  const [items, setItems] = useState<Integration[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [preferences, setPreferences] = useState<Preferences>({
    default_calendar: "google",
    default_mail: "google",
    default_conference: "none",
    fallback_teams_url: "",
    fallback_telemost_url: "",
  });
  const state = (provider: string) =>
    items.find((item) => item.provider === provider);
  const providerState = (provider: string) => {
    const item = state(provider);
    return (
      item?.account_email ||
      (item?.status === "connected" ? t("Подключено", "Connected") : "")
    );
  };
  function load() {
    Promise.all([
      api<Integration[]>("/integrations"),
      api<Preferences>("/preferences"),
    ])
      .then(([connected, saved]) => {
        setItems(connected);
        setPreferences(saved);
      })
      .catch((value) => setError(value.message));
  }
  useEffect(load, []);

  async function connect(provider: string, scopes: string[]) {
    setError("");
    try {
      const result = await api<{ authorization_url: string }>(
        `/integrations/${provider}/oauth/start`,
        { method: "POST", body: JSON.stringify({ scopes }) },
      );
      location.href = result.authorization_url;
    } catch (value) {
      setError(
        value instanceof Error
          ? value.message
          : t("Ошибка OAuth", "OAuth error"),
      );
    }
  }

  async function saveAI(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/integrations/openai", {
        method: "POST",
        body: JSON.stringify({
          api_key: data.get("api_key"),
          model: data.get("model"),
          transcription_model: "whisper-1",
        }),
      });
      setNotice(
        t(
          "OpenAI подключён. Ключ сохранён в зашифрованном виде.",
          "OpenAI connected. The key is stored encrypted.",
        ),
      );
      load();
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    }
  }

  async function password(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: data.get("current"),
          new_password: data.get("next"),
        }),
      });
      location.href = "/login";
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const saved = await api<Preferences>("/preferences", {
        method: "PUT",
        body: JSON.stringify({
          default_calendar: data.get("default_calendar"),
          default_mail: data.get("default_mail"),
          default_conference: data.get("default_conference"),
          fallback_teams_url: data.get("fallback_teams_url"),
          fallback_telemost_url: data.get("fallback_telemost_url"),
        }),
      });
      setPreferences(saved);
      setNotice(
        t("Настройки по умолчанию сохранены.", "Default providers saved."),
      );
    } catch (value) {
      setError(value instanceof Error ? value.message : t("Ошибка", "Error"));
    }
  }

  const disconnected = t("Не подключено", "Not connected");
  return (
    <Shell>
      <header className="pageHead">
        <div>
          <h1>{t("Настройки", "Settings")}</h1>
          <p className="muted">
            {t(
              "Секреты после сохранения нельзя прочитать обратно.",
              "Saved secrets cannot be read back.",
            )}
          </p>
        </div>
      </header>
      {notice && <p>{notice}</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="grid">
        <section className="panel stack">
          <h2>{t("Интеграции", "Integrations")}</h2>
          <div className="integration stack">
            <div>
              <strong>Google Calendar & Contacts</strong>
              <div className="status">
                {providerState("google") || disconnected}
              </div>
            </div>
            <button
              className="button secondary"
              onClick={() =>
                connect("google", [
                  "identity",
                  "calendar.read",
                  "calendar.write",
                  "contacts.read",
                ])
              }
            >
              {t("Авторизовать календарь", "Authorize calendar")}
            </button>
            <button
              className="button secondary"
              onClick={() =>
                connect("google", [
                  "identity",
                  "gmail.read",
                  "gmail.compose",
                  "gmail.send",
                ])
              }
            >
              {t("Авторизовать Gmail", "Authorize Gmail")}
            </button>
          </div>
          <div className="integration stack">
            <div>
              <strong>Microsoft 365 & Teams</strong>
              <div className="status">
                {providerState("microsoft") || disconnected}
              </div>
            </div>
            <button
              className="button secondary"
              onClick={() =>
                connect("microsoft", [
                  "identity",
                  "calendar",
                  "contacts",
                  "teams",
                  "mail.read",
                  "mail.write",
                ])
              }
            >
              {t("Авторизовать Teams", "Authorize Teams")}
            </button>
          </div>
          <div className="integration stack">
            <div>
              <strong>Zoom</strong>
              <div className="status">{providerState("zoom") || disconnected}</div>
            </div>
            <button
              className="button secondary"
              onClick={() => connect("zoom", ["identity", "meeting"])}
            >
              {t("Авторизовать Zoom", "Authorize Zoom")}
            </button>
          </div>
          <div className="integration stack">
            <div>
              <strong>Яндекс 360</strong>
              <div className="status">
                {t(
                  "Требуется сервисное приложение организации",
                  "Requires an organization service app",
                )}
              </div>
            </div>
            <p className="muted">
              {t(
                "Календарь и почта подключаются через CalDAV/IMAP; API Телемоста доступен только Яндекс 360 для бизнеса.",
                "Calendar and mail use CalDAV/IMAP; Telemost API is limited to Yandex 360 Business.",
              )}
            </p>
          </div>
          <form className="form" onSubmit={savePreferences}>
            <h2>{t("Сервисы по умолчанию", "Default services")}</h2>
            <label className="label">
              {t("Календарь", "Calendar")}
              <select
                className="field"
                name="default_calendar"
                value={preferences.default_calendar}
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    default_calendar: e.target.value,
                  })
                }
              >
                <option value="google">Google Calendar</option>
                <option value="microsoft">Microsoft Outlook</option>
                <option value="yandex">Яндекс Календарь</option>
                <option value="local">{t("Локальный", "Local")}</option>
              </select>
            </label>
            <label className="label">
              {t("Почта", "Mail")}
              <select
                className="field"
                name="default_mail"
                value={preferences.default_mail}
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    default_mail: e.target.value,
                  })
                }
              >
                <option value="google">Gmail</option>
                <option value="microsoft">Outlook</option>
                <option value="yandex">Яндекс Почта</option>
              </select>
            </label>
            <label className="label">
              {t("Видеосвязь", "Video service")}
              <select
                className="field"
                name="default_conference"
                value={preferences.default_conference}
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    default_conference: e.target.value,
                  })
                }
              >
                <option value="none">
                  {t("Не создавать", "Do not create")}
                </option>
                <option value="google">Google Meet</option>
                <option value="microsoft">Microsoft Teams</option>
                <option value="yandex">Яндекс Телемост</option>
                <option value="zoom">Zoom</option>
              </select>
            </label>
            <p className="muted">
              {t(
                "Видеосвязь используется только если вы явно попросили онлайн-встречу.",
                "Video is used only when you explicitly request an online meeting.",
              )}
            </p>
            <label className="label">
              {t("Постоянная ссылка Teams", "Permanent Teams link")}
              <input
                className="field"
                name="fallback_teams_url"
                type="url"
                value={preferences.fallback_teams_url}
                placeholder="https://teams.microsoft.com/l/meetup-join/..."
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    fallback_teams_url: e.target.value,
                  })
                }
              />
            </label>
            <label className="label">
              {t("Постоянная ссылка Телемоста", "Permanent Telemost link")}
              <input
                className="field"
                name="fallback_telemost_url"
                type="url"
                value={preferences.fallback_telemost_url}
                placeholder="https://telemost.yandex.ru/j/..."
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    fallback_telemost_url: e.target.value,
                  })
                }
              />
            </label>
            <p className="muted">
              {t(
                "Если API видеосервиса недоступен, постоянная ссылка будет добавлена в событие. Любой получивший её сможет использовать общую комнату повторно.",
                "If the video API is unavailable, the permanent link is added to the event. Anyone who has it can reuse the shared room.",
              )}
            </p>
            <button className="button">{t("Сохранить", "Save")}</button>
          </form>
          <form className="form" onSubmit={saveAI}>
            <h2>OpenAI</h2>
            {state("openai")?.configured && (
              <p className="status">
                {t(
                  "Ключ из Telegram-бота подключён на сервере.",
                  "The key from the Telegram bot is configured on the server.",
                )}
              </p>
            )}
            <label className="label">
              API key
              <input
                className="field"
                name="api_key"
                type="password"
                autoComplete="off"
                required
              />
            </label>
            <label className="label">
              {t("Модель", "Model")}
              <input
                className="field"
                name="model"
                defaultValue="gpt-5-mini"
                required
              />
            </label>
            <button className="button">
              {t("Заменить ключ OpenAI", "Replace OpenAI key")}
            </button>
          </form>
        </section>
        <section className="panel stack">
          <PushSetup />
          <form className="form" onSubmit={password}>
            <h2>{t("Смена пароля", "Change password")}</h2>
            <label className="label">
              {t("Текущий пароль", "Current password")}
              <input
                className="field"
                name="current"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <label className="label">
              {t("Новый пароль", "New password")}
              <input
                className="field"
                name="next"
                type="password"
                minLength={12}
                autoComplete="new-password"
                required
              />
            </label>
            <button className="button">
              {t("Сменить пароль", "Change password")}
            </button>
          </form>
        </section>
      </div>
    </Shell>
  );
}
