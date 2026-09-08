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
    items = [
        ("manufacturer", "Blank", "Blank"),
        ("manufacturer", "\u042d\u0424\u0424\u0410", "\u042d\u0424\u0424\u0410"),
        ("manufacturer", "Hempel", "Hempel"),
        ("manufacturer", "Jotun", "Jotun"),
        ("manufacturer", "Tikkurila", "Tikkurila"),
        ("binder", "\u044d\u043f\u043e\u043a\u0441\u0438\u0434", "\u042d\u043f\u043e\u043a\u0441\u0438\u0434"),
        ("binder", "\u043f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d", "\u041f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d"),
        ("binder", "\u0430\u043a\u0440\u0438\u043b", "\u0410\u043a\u0440\u0438\u043b"),
        ("binder", "\u0430\u043b\u043a\u0438\u0434", "\u0410\u043b\u043a\u0438\u0434"),
        ("binder", "\u0446\u0438\u043d\u043a-\u044d\u0442\u0438\u043b\u0441\u0438\u043b\u0438\u043a\u0430\u0442", "\u0426\u0438\u043d\u043a-\u044d\u0442\u0438\u043b\u0441\u0438\u043b\u0438\u043a\u0430\u0442"),
        ("corrosion", "C1", "C1"),
        ("corrosion", "C2", "C2"),
        ("corrosion", "C3", "C3"),
        ("corrosion", "C4", "C4"),
        ("corrosion", "C5", "C5"),
        ("corrosion", "CX", "CX"),
        ("durability", "Low", "Low (\u0434\u043e 7 \u043b\u0435\u0442)"),
        ("durability", "Medium", "Medium (7\u201315 \u043b\u0435\u0442)"),
        ("durability", "High", "High (15\u201325 \u043b\u0435\u0442)"),
        ("durability", "Very High", "Very High (> 25 \u043b\u0435\u0442)"),
    ]
    for dict_type, code, name in items:
        exists = session.query(DictionaryORM).filter_by(dict_type=dict_type, name=name).first()
        if not exists:
            session.add(DictionaryORM(dict_type=dict_type, code=code, name=name))
    session.flush()


def seed_demo_materials(session: Session) -> dict[str, int]:
    demo = [
        {
            "manufacturer": "Blank", "brand": "Blank",
            "material_name": "\u0413\u0440\u0443\u043d\u0442-\u042d\u043c\u0430\u043b\u044c Blank Universal",
            "material_type": MaterialType.PRIMER_ENAMEL.value,
            "binder_type": BinderType.EPOXY.value,
            "density": 1.4, "solids_percent": 73.0, "price_per_kg": 552.0,
            "recommended_dft_min": 100, "recommended_dft_max": 200, "ral": "-",
            "notes": "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b (\u0438\u0437 \u0441\u0442\u0430\u0440\u043e\u0433\u043e Excel)",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank", "brand": "Blank",
            "material_name": "\u042d\u043c\u0430\u043b\u044c Blank Finish",
            "material_type": MaterialType.FINISH.value,
            "binder_type": BinderType.POLYURETHANE.value,
            "density": 1.3, "solids_percent": 58.0, "price_per_kg": 892.0,
            "recommended_dft_min": 60, "recommended_dft_max": 100, "ral": "9003",
            "notes": "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b (\u0438\u0437 \u0441\u0442\u0430\u0440\u043e\u0433\u043e Excel)",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank", "brand": "Blank",
            "material_name": "\u0420\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c \u0434\u043b\u044f \u0433\u0440\u0443\u043d\u0442\u0430",
            "material_type": MaterialType.THINNER.value,
            "binder_type": BinderType.OTHER.value,
            "density": 0.9, "solids_percent": 0.0, "price_per_kg": 0.0,
            "notes": "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0440\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c",
            "is_incomplete": True,
        },
        {
            "manufacturer": "Blank", "brand": "Blank",
            "material_name": "\u0420\u0430\u0441\u0442\u0432\u043e\u0440\u0438\u0442\u0435\u043b\u044c \u0434\u043b\u044f \u044d\u043c\u0430\u043b\u0438",
            "material_type": MaterialType.THINNER.value,
            "binder_type": BinderType.OTHER.value,
            "density": 0.9, "solids_percent": 0.0, "price_per_kg": 0.0,
            "notes": "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0440\u0430\u0441\u0442\u0432\u043e\u0440\u0438\u0442\u0435\u043b\u044c",
            "is_incomplete": True,
        },
    ]
    name_to_id: dict[str, int] = {}
    for data in demo:
        existing = session.query(MaterialORM).filter_by(material_name=data["material_name"]).first()
        if existing:
            name_to_id[data["material_name"]] = existing.id
            continue
        orm = MaterialORM(**data, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        session.add(orm)
        session.flush()
        name_to_id[data["material_name"]] = orm.id
    return name_to_id


def seed_demo_system(session: Session, name_to_id: dict[str, int]) -> None:
    system_name = "\u0421\u0438\u0441\u0442\u0435\u043c\u0430 Blank Universal + Finish (\u0434\u0435\u043c\u043e)"
    existing = session.query(CoatingSystemORM).filter_by(system_name=system_name).first()
    if existing:
        return
    system = CoatingSystemORM(
        system_name=system_name,
        manufacturer="Blank",
        description="\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u0430\u044f \u0434\u0432\u0443\u0445\u0441\u043b\u043e\u0439\u043d\u0430\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u0430 \u0438\u0437 \u0441\u0442\u0430\u0440\u043e\u0433\u043e Excel-\u043a\u0430\u043b\u044c\u043a\u0443\u043b\u044f\u0442\u043e\u0440\u0430",
        durability="Medium",
        total_dft_min=160, total_dft_max=300, number_of_layers=2,
        notes="\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435. \u0422\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 TDS.",
        is_active=True,
    )
    session.add(system)
    session.flush()
    primer_id = name_to_id.get("\u0413\u0440\u0443\u043d\u0442-\u042d\u043c\u0430\u043b\u044c Blank Universal")
    finish_id = name_to_id.get("\u042d\u043c\u0430\u043b\u044c Blank Finish")
    for layer in [
        CoatingSystemLayerORM(
            system_id=system.id, layer_number=1, material_id=primer_id,
            layer_type=MaterialType.PRIMER_ENAMEL.value, target_dft=200.0,
            dft_min=100, dft_max=200, thinner_percent=5.0,
        ),
        CoatingSystemLayerORM(
            system_id=system.id, layer_number=2, material_id=finish_id,
            layer_type=MaterialType.FINISH.value, target_dft=100.0,
            dft_min=60, dft_max=100, thinner_percent=5.0,
        ),
    ]:
        session.add(layer)
    session.flush()


def seed_compatibility(session: Session) -> None:
    rules = [
        ("\u044d\u043f\u043e\u043a\u0441\u0438\u0434", "\u044d\u043f\u043e\u043a\u0441\u0438\u0434", CompatibilityStatus.ALLOWED.value, "\u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u044c"),
        ("\u044d\u043f\u043e\u043a\u0441\u0438\u0434", "\u043f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d", CompatibilityStatus.ALLOWED.value, "\u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u044c"),
        ("\u043f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d", "\u043f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d", CompatibilityStatus.ALLOWED.value, ""),
        ("\u0430\u043b\u043a\u0438\u0434", "\u044d\u043f\u043e\u043a\u0441\u0438\u0434", CompatibilityStatus.WARNING.value, "\u0422\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u0438"),
        ("\u0430\u043b\u043a\u0438\u0434", "\u043f\u043e\u043b\u0438\u0443\u0440\u0435\u0442\u0430\u043d", CompatibilityStatus.WARNING.value, "\u0422\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u0438"),
    ]
    for from_b, to_b, status, notes in rules:
        exists = session.query(LayerCompatibilityORM).filter_by(from_binder=from_b, to_binder=to_b).first()
        if not exists:
            session.add(LayerCompatibilityORM(from_binder=from_b, to_binder=to_b, status=status, notes=notes))
    session.flush()


def run_seed(session: Session) -> None:
    seed_dictionaries(session)
    name_to_id = seed_demo_materials(session)
    seed_demo_system(session, name_to_id)
    seed_compatibility(session)
    session.commit()
    print("Seed completed: dictionaries, demo materials, demo system, compatibility rules.")
