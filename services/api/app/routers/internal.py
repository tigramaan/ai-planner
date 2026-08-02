import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import AuditLog, PushSubscription, Reminder
from ..schemas import ReminderDelivery
from ..security import decrypt_json

router = APIRouter(prefix="/internal/v1", tags=["internal"], include_in_schema=False)


def worker_authorized(
    x_worker_token: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.worker_service_token or not secrets.compare_digest(
        x_worker_token, settings.worker_service_token
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid worker identity")


@router.post("/reminders/claim", dependencies=[Depends(worker_authorized)])
def claim_reminders(db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    rows = db.scalars(
        select(Reminder)
        .where(
            Reminder.next_attempt_at <= now,
            or_(
                Reminder.status.in_(["scheduled", "retry"]),
                Reminder.status == "processing",
            ),
        )
        .order_by(Reminder.next_attempt_at)
        .limit(25)
        .with_for_update(skip_locked=True)
    ).all()
    claimed = []
    for reminder in rows:
        reminder.status = "processing"
        reminder.attempts += 1
        reminder.next_attempt_at = now + timedelta(minutes=5)
        subscriptions = db.scalars(
            select(PushSubscription).where(PushSubscription.user_id == reminder.user_id)
        ).all()
        push = []
        for subscription in subscriptions:
            data = decrypt_json(
                get_settings(),
                subscription.encrypted_subscription,
                f"push:{reminder.user_id}:{subscription.endpoint_hash}",
            )
            push.append(
                {
                    "id": subscription.id,
                    "endpoint": data["endpoint"],
                    "keys": {"p256dh": data["p256dh"], "auth": data["auth"]},
                }
            )
        claimed.append(
            {
                "id": reminder.id,
                "user_id": reminder.user_id,
                "title": reminder.title,
                "channel": reminder.channel,
                "attempt": reminder.attempts,
                "subscriptions": push,
            }
        )
    db.commit()
    return claimed


@router.post(
    "/reminders/{reminder_id}/complete",
    status_code=204,
    dependencies=[Depends(worker_authorized)],
)
def complete_reminder(
    reminder_id: str,
    body: ReminderDelivery,
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if not reminder or reminder.status != "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Reminder is not processing")
    now = datetime.now(UTC)
    if body.status == "delivered":
        reminder.status = "delivered"
        reminder.delivered_at = now
        reminder.last_error = None
    elif body.status == "retry" and reminder.attempts < 5:
        reminder.status = "retry"
        reminder.next_attempt_at = now + timedelta(minutes=min(2**reminder.attempts, 30))
        reminder.last_error = body.error
    else:
        reminder.status = "failed"
        reminder.last_error = body.error
    db.add(
        AuditLog(
            user_id=reminder.user_id,
            action=f"reminder.{reminder.status}",
            target_type="reminder",
            target_id=reminder.id,
            actor="worker",
            details_redacted_json={"attempts": reminder.attempts},
            ip="internal",
        )
    )
    db.commit()
