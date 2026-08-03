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
    end = _local(payload.get("end_iso") or payload.get("original_end_iso"), timezone)
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
            interval += f"-{end.strftime('%H:%M')}"
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
                f"Напоминание: за {payload.get('reminder_minutes', 5)} мин.",
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
                f"Reminder: {payload.get('reminder_minutes', 5)} min before.",
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
        if conference and conference != "none":
            lines.append(
                f"Видеосвязь: {conference_name}."
                if ru
                else f"Video service: {conference_name}."
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


def _provider_name(provider: str, ru: bool) -> str:
    if provider == "microsoft":
        return "Microsoft Outlook"
    if provider == "yandex":
        return "Яндекс Календарь" if ru else "Yandex Calendar"
    return "Google Calendar"


def action_result_summary(
    action_type: str, payload: dict, result: dict, warnings: list[str], locale: str
) -> dict[str, str | None]:
    ru = locale == "ru"
    timezone = payload.get("timezone") or "Europe/Moscow"
    start = _local(payload.get("start_iso") or payload.get("original_start_iso"), timezone)
    end = _local(payload.get("end_iso"), timezone)
    title = payload.get("title") or payload.get("event_title") or (
        "Без названия" if ru else "Untitled"
    )
    attendees = payload.get("added_attendees") or payload.get("attendees") or []
    calendar_link = result.get("htmlLink") or result.get("webLink")
    join_link = (result.get("onlineMeeting") or {}).get("joinUrl") or result.get("hangoutLink")
    if not join_link:
        join_link = next(
            (
                item.get("uri")
                for item in (result.get("conferenceData") or {}).get("entryPoints", [])
                if item.get("entryPointType") == "video" and item.get("uri")
            ),
            None,
        )
    join_link = join_link or payload.get("external_join_url")
    when = start.strftime("%d.%m.%Y, %H:%M") if start else ""
    if when and end:
        when += f"-{end.strftime('%H:%M')}"
    headings = {
        "create_meeting": ("Встреча создана", "Meeting created"),
        "update_event": ("Встреча изменена", "Meeting updated"),
        "add_event_participants": ("Участники добавлены", "Participants added"),
        "cancel_event": ("Встреча удалена из календаря", "Meeting removed from calendar"),
        "send_email": ("Письмо отправлено", "Email sent"),
    }
    heading = headings.get(action_type, ("Действие выполнено", "Action completed"))[0 if ru else 1]
    lines = [f"{heading}: «{title}»."]
    if when:
        lines.append(("Когда: " if ru else "When: ") + f"{when} ({timezone}).")
    provider = payload.get("provider", "google")
    if action_type == "send_email":
        mail_name = (
            "Microsoft Outlook"
            if provider == "microsoft"
            else ("Яндекс Почта" if ru else "Yandex Mail")
            if provider == "yandex"
            else "Gmail"
        )
        lines.append(("Почта: " if ru else "Mail: ") + mail_name + ".")
    else:
        lines.append(("Календарь: " if ru else "Calendar: ") + _provider_name(provider, ru) + ".")
    if attendees:
        added = action_type == "add_event_participants"
        label = (
            "Добавлены участники: " if added and ru else
            "Added participants: " if added else
            "Участники: " if ru else "Participants: "
        )
        lines.append(label + ", ".join(attendees) + ".")
    if calendar_link:
        lines.append(("Открыть в календаре: " if ru else "Open in calendar: ") + calendar_link)
    if join_link:
        lines.append(("Открыть видеовстречу: " if ru else "Open video meeting: ") + join_link)
    if warnings:
        unavailable = any("not created" in warning or "not configured" in warning for warning in warnings)
        lines.append(
            "Важно: видеовстреча не создана, но событие календаря сохранено."
            if unavailable and ru else
            "Note: the video meeting was not created, but the calendar event was saved."
            if unavailable else
            "Важно: использована настроенная постоянная ссылка на видеовстречу."
            if ru else "Note: the configured permanent video-room link was used."
        )
    return {"report": "\n".join(lines), "calendar_link": calendar_link, "join_link": join_link}
