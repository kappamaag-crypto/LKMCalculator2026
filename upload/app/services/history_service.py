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
from app.services.snapshot_utils import load_and_verify_snapshot, seal_snapshot


class HistoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CalculationRepository(session)

    def save_calculation(self, result: SystemCalculationResult, notes: str = "") -> int:
        """Сохранить расчёт как неизменяемый снимок входных данных и результата."""
        obj = result.object_data
        snapshot = {
            "snapshot_version": 4,
            "object": {
                "object_name": obj.object_name,
                "customer": obj.customer,
                "project": obj.project,
                "calculation_number": obj.calculation_number,
                "area_m2": obj.area_m2,
                "corrosion_category": obj.corrosion_category.value if obj.corrosion_category else None,
                "durability": obj.durability.value if obj.durability else None,
            },
            "system": {
                "name": result.system.system_name,
                "manufacturer": result.system.manufacturer,
                "description": result.system.description,
                "total_dft_min": result.system.total_dft_min,
                "total_dft_target": result.system.total_dft_target,
                "total_dft_max": result.system.total_dft_max,
            },
            "system_name": result.system.system_name,
            "total_dft": result.total_dft,
            "total_cost_per_m2": result.total_cost_per_m2,
            "total_cost": result.total_cost,
            "total_consumption_kg": result.total_practical_consumption_kg,
            "layers": [],
        }
        for lr in result.layers:
            snapshot["layers"].append({
                "material_id": lr.material.id,
                "material_name": lr.material.material_name,
                "manufacturer": lr.material.manufacturer,
                "brand": lr.material.brand,
                "material_type": lr.material.material_type.value if hasattr(lr.material.material_type, "value") else str(lr.material.material_type),
                "binder": lr.material.binder_type.value if hasattr(lr.material.binder_type, "value") else str(lr.material.binder_type),
                "density": lr.material.density,
                "solids_percent": lr.material.solids_percent,
                "solids_by_volume_percent": lr.material.solids_by_volume_percent,
                "price_per_kg": lr.material.price_per_kg,
                "price_per_liter": lr.material.price_per_liter,
                "target_dft": lr.target_dft,
                "losses_percent": lr.losses_percent,
                "thinner_percent": lr.thinner_percent,
                "thinner_name": lr.thinner.material_name if lr.thinner else None,
                "thinner_id": lr.thinner.id if lr.thinner else None,
                "thinner_density": lr.thinner.density if lr.thinner else None,
                "thinner_price_per_kg": lr.thinner.price_per_kg if lr.thinner else None,
                "thinner_price_per_liter": lr.thinner.price_per_liter if lr.thinner else None,
                "thinner_basis": lr.thinner_basis,
                "wft": lr.wft,
                "practical_consumption_kg": lr.practical_consumption_kg,
                "practical_consumption_l": lr.practical_consumption_l,
                "thinner_consumption_kg": lr.thinner_consumption_kg,
                "thinner_consumption_l": lr.thinner_consumption_l,
                "cost_per_m2": lr.cost_per_m2,
                "thinner_cost_per_m2": lr.thinner_cost_per_m2,
                "total_consumption_kg": lr.total_consumption_kg,
                "total_consumption_l": lr.total_consumption_l,
                "total_cost": lr.total_cost,
            })
        snapshot = seal_snapshot(snapshot)

        now = datetime.now(timezone.utc)
        calc = CalculationORM(
            calculation_number=obj.calculation_number or "",
            object_name=obj.object_name or "",
            customer=obj.customer or "",
            project=obj.project or "",
            area_m2=obj.area_m2 if obj.area_m2 is not None else null(),
            system_name=result.system.system_name or "Пользовательская",
            total_dft=result.total_dft,
            total_cost_per_m2=result.total_cost_per_m2 if result.total_cost_per_m2 is not None else null(),
            total_cost=result.total_cost if result.total_cost is not None else null(),
            total_consumption_kg=result.total_practical_consumption_kg,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        for i, lr in enumerate(result.layers):
            layer_snapshot = seal_snapshot(snapshot["layers"][i])
            calc.layers.append(CalculationLayerORM(
                layer_number=i + 1,
                material_name=lr.material.material_name,
                binder=lr.material.binder_type.value if hasattr(lr.material.binder_type, "value") else str(lr.material.binder_type),
                dry_thickness=lr.target_dft,
                consumption_kg=lr.practical_consumption_kg,
                consumption_l=lr.practical_consumption_l,
                cost_per_m2=lr.cost_per_m2 if lr.cost_per_m2 is not None else null(),
                snapshot_json=json.dumps(layer_snapshot, ensure_ascii=False),
            ))
        self.session.add(calc)
        self.session.flush()
        return calc.id

    def list_calculations(self, limit: int = 100) -> Sequence[CalculationORM]:
        return self.repo.list_recent(limit=limit)

    def get_calculation(self, calc_id: int) -> Optional[CalculationORM]:
        return self.repo.get_by_id(calc_id)

    def get_calculation_snapshot(self, calc_id: int) -> dict:
        """Read only a verified sealed snapshot; catalog changes cannot rewrite it."""
        calc = self.get_calculation(calc_id)
        if calc is None:
            raise KeyError(calc_id)
        return load_and_verify_snapshot(calc.snapshot_json)

    def delete_calculation(self, calc_id: int) -> None:
        self.repo.delete(calc_id)

    def save_comparison(self, comparison: ComparisonResult, notes: str = "") -> int:
        snapshot = {
            "snapshot_version": 2,
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
        snapshot = seal_snapshot(snapshot)
        cmp = ComparisonORM(
            object_name=comparison.object_data.object_name or "",
            area_m2=comparison.object_data.area_m2 if comparison.object_data.area_m2 is not None else null(),
            systems_count=len(comparison.systems),
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(cmp)
        self.session.flush()
        return cmp.id

    def get_comparison_snapshot(self, comparison_id: int) -> dict:
        """Read only a verified sealed comparison snapshot."""
        cmp = self.session.get(ComparisonORM, comparison_id)
        if cmp is None:
            raise KeyError(comparison_id)
        return load_and_verify_snapshot(cmp.snapshot_json)

    def list_comparisons(self, limit: int = 50) -> Sequence[ComparisonORM]:
        from sqlalchemy import select
        stmt = select(ComparisonORM).order_by(ComparisonORM.created_at.desc()).limit(limit)
        return self.session.scalars(stmt).all()
