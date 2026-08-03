from .adapters import gmail_attachment, gmail_message
from .agent import summarize_email_content, triage_email_rows
from .mail_documents import email_text_bundle


def summary_requested(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in ("резюме", "сводк", "суммар", "summary", "summar"))


def triage_requested(text: str) -> bool:
    normalized = text.casefold()
    return any(
        marker in normalized
        for marker in (
            "полезн",
            "важн",
            "отреаг",
            "реагиров",
            "мусор",
            "спам",
            "рассыл",
            "triage",
            "actionable",
            "important email",
        )
    )


def mail_search_answer(rows: list[dict], locale: str) -> str:
    if not rows:
        return "Писем не найдено." if locale == "ru" else "No emails found."
    return "\n".join(
        f"{index + 1}. {row['subject']} | {row['from']}" for index, row in enumerate(rows)
    )


async def triage_mail_answer(
    rows: list[dict], ai_config: dict[str, str], locale: str
) -> str:
    if not rows:
        return mail_search_answer(rows, locale)
    classified = await triage_email_rows(
        ai_config["api_key"],
        ai_config["model"],
        ai_config["reasoning_effort"],
        rows,
        locale,
    )
    selected = [item for item in classified if item["category"] != "ignore"]
    ignored = len(classified) - len(selected)
    if not selected:
        return (
            f"Среди {len(classified)} писем не нашёл требующих реакции или явно важных. Отсеяно как рассылки и шум: {ignored}."
            if locale == "ru"
            else f"None of {len(classified)} emails appear actionable or clearly important. Filtered as newsletters or noise: {ignored}."
        )
    heading = "Требуют внимания:" if locale == "ru" else "Needs attention:"
    lines = [heading]
    labels = {
        "action": ("нужно действие", "action needed"),
        "important": ("важно прочитать", "worth reading"),
    }
    for number, item in enumerate(selected, 1):
        row = rows[item["index"]]
        label = labels[item["category"]][0 if locale == "ru" else 1]
        lines.append(f"{number}. {row['subject']} | {row['from']} — {label}")
        if item["reason"]:
            lines.append(f"   {item['reason']}")
        if item["suggested_action"]:
            prefix = "Что сделать" if locale == "ru" else "Next"
            lines.append(f"   {prefix}: {item['suggested_action']}")
    footer = (
        f"Отсеяно как рассылки, промо или несущественное: {ignored}."
        if locale == "ru"
        else f"Filtered as newsletters, promotions or noise: {ignored}."
    )
    return "\n".join([*lines, footer])


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
