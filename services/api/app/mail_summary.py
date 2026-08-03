from .adapters import gmail_attachment, gmail_message
from .agent import summarize_email_content
from .mail_documents import email_text_bundle


def summary_requested(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in ("резюме", "сводк", "суммар", "summary", "summar"))


def mail_search_answer(rows: list[dict], locale: str) -> str:
    if not rows:
        return "Писем не найдено." if locale == "ru" else "No emails found."
    return "\n".join(
        f"{index + 1}. {row['subject']} | {row['from']}" for index, row in enumerate(rows)
    )


async def summarize_google_email(
    token: str,
    row: dict,
    ai_config: dict[str, str],
    locale: str,
) -> str:
    message = await gmail_message(token, row["id"])
    content, attachments, warnings = await email_text_bundle(
        message,
        lambda attachment_id: gmail_attachment(token, row["id"], attachment_id),
    )
    if not content.strip():
        return (
            "Текст письма и поддерживаемых вложений извлечь не удалось."
            if locale == "ru"
            else "The email and supported attachments contained no extractable text."
        )
    summary = await summarize_email_content(
        ai_config["api_key"],
        ai_config["model"],
        ai_config["reasoning_effort"],
        content,
        locale,
    )
    attachment_label = "Вложения" if locale == "ru" else "Attachments"
    attachment_line = f"\n{attachment_label}: {', '.join(attachments)}" if attachments else ""
    warning_line = f"\n{' '.join(warnings)}" if warnings else ""
    return f"{row['subject']} | {row['from']}\n\n{summary}{attachment_line}{warning_line}"
