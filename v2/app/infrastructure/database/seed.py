"""Seed initial data (demonstration materials and systems)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    MaterialORM,
    CoatingSystemORM,
    CoatingSystemLayerORM,
    LayerCompatibilityORM,
    DictionaryORM,
)
from app.domain.enums import MaterialType, BinderType, CompatibilityStatus


def seed_dictionaries(session: Session) -> None:
    """Заполнение справочников."""
    items = [
        ("manufacturer", "Blank", "Blank"),
        ("manufacturer", "ЭФФА", "ЭФФА"),
        ("manufacturer", "Hempel", "Hempel"),
        ("manufacturer", "Jotun", "Jotun"),
        ("manufacturer", "Tikkurila", "Tikkurila"),
        ("binder", "эпоксид", "Эпоксид"),
        ("binder", "полиуретан", "Полиуретан"),
        ("binder", "акрил", "Акрил"),
        ("binder", "алкид", "Алкид"),
        ("binder", "цинк-этилсиликат", "Цинк-этилсиликат"),
        ("corrosion", "C1", "C1"),
        ("corrosion", "C2", "C2"),
        ("corrosion", "C3", "C3"),
        ("corrosion", "C4", "C4"),
        ("corrosion", "C5", "C5"),
        ("corrosion", "CX", "CX"),
        ("durability", "Low", "Low (до 7 лет)"),
        ("durability", "Medium", "Medium (7–15 лет)"),
        ("durability", "High", "High (15–25 лет)"),
        ("durability", "Very High", "Very High (> 25 лет)"),
    ]
    for dict_type, code, name in items:
        exists = session.query(DictionaryORM).filter_by(dict_type=dict_type, name=name).first()
        if not exists:
            session.add(DictionaryORM(dict_type=dict_type, code=code, name=name))
    session.flush()


def seed_demo_materials(session: Session) -> dict[str, int]:
    """
    Демонстрационные материалы (на основе Excel-примера).
    Возвращает словарь {имя: id}.
    """
    demo = [
        {
            "manufacturer": "Blank",
            "brand": "Blank",
            "material_name": "Грунт-Эмаль Blank Universal",
            "material_type": MaterialType.PRIMER_ENAMEL.value,
            "binder_type": BinderType.EPOXY.value,
            "density": 1.4,
            "solids_percent": 73.0,
            "price_per_kg": 552.0,
            "recommended_dft_min": 100,
            "recommended_dft_max": 200,
            "ral": "-",
            "notes": "Демонстрационный материал (из старого Excel)",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank",
            "brand": "Blank",
            "material_name": "Эмаль Blank Finish",
            "material_type": MaterialType.FINISH.value,
            "binder_type": BinderType.POLYURETHANE.value,
            "density": 1.3,
            "solids_percent": 58.0,
            "price_per_kg": 892.0,
            "recommended_dft_min": 60,
            "recommended_dft_max": 100,
            "ral": "9003",
            "notes": "Демонстрационный материал (из старого Excel)",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank",
            "brand": "Blank",
            "material_name": "Разбавитель для грунта",
            "material_type": MaterialType.THINNER.value,
            "binder_type": BinderType.OTHER.value,
            "density": 0.9,
            "solids_percent": 0.0,
            "price_per_kg": 0.0,
            "notes": "Демонстрационный разбавитель",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank",
            "brand": "Blank",
            "material_name": "Растворитель для эмали",
            "material_type": MaterialType.THINNER.value,
            "binder_type": BinderType.OTHER.value,
            "density": 0.9,
            "solids_percent": 0.0,
            "price_per_kg": 0.0,
            "notes": "Демонстрационный растворитель",
            "is_incomplete": True,
        },
    ]

    name_to_id: dict[str, int] = {}
    for data in demo:
        existing = (
            session.query(MaterialORM)
            .filter_by(material_name=data["material_name"])
            .first()
        )
        if existing:
            name_to_id[data["material_name"]] = existing.id
            continue
        orm = MaterialORM(**data, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        session.add(orm)
        session.flush()
        name_to_id[data["material_name"]] = orm.id

    return name_to_id


def seed_demo_system(session: Session, name_to_id: dict[str, int]) -> None:
    """Демонстрационная система на основе Excel."""
    system_name = "Система Blank Universal + Finish (демо)"
    existing = session.query(CoatingSystemORM).filter_by(system_name=system_name).first()
    if existing:
        return

    system = CoatingSystemORM(
        system_name=system_name,
        manufacturer="Blank",
        description="Демонстрационная двухслойная система из старого Excel-калькулятора",
        durability="Medium",
        total_dft_min=160,
        total_dft_max=300,
        number_of_layers=2,
        notes="Демонстрационные данные. Требуется подтверждение TDS.",
        is_active=True,
    )
    session.add(system)
    session.flush()

    primer_id = name_to_id.get("Грунт-Эмаль Blank Universal")
    finish_id = name_to_id.get("Эмаль Blank Finish")

    layers = [
        CoatingSystemLayerORM(
            system_id=system.id,
            layer_number=1,
            material_id=primer_id,
            layer_type=MaterialType.PRIMER_ENAMEL.value,
            target_dft=200.0,
            dft_min=100,
            dft_max=200,
            thinner_percent=5.0,
        ),
        CoatingSystemLayerORM(
            system_id=system.id,
            layer_number=2,
            material_id=finish_id,
            layer_type=MaterialType.FINISH.value,
            target_dft=100.0,
            dft_min=60,
            dft_max=100,
            thinner_percent=5.0,
        ),
    ]
    for layer in layers:
        session.add(layer)
    session.flush()


def seed_compatibility(session: Session) -> None:
    """Базовые правила совместимости (демонстрационные)."""
    rules = [
        ("эпоксид", "эпоксид", CompatibilityStatus.ALLOWED.value, "Стандартная совместимость"),
        ("эпоксид", "полиуретан", CompatibilityStatus.ALLOWED.value, "Стандартная совместимость"),
        ("полиуретан", "полиуретан", CompatibilityStatus.ALLOWED.value, ""),
        ("алкид", "эпоксид", CompatibilityStatus.WARNING.value, "Требуется проверка совместимости"),
        ("алкид", "полиуретан", CompatibilityStatus.WARNING.value, "Требуется проверка совместимости"),
    ]
    for from_b, to_b, status, notes in rules:
        exists = (
            session.query(LayerCompatibilityORM)
            .filter_by(from_binder=from_b, to_binder=to_b)
            .first()
        )
        if not exists:
            session.add(
                LayerCompatibilityORM(
                    from_binder=from_b,
                    to_binder=to_b,
                    status=status,
                    notes=notes,
                )
            )
    session.flush()


def run_seed(session: Session) -> None:
    """Запуск полного seed."""
    seed_dictionaries(session)
    name_to_id = seed_demo_materials(session)
    seed_demo_system(session, name_to_id)
    seed_compatibility(session)
    session.commit()
    print("Seed completed: dictionaries, demo materials, demo system, compatibility rules.")