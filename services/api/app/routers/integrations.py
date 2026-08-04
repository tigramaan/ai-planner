import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters import ProviderError, account_profile, verify_google_gmail_access
from ..audit import audit
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..integrations import integration_view, read_secret, upsert_secret
from ..models import Integration, User
from ..oauth import authorization_url, consume_state, create_state, exchange_code, resolve_scopes
from ..schemas import OAuthStart, SecretWrite
from .auth import set_auth_cookies

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])
logger = logging.getLogger(__name__)


@router.get("")
def list_integrations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    rows = db.scalars(
        select(Integration).where(Integration.user_id == user.id).order_by(Integration.provider)
    ).all()
    result = [integration_view(row) for row in rows]
    if settings.openai_api_key and not any(row.provider == "openai" for row in rows):
        result.append(
            {
                "provider": "openai",
                "status": "connected",
                "scopes": [],
                "configured": True,
                "source": "server",
            }
        )
    return result


@router.post("/openai")
def configure_openai(
    body: SecretWrite,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    integration = upsert_secret(db, settings, user, "openai", body.model_dump())
    audit(
        db,
        user,
        request,
        "integration.configured",
        "integration",
        integration.id,
        {"provider": "openai"},
    )
    db.commit()
    return integration_view(integration)


@router.post("/{provider}/oauth/start")
def oauth_start(
    provider: str,
    body: OAuthStart,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ru = request.headers.get("accept-language", "").lower().startswith("ru")
    if provider not in {"google", "microsoft", "zoom"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unsupported provider")
    if provider == "google" and not settings.google_client_id:
        detail = "Клиент Google OAuth не настроен" if ru else "Google OAuth client is not configured"
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    if provider == "microsoft" and not settings.microsoft_client_id:
        detail = (
            "Клиент Microsoft OAuth не настроен"
            if ru
            else "Microsoft OAuth client is not configured"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    if provider == "zoom" and not settings.zoom_client_id:
        detail = "Клиент Zoom OAuth не настроен" if ru else "Zoom OAuth client is not configured"
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    try:
        scopes = resolve_scopes(provider, body.scopes)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    state = create_state(db, user, provider, scopes)
    access = request.cookies.get("access_token", "")
    refresh = request.cookies.get("refresh_token", "")
    if access and refresh:
        set_auth_cookies(response, settings, access, refresh)
    return {
        "authorization_url": authorization_url(settings, provider, state, scopes),
        "scopes": scopes,
    }


@router.get("/{provider}/oauth/callback")
async def oauth_callback(
    provider: str,
    state: str,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if provider not in {"google", "microsoft", "zoom"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unsupported provider")
    try:
        record = consume_state(db, state, provider)
        if error or not code:
            raise RuntimeError("OAuth access was declined")
        tokens = await exchange_code(settings, provider, code, record.scopes)
        if provider == "google":
            granted = set(tokens.get("scope", "").split())
            if not granted or not set(record.scopes).issubset(granted):
                raise RuntimeError("Google did not grant all requested permissions")
        profile = await account_profile(provider, tokens["access_token"])
        if provider == "google" and any("/auth/gmail." in scope for scope in record.scopes):
            try:
                await verify_google_gmail_access(tokens["access_token"])
            except ProviderError as exc:
                logger.warning(
                    "Gmail capability check failed status=%s reason=%s",
                    exc.status_code,
                    exc.provider_reason or "unspecified",
                )
                return RedirectResponse(
                    f"{settings.public_base_url}/settings?"
                    f"{urlencode({'oauth_error': 'gmail_mailbox_unavailable'})}",
                    status_code=303,
                )
    except ProviderError as exc:
        logger.warning(
            "OAuth provider capability check failed provider=%s status=%s reason=%s",
            provider,
            exc.status_code,
            exc.provider_reason or "unspecified",
        )
        return RedirectResponse(
            f"{settings.public_base_url}/settings?"
            f"{urlencode({'oauth_error': 'oauth_access_denied'})}",
            status_code=303,
        )
    except (ValueError, RuntimeError):
        reason = "gmail_access_denied" if provider == "google" else "oauth_access_denied"
        return RedirectResponse(
            f"{settings.public_base_url}/settings?{urlencode({'oauth_error': reason})}",
            status_code=303,
        )
    user = db.get(User, record.user_id)
    try:
        previous = read_secret(db, settings, user, provider)
    except LookupError:
        previous = {}
    tokens = {**previous, **tokens}
    if tokens.get("expires_in"):
        tokens["expires_at"] = (
            datetime.now(UTC) + timedelta(seconds=int(tokens["expires_in"]))
        ).isoformat()
    email = profile.get("email") or profile.get("mail") or profile.get("userPrincipalName")
    integration = upsert_secret(db, settings, user, provider, tokens, record.scopes, email)
    integration.last_healthcheck_at = datetime.now(UTC)
    db.commit()
    return RedirectResponse(
        f"{settings.public_base_url}/settings?{urlencode({'connected': provider})}",
        status_code=303,
    )


@router.delete("/{provider}", status_code=204)
def disconnect(
    provider: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    integration = db.scalar(
        select(Integration).where(Integration.user_id == user.id, Integration.provider == provider)
    )
    if integration:
        audit(
            db,
            user,
            request,
            "integration.disconnected",
            "integration",
            integration.id,
            {"provider": provider},
        )
        db.delete(integration)
        db.commit()
