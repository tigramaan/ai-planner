from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .schemas import Intent


def provider_mail_query(
    provider: str,
    intent: Intent,
    raw_text: str,
    timezone: str,
    now: datetime | None = None,
) -> str:
    """Translate planner semantics into the provider's native search syntax."""
    fallback = intent.body or intent.title or intent.event_query or raw_text
    if provider != "google":
        return fallback

    source = " ".join(
        value
        for value in (raw_text, intent.event_query, intent.body, intent.title)
        if value
    )
    normalized = source.casefold()
    terms: list[str] = []

    if "непроч" in normalized or "unread" in normalized:
        terms.append("is:unread")
    if "сегодня" in normalized or "today" in normalized:
        local_now = now.astimezone(ZoneInfo(timezone)) if now else datetime.now(ZoneInfo(timezone))
        today = local_now.date()
        tomorrow = today + timedelta(days=1)
        terms.extend((f"after:{today:%Y/%m/%d}", f"before:{tomorrow:%Y/%m/%d}"))
    if any(marker in normalized for marker in ("влож", "прикреп", "документ", "attachment")):
        terms.append("has:attachment")

    for participant in intent.participants:
        escaped = participant.replace('"', "")
        if escaped:
            terms.append(f'from:"{escaped}"')

    return " ".join(dict.fromkeys(terms)) or fallback
