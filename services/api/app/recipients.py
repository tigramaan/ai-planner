from dataclasses import dataclass, field
from email.utils import parseaddr

from sqlalchemy.orm import Session

from .adapters import ProviderError, search_contacts, search_email
from .config import Settings
from .integrations import valid_access_token
from .models import User
from .recipient_aliases import find_recipient_alias


@dataclass
class RecipientResolution:
    recipients: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: dict[str, list[str]] = field(default_factory=dict)


def is_email(value: str) -> bool:
    _, address = parseaddr(value)
    return bool(address and "@" in address and address.rsplit("@", 1)[1])


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def candidate_addresses(query: str, contacts: list[dict], messages: list[dict]) -> list[str]:
    candidates: list[tuple[str, str]] = []
    for row in contacts:
        candidates.append((row.get("name", ""), row.get("email", "")))
    for row in messages:
        name, address = parseaddr(row.get("from", ""))
        candidates.append((name, address))
    exact = [address for name, address in candidates if normalize_name(name) == normalize_name(query)]
    selected = exact or [address for _, address in candidates]
    return list(dict.fromkeys(address.casefold() for address in selected if is_email(address)))


async def resolve_recipients(
    db: Session,
    settings: Settings,
    user: User,
    values: list[str],
    preferred_provider: str,
) -> RecipientResolution:
    result = RecipientResolution()
    providers = list(dict.fromkeys([preferred_provider, "google", "microsoft"]))
    for value in values:
        if is_email(value):
            result.recipients.append(parseaddr(value)[1].casefold())
            continue
        remembered = find_recipient_alias(db, settings, user, value) if db is not None else None
        if remembered:
            result.recipients.append(remembered)
            continue
        addresses: list[str] = []
        for provider in providers:
            try:
                token = await valid_access_token(db, settings, user, provider)
            except (LookupError, ProviderError):
                continue
            try:
                contacts = await search_contacts(provider, token, value)
            except ProviderError:
                contacts = []
            try:
                messages = await search_email(provider, token, value)
            except ProviderError:
                messages = []
            addresses.extend(candidate_addresses(value, contacts, messages))
        addresses = list(dict.fromkeys(addresses))
        if len(addresses) == 1:
            result.recipients.append(addresses[0])
        elif addresses:
            result.ambiguous[value] = addresses
        else:
            result.unresolved.append(value)
    result.recipients = list(dict.fromkeys(result.recipients))
    return result
