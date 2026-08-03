import base64
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any

import httpx


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def graph_datetime(value: str) -> str:
    return datetime.fromisoformat(value).astimezone(UTC).replace(tzinfo=None).isoformat()


async def provider_request(
    method: str,
    url: str,
    token: str,
    *,
    json: dict | None = None,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    if not url.startswith(
        (
            "https://www.googleapis.com/",
            "https://gmail.googleapis.com/",
            "https://people.googleapis.com/",
            "https://graph.microsoft.com/",
        )
    ):
        raise ProviderError("Provider URL is not allowlisted")
    async with httpx.AsyncClient(timeout=20) as client:
        request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
        response = await client.request(
            method, url, headers=request_headers, json=json, params=params
        )
    if response.status_code >= 400:
        raise ProviderError(f"Provider request failed ({response.status_code})", response.status_code)
    return response.json() if response.content else {}


async def account_profile(provider: str, token: str) -> dict:
    if provider == "google":
        return await provider_request("GET", "https://www.googleapis.com/oauth2/v2/userinfo", token)
    return await provider_request("GET", "https://graph.microsoft.com/v1.0/me", token)


async def search_contacts(provider: str, token: str, query: str, limit: int = 10) -> list[dict]:
    if provider == "google":
        data = await provider_request(
            "GET",
            "https://people.googleapis.com/v1/people/me/connections",
            token,
            params={"personFields": "names,emailAddresses", "pageSize": 1000},
        )
        rows = []
        normalized_query = " ".join(query.casefold().split())
        for person in data.get("connections", []):
            names = person.get("names", [])
            name = names[0].get("displayName", "") if names else ""
            if normalized_query not in " ".join(name.casefold().split()):
                continue
            for email in person.get("emailAddresses", []):
                if email.get("value"):
                    rows.append({"name": name, "email": email["value"]})
                    if len(rows) >= limit:
                        return rows
        return rows
    escaped = query.replace("'", "''")
    data = await provider_request(
        "GET",
        "https://graph.microsoft.com/v1.0/me/contacts",
        token,
        params={
            "$filter": f"contains(displayName,'{escaped}')",
            "$top": min(limit, 20),
            "$select": "displayName,emailAddresses",
        },
    )
    return [
        {"name": row.get("displayName", ""), "email": email.get("address", "")}
        for row in data.get("value", [])
        for email in row.get("emailAddresses", [])
        if email.get("address")
    ]


async def list_calendar_events(
    provider: str, token: str, start: datetime, end: datetime
) -> list[dict]:
    if provider == "google":
        data = await provider_request(
            "GET",
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            token,
            params={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
        return data.get("items", [])
    data = await provider_request(
        "GET",
        "https://graph.microsoft.com/v1.0/me/calendarView",
        token,
        params={
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$orderby": "start/dateTime",
        },
        headers={"Prefer": 'outlook.timezone="UTC"'},
    )
    return data.get("value", [])


async def create_calendar_event(provider: str, token: str, payload: dict[str, Any]) -> dict:
    attendees = payload.get("attendees", [])
    if provider == "google":
        body = {
            "summary": payload["title"],
            "start": {"dateTime": payload["start_iso"], "timeZone": payload["timezone"]},
            "end": {"dateTime": payload["end_iso"], "timeZone": payload["timezone"]},
            "attendees": [{"email": email} for email in attendees],
        }
        if payload.get("conference") == "google_meet":
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": payload["idempotency_key"],
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        created = await provider_request(
            "POST",
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            token,
            json=body,
            params={"sendUpdates": "all", "conferenceDataVersion": 1},
        )
        return await provider_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{created['id']}",
            token,
        )
    body = {
        "subject": payload["title"],
        "start": {"dateTime": graph_datetime(payload["start_iso"]), "timeZone": "UTC"},
        "end": {"dateTime": graph_datetime(payload["end_iso"]), "timeZone": "UTC"},
        "attendees": [
            {"emailAddress": {"address": email}, "type": "required"} for email in attendees
        ],
        "isOnlineMeeting": payload.get("conference") == "microsoft_teams",
        "onlineMeetingProvider": "teamsForBusiness",
        "transactionId": payload["idempotency_key"],
    }
    created = await provider_request(
        "POST", "https://graph.microsoft.com/v1.0/me/events", token, json=body
    )
    return await provider_request(
        "GET", f"https://graph.microsoft.com/v1.0/me/events/{created['id']}", token
    )


async def update_calendar_event(provider: str, token: str, payload: dict[str, Any]) -> dict:
    event_id = payload["event_id"]
    attendees = payload.get("attendees", [])
    if provider == "google":
        body: dict[str, Any] = {}
        if payload.get("start_iso"):
            body["start"] = {"dateTime": payload["start_iso"], "timeZone": payload["timezone"]}
            body["end"] = {"dateTime": payload["end_iso"], "timeZone": payload["timezone"]}
        if "attendees" in payload:
            body["attendees"] = [{"email": email} for email in attendees]
        await provider_request(
            "PATCH",
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
            token,
            json=body,
            params={"sendUpdates": "all"},
        )
        return await provider_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
            token,
        )
    body = {}
    if payload.get("start_iso"):
        body["start"] = {"dateTime": graph_datetime(payload["start_iso"]), "timeZone": "UTC"}
        body["end"] = {"dateTime": graph_datetime(payload["end_iso"]), "timeZone": "UTC"}
    if "attendees" in payload:
        body["attendees"] = [
            {"emailAddress": {"address": email}, "type": "required"} for email in attendees
        ]
    await provider_request(
        "PATCH", f"https://graph.microsoft.com/v1.0/me/events/{event_id}", token, json=body
    )
    return await provider_request(
        "GET", f"https://graph.microsoft.com/v1.0/me/events/{event_id}", token
    )


async def cancel_calendar_event(provider: str, token: str, event_id: str) -> dict:
    url = (
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        if provider == "google"
        else f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    )
    params = {"sendUpdates": "all"} if provider == "google" else None
    await provider_request("DELETE", url, token, params=params)
    try:
        await provider_request("GET", url, token)
    except ProviderError as exc:
        if exc.status_code == 404:
            return {"id": event_id, "status": "cancelled"}
        raise
    raise ProviderError("Calendar event still exists after cancellation")


async def search_email(provider: str, token: str, query: str, limit: int = 10) -> list[dict]:
    if provider == "google":
        listing = await provider_request(
            "GET",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            token,
            params={"q": query, "maxResults": min(limit, 20)},
        )
        rows = []
        for item in listing.get("messages", []):
            message = await provider_request(
                "GET",
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}",
                token,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            )
            headers = {
                row["name"].casefold(): row["value"]
                for row in message.get("payload", {}).get("headers", [])
            }
            rows.append(
                {
                    "id": message.get("id"),
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", "(без темы)"),
                    "received_at": headers.get("date"),
                    "snippet": message.get("snippet", ""),
                }
            )
        return rows
    data = await provider_request(
        "GET",
        "https://graph.microsoft.com/v1.0/me/messages",
        token,
        params={
            "$search": f'"{query}"',
            "$top": min(limit, 20),
            "$select": "id,subject,from,receivedDateTime,bodyPreview",
        },
        headers={"ConsistencyLevel": "eventual"},
    )
    return [
        {
            "id": row.get("id"),
            "from": (row.get("from") or {}).get("emailAddress", {}).get("address", ""),
            "subject": row.get("subject") or "(без темы)",
            "received_at": row.get("receivedDateTime"),
            "snippet": row.get("bodyPreview", ""),
        }
        for row in data.get("value", [])
    ]


async def send_email(provider: str, token: str, payload: dict[str, Any]) -> dict:
    recipients = payload["recipients"]
    if provider == "google":
        message = EmailMessage()
        message["To"] = ", ".join(recipients)
        message["Subject"] = payload["subject"]
        message.set_content(payload["body"])
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        created = await provider_request(
            "POST",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            token,
            json={"raw": raw},
        )
        verified = await provider_request(
            "GET",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{created['id']}",
            token,
            params={"format": "metadata"},
        )
        return {"id": verified["id"], "thread_id": verified.get("threadId"), "status": "sent"}
    body = {
        "subject": payload["subject"],
        "body": {"contentType": "Text", "content": payload["body"]},
        "toRecipients": [{"emailAddress": {"address": address}} for address in recipients],
    }
    draft = await provider_request(
        "POST", "https://graph.microsoft.com/v1.0/me/messages", token, json=body
    )
    verified = await provider_request(
        "GET",
        f"https://graph.microsoft.com/v1.0/me/messages/{draft['id']}",
        token,
        params={"$select": "id,subject,isDraft"},
    )
    if not verified.get("isDraft") or verified.get("subject") != payload["subject"]:
        raise ProviderError("Outlook draft verification failed")
    await provider_request(
        "POST", f"https://graph.microsoft.com/v1.0/me/messages/{draft['id']}/send", token
    )
    return {"id": draft["id"], "status": "submitted"}


def default_event_window() -> tuple[datetime, datetime]:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)
