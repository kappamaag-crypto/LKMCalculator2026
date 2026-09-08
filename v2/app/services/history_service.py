"""Сервис истории расчётов и сравнений (SQLite)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.infrastructure.database.models import CalculationORM, CalculationLayerORM, ComparisonORM
from app.infrastructure.database.repositories import CalculationRepository
from app.domain.models import SystemCalculationResult, ComparisonResult, ObjectData, CoatingSystem


class HistoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CalculationRepository(session)

    def save_calculation(self, result: SystemCalculationResult, notes: str = "") -> int:
        """Сохранить расчёт. Возвращает id."""
        obj = result.object_data
        snapshot = {
            "object": {
                "object_name": obj.object_name,
                "customer": obj.customer,
                "project": obj.project,
                "calculation_number": obj.calculation_number,
                "area_m2": obj.area_m2,
                "corrosion_category": obj.corrosion_category.value if obj.corrosion_category else None,
                "durability": obj.durability.value if obj.durability else None,
            },
            "system_name": result.system.system_name,
            "total_dft": result.total_dft,
            "total_cost_per_m2": result.total_cost_per_m2,
            "total_cost": result.total_cost,
            "total_consumption_kg": result.total_practical_consumption_kg,
            "layers": [
                {
                    "material_name": lr.material.material_name,
                    "binder": lr.material.binder_type.value if hasattr(lr.material.binder_type, "value") else str(lr.material.binder_type),
                    "density": lr.material.density,
                    "solids_percent": lr.material.solids_percent,
                    "price_per_kg": lr.material.price_per_kg,
                    "target_dft": lr.target_dft,
                    "losses_percent": lr.losses_percent,
                    "thinner_percent": lr.thinner_percent,
                    "wft": lr.wft,
                    "practical_consumption_kg": lr.practical_consumption_kg,
                    "cost_per_m2": lr.cost_per_m2,
                    "total_consumption_kg": lr.total_consumption_kg,
                    "total_cost": lr.total_cost,
                }
                for lr in result.layers
            ],
        }
        calc = CalculationORM(
            calculation_number=obj.calculation_number or "",
            object_name=obj.object_name or "",
            customer=obj.customer or "",
            project=obj.project or "",
            area_m2=obj.area_m2 or 0.0,
            system_name=result.system.system_name or "Пользовательская",
            total_dft=result.total_dft,
            total_cost_per_m2=result.total_cost_per_m2,
            total_cost=result.total_cost,
            total_consumption_kg=result.total_practical_consumption_kg,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        for i, lr in enumerate(result.layers):
            calc.layers.append(CalculationLayerORM(
                layer_number=i + 1,
                material_name=lr.material.material_name,
                binder=lr.material.binder_type.value if hasattr(lr.material.binder_type, "value") else str(lr.material.binder_type),
                dry_thickness=lr.target_dft,
                consumption_kg=lr.practical_consumption_kg,
                consumption_l=lr.practical_consumption_l,
                cost_per_m2=lr.cost_per_m2,
                snapshot_json=json.dumps(snapshot["layers"][i], ensure_ascii=False),
            ))
        self.session.add(calc)
        self.session.flush()
        return calc.id

    def list_calculations(self, limit: int = 100) -> Sequence[CalculationORM]:
        return self.repo.list_recent(limit=limit)

    def get_calculation(self, calc_id: int) -> Optional[CalculationORM]:
        return self.repo.get_by_id(calc_id)

    def delete_calculation(self, calc_id: int) -> None:
        self.repo.delete(calc_id)

    def save_comparison(self, comparison: ComparisonResult, notes: str = "") -> int:
        snapshot = {
            "object_name": comparison.object_data.object_name,
            "area_m2": comparison.object_data.area_m2,
            "systems": [
                {
                    "name": s.system.system_name,
                    "total_dft": s.total_dft,
                    "total_cost_per_m2": s.total_cost_per_m2,
                    "total_cost": s.total_cost,
                    "layers_count": len(s.layers),
                }
                for s in comparison.systems
            ],
            "cheapest_index": comparison.cheapest_index,
            "best_balance_index": comparison.best_balance_index,
        }
        cmp = ComparisonORM(
            object_name=comparison.object_data.object_name or "",
            area_m2=comparison.object_data.area_m2 or 0.0,
            systems_count=len(comparison.systems),
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            notes=notes,
            created_at=datetime.utcnow(),
        )
        self.session.add(cmp)
        self.session.flush()
        return cmp.id

    def list_comparisons(self, limit: int = 50) -> Sequence[ComparisonORM]:
        from sqlalchemy import select
        stmt = (
            select(ComparisonORM)
            .order_by(ComparisonORM.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()