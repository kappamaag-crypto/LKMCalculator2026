"""Сервис истории расчётов и сравнений (SQLite)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import null
from sqlalchemy.orm import Session

from app.infrastructure.database.models import CalculationORM, CalculationLayerORM, ComparisonORM
from app.infrastructure.database.repositories import CalculationRepository
from app.domain.models import SystemCalculationResult, ComparisonResult
from app.domain.surface_profile import SurfaceCondition, SurfacePreparation, SurfaceProfile
from app.domain.normative import UNKNOWN
from app.services.engineering_context_snapshot import (
    engineering_context_from_dict,
    engineering_context_to_dict,
    normative_model_to_dict,
    surface_condition_to_dict,
)
from app.services.snapshot_utils import load_and_verify_snapshot, seal_snapshot
from app.services.tds_normative_bridge import tds_trace_for_material, engineering_context_from_known_tds


class HistoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CalculationRepository(session)

    def get_calculation_tds_traces(self, calc_id: int) -> list[dict]:
        snapshot = self.get_calculation_snapshot(calc_id)
        traces = snapshot.get("tds_traces")
        if isinstance(traces, list):
            return list(traces)
        return [t for layer in snapshot.get("layers") or [] if isinstance((t := layer.get("tds_trace")), dict)]

    def get_calculation_tds_verified(self, calc_id: int) -> str:
        snapshot = self.get_calculation_snapshot(calc_id)
        status = snapshot.get("tds_verified")
        if status in ("KNOWN", "UNKNOWN"):
            return status
        traces = self.get_calculation_tds_traces(calc_id)
        return "KNOWN" if traces and all(t.get("tds_verified") == "KNOWN" for t in traces) else "UNKNOWN"
