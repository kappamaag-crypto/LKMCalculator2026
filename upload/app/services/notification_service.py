"""Reliable notification delivery with durable outbox and environment-only secrets."""

from __future__ import annotations

import hashlib
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.notifications.outbox import (
    FAILED,
    PENDING,
    RETRY,
    SENT,
    SENDING,
    NotificationOutboxORM,
)


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str
    use_tls: bool = True
    timeout_seconds: int = 20

    @classmethod
    def from_environment(cls) -> "SMTPSettings":
        """Read SMTP credentials from environment; never persist them in SQLite."""
        host = os.getenv("LKM_SMTP_HOST", "").strip()
        username = os.getenv("LKM_SMTP_USERNAME", "").strip()
        password = os.getenv("LKM_SMTP_PASSWORD", "")
        sender = os.getenv("LKM_SMTP_SENDER", username).strip()
        if not host or not sender:
            raise RuntimeError("SMTP is not configured: LKM_SMTP_HOST and LKM_SMTP_SENDER are required")
        try:
            port = int(os.getenv("LKM_SMTP_PORT", "587"))
            timeout = int(os.getenv("LKM_SMTP_TIMEOUT", "20"))
        except ValueError as exc:
            raise RuntimeError("SMTP port/timeout must be integers") from exc
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            sender=sender,
            use_tls=os.getenv("LKM_SMTP_TLS", "1").strip().lower() not in {"0", "false", "no"},
            timeout_seconds=timeout,
        )


class SMTPMailer:
    """Small SMTP adapter. Credentials live only in memory for one delivery call."""

    def __init__(self, settings: SMTPSettings):
        self.settings = settings

    def send(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.settings.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.settings.host, self.settings.port, timeout=self.settings.timeout_seconds) as smtp:
            smtp.ehlo()
            if self.settings.use_tls:
                smtp.starttls()
                smtp.ehlo()
            if self.settings.username:
                smtp.login(self.settings.username, self.settings.password)
            smtp.send_message(message)


class NotificationService:
    """Queue notifications transactionally and deliver them with bounded retries."""

    def __init__(self, session: Session, mailer: SMTPMailer | None = None, *, max_attempts: int = 5):
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.session = session
        self.mailer = mailer or SMTPMailer(SMTPSettings.from_environment())
        self.max_attempts = max_attempts

    @staticmethod
    def make_idempotency_key(event: str, stable_id: str | int) -> str:
        raw = f"{event}:{stable_id}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def enqueue(
        self,
        recipient: str,
        subject: str,
        body: str,
        *,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> int:
        """Insert one durable notification; repeated keys return the existing record."""
        if not recipient.strip():
            raise ValueError("recipient is required")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        timestamp = now or datetime.now(timezone.utc)
        row = NotificationOutboxORM(
            idempotency_key=idempotency_key,
            recipient=recipient.strip(),
            subject=subject,
            body=body,
            status=PENDING,
            attempts=0,
            next_attempt_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            existing = self.session.scalar(
                select(NotificationOutboxORM).where(NotificationOutboxORM.idempotency_key == idempotency_key)
            )
            if existing is None:
                raise
            return existing.id
        return row.id

    @staticmethod
    def _backoff(attempts: int) -> timedelta:
        # 1, 2, 4, 8, 16 minutes; deterministic and bounded by max_attempts.
        return timedelta(minutes=min(16, 2 ** max(0, attempts - 1)))

    def process_due(self, *, now: datetime | None = None, limit: int = 20) -> int:
        """Deliver due rows; failures are retained for retry and never silently lost."""
        if limit < 1:
            return 0
        current = now or datetime.now(timezone.utc)
        rows = self.session.scalars(
            select(NotificationOutboxORM)
            .where(NotificationOutboxORM.status.in_([PENDING, RETRY]))
            .where(NotificationOutboxORM.next_attempt_at <= current)
            .order_by(NotificationOutboxORM.id)
            .limit(limit)
        ).all()
        delivered = 0
        for row in rows:
            if row.status not in {PENDING, RETRY}:
                continue
            row.status = SENDING
            row.attempts += 1
            row.updated_at = current
            self.session.flush()
            try:
                self.mailer.send(row.recipient, row.subject, row.body)
            except Exception as exc:  # SMTP/library errors are converted to durable retry state.
                row.last_error = str(exc)[:4000]
                row.status = RETRY if row.attempts < self.max_attempts else FAILED
                row.next_attempt_at = current + self._backoff(row.attempts)
                row.updated_at = current
                self.session.flush()
                continue
            row.status = SENT
            row.sent_at = current
            row.last_error = None
            row.updated_at = current
            self.session.flush()
            delivered += 1
        return delivered


def enqueue_event(
    session: Session,
    event: str,
    stable_id: str | int,
    recipient: str,
    subject: str,
    body: str,
    *,
    mailer: SMTPMailer | None = None,
) -> int:
    """Convenience API for event-driven callers with deterministic idempotency."""
    key = NotificationService.make_idempotency_key(event, stable_id)
    return NotificationService(session, mailer=mailer).enqueue(
        recipient,
        subject,
        body,
        idempotency_key=key,
    )
