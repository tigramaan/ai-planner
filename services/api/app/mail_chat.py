from sqlalchemy.orm import Session

from .adapters import ProviderError, search_email
from .config import Settings
from .integrations import valid_access_token
from .mail_queries import MAIL_READ_SCOPE, mail_access_granted, provider_mail_query
from .mail_summary import (
    mail_search_answer,
    summarize_google_email,
    summary_requested,
    triage_mail_answer,
    triage_requested,
)
from .models import User
from .schemas import Intent


async def handle_mail_search(
    db: Session,
    settings: Settings,
    user: User,
    intent: Intent,
    text: str,
    ai_config: dict[str, str],
    locale: str,
) -> str:
    ru = locale == "ru"
    provider = intent.provider or user.default_mail
    if provider in MAIL_READ_SCOPE and not mail_access_granted(db, user, provider):
        return (
            f"Для чтения писем нужно отдельно разрешить доступ к {provider}. "
            "Откройте «Настройки», нажмите кнопку авторизации почты и повторите запрос."
            if ru
            else f"Mail read access for {provider} is not authorized. Open Settings, "
            "authorize mail access, and retry."
        )
    try:
        token = await valid_access_token(db, settings, user, provider)
        query = provider_mail_query(provider, intent, text, user.timezone)
        wants_triage = triage_requested(text)
        rows = await search_email(provider, token, query, limit=20 if wants_triage else 10)
    except LookupError:
        return (
            f"Сначала подключите {provider} в настройках."
            if ru
            else f"Connect {provider} in Settings first."
        )
    except ProviderError as exc:
        if provider == "google":
            return (
                "Gmail отклонил доступ. Повторно авторизуйте Gmail в настройках."
                if ru
                else "Gmail rejected access. Reauthorize Gmail in Settings."
            )
        return (
            f"{provider} отклонил запрос ({exc.status_code})."
            if ru
            else f"{provider} rejected the request ({exc.status_code})."
        )
    if wants_triage:
        try:
            return await triage_mail_answer(rows, ai_config, locale)
        except RuntimeError:
            return (
                "Письма найдены, но сейчас не удалось надёжно отделить важные от рассылок. "
                "Попробуйте ещё раз."
                if ru
                else "Emails were found, but they could not be reliably triaged right now. "
                "Please retry."
            )
    if rows and summary_requested(text) and provider == "google":
        try:
            return await summarize_google_email(token, rows[0], ai_config, locale)
        except (ProviderError, RuntimeError):
            return (
                "Письмо найдено, но подготовить резюме сейчас не удалось."
                if ru
                else "The email was found, but its summary could not be prepared."
            )
    return mail_search_answer(rows, locale)
