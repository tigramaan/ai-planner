from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from .bootstrap import ensure_owner
from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import (
    auth,
    booking,
    chat,
    commitments,
    family,
    integrations,
    internal,
    local_items,
    planner,
    reminders,
    task_collaboration,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_owner(db, get_settings())
    yield


app = FastAPI(title="UMEC AI Planner API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.include_router(auth.router)
app.include_router(family.router)
app.include_router(chat.router)
app.include_router(integrations.router)
app.include_router(planner.router)
app.include_router(reminders.router)
app.include_router(local_items.router)
app.include_router(commitments.router)
app.include_router(internal.router)
app.include_router(booking.router)
app.include_router(task_collaboration.router)


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "api"}


@app.get("/health/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
