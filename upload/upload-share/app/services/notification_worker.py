"""Opt-in one-shot notification worker for the desktop application lifecycle."""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationWorker:
    """Process a bounded notification batch when explicitly enabled.

    The worker is deliberately one-shot: the desktop process does not own a
    permanent daemon thread. A future scheduler/service can call run_once()
    without changing the durable outbox contract.
    """

    @staticmethod
    def enabled() -> bool:
        return os.getenv("LKM_NOTIFICATIONS_ENABLED", "0").strip().lower() in {"1", "true", "yes"}

    @classmethod
    def run_once(cls, session: Session, *, limit: int = 20) -> int:
        if not cls.enabled():
            return 0
        if not NotificationService.smtp_configured():
            logger.warning("Notification worker is enabled but SMTP is not configured")
            return 0
        try:
            delivered = NotificationService(session).process_due(limit=limit)
            session.commit()
            return delivered
        except Exception:
            session.rollback()
            logger.exception("Notification worker failed; durable outbox rows remain available for retry")
            return 0
