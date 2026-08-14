import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import AgentMessage, AuditLog, PushDelivery, PushSubscription, Reminder, Timer
from ..reminder_recurrence import next_occurrence
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
            Reminder.paused.is_(False),
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
        subscription_query = select(PushSubscription).where(
            PushSubscription.user_id == reminder.user_id
        )
        if reminder.target_subscription_id:
            subscription_query = subscription_query.where(
                PushSubscription.id == reminder.target_subscription_id
            )
        subscriptions = db.scalars(subscription_query).all()
        push = []
        for subscription in subscriptions:
            delivery = db.scalar(
                select(PushDelivery).where(
                    PushDelivery.reminder_id == reminder.id,
                    PushDelivery.endpoint_hash == subscription.endpoint_hash,
                )
            )
            if delivery is not None and delivery.status in {"delivered", "stale"}:
                continue
            data = decrypt_json(
                get_settings(),
                subscription.encrypted_subscription,
                f"push:{reminder.user_id}:{subscription.endpoint_hash}",
            )
            if delivery is None:
                delivery = PushDelivery(
                    reminder_id=reminder.id,
                    subscription_id=subscription.id,
                    endpoint_hash=subscription.endpoint_hash,
                    provider=urlparse(data["endpoint"]).hostname or "web-push",
                    user_agent=subscription.user_agent,
                    attempts=1,
                    created_at=now,
                    updated_at=now,
                )
                db.add(delivery)
            else:
                delivery.attempts = (delivery.attempts or 0) + 1
            delivery.updated_at = now
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
    if body.deliveries:
        for result in body.deliveries:
            subscription = db.get(PushSubscription, result.subscription_id)
            if subscription is None or subscription.user_id != reminder.user_id:
                continue
            delivery = db.scalar(
                select(PushDelivery).where(
                    PushDelivery.reminder_id == reminder.id,
                    PushDelivery.endpoint_hash == subscription.endpoint_hash,
                )
            )
            if delivery is None:
                continue
            delivery.status = result.status
            delivery.status_code = result.status_code
            delivery.last_error = result.error
            delivery.updated_at = now
            if result.status == "delivered":
                subscription.last_used_at = now
            elif result.status == "stale":
                db.delete(subscription)
        db.flush()
        deliveries = db.scalars(
            select(PushDelivery).where(PushDelivery.reminder_id == reminder.id)
        ).all()
        pending = any(row.status in {"scheduled", "retry"} for row in deliveries)
        accepted = any(row.status == "delivered" for row in deliveries)
        if pending and reminder.attempts < 5:
            body.status = "retry"
            body.error = "partial push delivery"
        elif accepted:
            body.status = "delivered"
            body.error = None
        else:
            body.status = "failed"
            body.error = "no device accepted push"
    if body.status == "delivered":
        reminder.delivered_at = now
        reminder.last_error = None
        if reminder.recurrence_json and not reminder.timer_id and not reminder.task_id:
            following = next_occurrence(reminder.due_at, reminder.timezone, reminder.recurrence_json)
            reminder.due_at = following
            reminder.next_attempt_at = following
            reminder.status = "scheduled"
            reminder.attempts = 0
            db.execute(delete(PushDelivery).where(PushDelivery.reminder_id == reminder.id))
        else:
            reminder.status = "delivered"
        if reminder.timer_id:
            timer = db.get(Timer, reminder.timer_id)
            if timer is not None:
                timer.status = "finished"
            db.add(
                AgentMessage(
                    user_id=reminder.user_id,
                    role="assistant",
                    text=reminder.title,
                    created_at=now,
                )
            )
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
