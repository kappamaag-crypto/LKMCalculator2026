"""Application service for coating inspection records."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from app.domain.inspection import InspectionDefect, InspectionMeasurement, InspectionRecord


class InspectionService:
    """Build and validate inspection records without normative inference."""

    @staticmethod
    def create_record(inspection_id: str, *, object_name: str = "", inspector: str = "", standard_reference: str = "", standard_source: str = "", coating_system: str = "", substrate: str = "", preparation: str = "", measurements=(), defects=(), photo_refs=(), notes: str = "", conclusion: str = "", acceptance_status: str = "UNKNOWN") -> InspectionRecord:
        record = InspectionRecord(inspection_id=inspection_id.strip(), object_name=object_name.strip(), inspector=inspector.strip(), standard_reference=standard_reference.strip(), standard_source=standard_source.strip(), coating_system=coating_system.strip(), substrate=substrate.strip(), preparation=preparation.strip(), measurements=tuple(measurements), defects=tuple(defects), photo_refs=tuple(p for p in photo_refs if p), notes=notes.strip(), conclusion=conclusion.strip(), acceptance_status=acceptance_status, inspection_date=datetime.now())
        record.validate()
        return record

    @staticmethod
    def summary(record: InspectionRecord) -> str:
        record.validate()
        lines = [f"Инспекция: {record.inspection_id}", f"Статус: {record.acceptance_status}", f"Измерений: {len(record.measurements)}; дефектов: {len(record.defects)}; фото: {len(record.photo_refs)}"]
        if record.object_name: lines.insert(1, f"Объект: {record.object_name}")
        if record.standard_reference: lines.append(f"Источник/НД: {record.standard_reference} {record.standard_source}".strip())
        if record.acceptance_status == "UNKNOWN": lines.append("Приёмка не определена: критерий или решение не подтверждены.")
        return "\n".join(lines)

    @staticmethod
    def to_dict(record: InspectionRecord) -> dict:
        record.validate()
        data = asdict(record)
        data["inspection_date"] = record.inspection_date.isoformat() if record.inspection_date else None
        data["created_at"] = record.created_at.isoformat()
        return data
