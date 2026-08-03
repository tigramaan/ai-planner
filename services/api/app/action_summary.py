from datetime import datetime
from zoneinfo import ZoneInfo


def _local(value: str | None, timezone: str) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(ZoneInfo(timezone))


def action_summary(action_type: str, payload: dict, locale: str) -> str:
    ru = locale == "ru"
    timezone = payload.get("timezone") or "Europe/Moscow"
    start = _local(payload.get("start_iso"), timezone)
    end = _local(payload.get("end_iso"), timezone)
    title = payload.get("title") or payload.get("event_title") or (
        "Без названия" if ru else "Untitled"
    )
    provider = payload.get("provider", "google")
    calendar_name = (
        "Microsoft" if provider == "microsoft" else "Яндекс" if provider == "yandex" else "Google"
    )
    conference = payload.get("conference")
    conference_name = (
        "Microsoft Teams"
        if conference == "microsoft_teams"
        else "Google Meet"
        if conference == "google_meet"
        else "Яндекс Телемост"
        if conference == "yandex_telemost"
        else "Zoom"
        if conference == "zoom"
        else ("без видеосвязи" if ru else "none")
    )
    attendees = (
        payload.get("added_attendees")
        or payload.get("attendees")
        or payload.get("recipients")
        or []
    )
    people = ", ".join(attendees) if attendees else ("нет" if ru else "none")
    when = ""
    if start:
        interval = start.strftime("%d.%m.%Y, %H:%M")
        if end:
            interval += f"–{end.strftime('%H:%M')}"
        when = interval

    if action_type == "create_meeting":
        lines = (
            [
                f"Создать встречу «{title}».",
                f"Когда: {when}.",
                f"Часовой пояс: {timezone}.",
                f"Участники: {people}.",
                f"Календарь: {calendar_name}.",
                f"Видеосвязь: {conference_name}.",
                (
                    "После подтверждения создам событие и отправлю календарные приглашения."
                    if conference == "none"
                    else "После подтверждения создам событие и видеовстречу, затем отправлю календарные приглашения."
                ),
            ]
            if ru
            else [
                f'Create meeting "{title}".',
                f"When: {when}.",
                f"Timezone: {timezone}.",
                f"Participants: {people}.",
                f"Calendar: {calendar_name}.",
                f"Video service: {conference_name}.",
                (
                    "After confirmation I will create the event and send calendar invitations."
                    if conference == "none"
                    else "After confirmation I will create the event and video meeting, then send invitations."
                ),
            ]
        )
    elif action_type == "update_event":
        lines = (
            [f"Перенести встречу «{title}».", f"Новое время: {when}.", f"Часовой пояс: {timezone}."]
            if ru
            else [f'Reschedule "{title}".', f"New time: {when}.", f"Timezone: {timezone}."]
        )
    elif action_type == "add_event_participants":
        lines = (
            [f"Добавить участников во встречу «{title}»: {people}."]
            if ru
            else [f'Add participants to "{title}": {people}.']
        )
    elif action_type == "cancel_event":
        original = _local(payload.get("original_start_iso"), timezone)
        original_text = original.strftime("%d.%m.%Y, %H:%M") if original else ""
        lines = (
            [f"Отменить встречу «{title}» ({original_text}, {timezone})."]
            if ru
            else [f'Cancel "{title}" ({original_text}, {timezone}).']
        )
    elif action_type == "send_email":
        subject = payload.get("subject") or title
        lines = (
            [f"Отправить письмо «{subject}» адресатам: {people}."]
            if ru
            else [f'Send email "{subject}" to: {people}.']
        )
    else:
        lines = [title]
    return "\n".join(lines)[:500]
