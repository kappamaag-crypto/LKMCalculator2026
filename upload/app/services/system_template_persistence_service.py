"""Application service for the explicit confirmation -> persistence boundary."""
from __future__ import annotations

from app.domain.system_template import SystemTemplateDraft
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.system_template_repository import SystemTemplateRepository


class SystemTemplatePersistenceService:
    """Persist a template only after a deliberate confirmation decision.

    The service never creates or updates Material records. Material matching and
    any incomplete-card workflow remain explicit UI actions outside this boundary.
    """

    def save_confirmed(self, draft: SystemTemplateDraft) -> int:
        draft.validate()
        if draft.status != "CONFIRMED":
            raise ValueError("Для сохранения требуется статус CONFIRMED")
        if draft.metadata.get("tds_verified") != "KNOWN":
            raise ValueError("Нельзя сохранить шаблон: применимость TDS не подтверждена")

        with get_session_factory()() as session:
            repository = SystemTemplateRepository(session)
            orm = repository.add_confirmed(draft)
            template_id = orm.id
            session.commit()
            return template_id

    def list_confirmed(self):
        with get_session_factory()() as session:
            return list(SystemTemplateRepository(session).list_all(active_only=True))
