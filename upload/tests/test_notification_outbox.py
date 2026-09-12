"""§11.1 durable notification outbox — no real SMTP required."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.engine import Base
from app.infrastructure.notifications.outbox import (
    FAILED,
    PENDING,
    RETRY,
    SENT,
    NotificationOutboxORM,
)
from app.services.notification_service import NotificationService, enqueue_event
from app.services.notification_worker import NotificationWorker


class FakeMailer:
    def __init__(self, *, fail_times: int = 0):
        self.fail_times = fail_times
        self.sent: list[tuple[str, str, str]] = []
        self.calls = 0

    def send(self, recipient: str, subject: str, body: str, *, idempotency_key: str | None = None) -> None:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"smtp fail #{self.calls}")
        self.sent.append((recipient, subject, body))


def _session():
    engine = create_engine("sqlite:///:memory:")
    from app.infrastructure.notifications import outbox  # noqa: F401
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_enqueue_creates_pending_row_without_credentials():
    session = _session()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    svc = NotificationService(session)
    row_id = svc.enqueue("a@example.com", "Subj", "Body", idempotency_key="k1", now=now)
    session.commit()
    row = session.get(NotificationOutboxORM, row_id)
    assert row is not None
    assert row.status == PENDING
    assert row.attempts == 0
    assert row.recipient == "a@example.com"
    for attr in ("password", "username", "host", "smtp"):
        assert not hasattr(row, attr)


def test_duplicate_idempotency_key_returns_existing_id():
    session = _session()
    svc = NotificationService(session)
    first = svc.enqueue("a@example.com", "S", "B", idempotency_key="same-key")
    session.commit()
    second = svc.enqueue("a@example.com", "S2", "B2", idempotency_key="same-key")
    assert first == second
    rows = session.scalars(select(NotificationOutboxORM)).all()
    assert len(rows) == 1


def test_process_due_marks_sent_with_fake_mailer():
    session = _session()
    mailer = FakeMailer()
    svc = NotificationService(session, mailer=mailer)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    svc.enqueue("a@example.com", "S", "B", idempotency_key="ok", now=now)
    session.commit()
    delivered = svc.process_due(now=now)
    session.commit()
    assert delivered == 1
    row = session.scalars(select(NotificationOutboxORM)).one()
    assert row.status == SENT
    assert row.sent_at is not None
    assert mailer.sent == [("a@example.com", "S", "B")]


def test_process_due_retries_then_fails():
    session = _session()
    mailer = FakeMailer(fail_times=99)
    svc = NotificationService(session, mailer=mailer, max_attempts=2)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    svc.enqueue("a@example.com", "S", "B", idempotency_key="fail", now=now)
    session.commit()
    assert svc.process_due(now=now) == 0
    session.commit()
    row = session.scalars(select(NotificationOutboxORM)).one()
    assert row.status == RETRY
    assert row.attempts == 1
    assert row.last_error
    later = now + timedelta(hours=1)
    assert svc.process_due(now=later) == 0
    session.commit()
    row = session.scalars(select(NotificationOutboxORM)).one()
    assert row.status == FAILED
    assert row.attempts == 2


def test_worker_disabled_delivers_nothing(monkeypatch):
    session = _session()
    monkeypatch.delenv("LKM_NOTIFICATIONS_ENABLED", raising=False)
    assert NotificationWorker.enabled() is False
    assert NotificationWorker.run_once(session) == 0


def test_enqueue_event_uses_stable_idempotency_key():
    session = _session()
    a = enqueue_event(session, "calc_done", 42, "a@example.com", "S", "B")
    session.commit()
    b = enqueue_event(session, "calc_done", 42, "a@example.com", "S", "B")
    assert a == b
    key = NotificationService.make_idempotency_key("calc_done", 42)
    row = session.get(NotificationOutboxORM, a)
    assert row.idempotency_key == key
