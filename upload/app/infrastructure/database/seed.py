"""Seed initial data and the curated SPKEFFA product catalog."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from app.infrastructure.database.models import MaterialORM, MaterialComponentORM, MaterialMixORM, CoatingSystemORM, CoatingSystemLayerORM, LayerCompatibilityORM, DictionaryORM
from app.domain.enums import MaterialType, BinderType, CompatibilityStatus
from app.domain.compatibility import check_binders

CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "spkeffa_catalog.json"


def seed_dictionaries(session: Session) -> None:
    items = [
        ("manufacturer", "Blank", "Blank"), ("manufacturer", "ЭФФА", "ЭФФА"), ("manufacturer", "Veksa", "Veksa"),
        ("manufacturer", "Hempel", "Hempel"), ("manufacturer", "Jotun", "Jotun"), ("manufacturer", "Tikkurila", "Tikkurila"),
        ("binder", "эпоксид", "Эпоксид"), ("binder", "полиуретан", "Полиуретан"), ("binder", "акрил", "Акрил"),
        ("binder", "алкид", "Алкид"), ("binder", "цинк-этилсиликат", "Цинк-этилсиликат"),
        *[("corrosion", x, x) for x in ("C1", "C2", "C3", "C4", "C5", "CX")],
        ("durability", "Low", "Low (до 7 лет)"), ("durability", "Medium", "Medium (7–15 лет)"),
        ("durability", "High", "High (15–25 лет)"), ("durability", "Very High", "Very High (> 25 лет)"),
    ]
    for dict_type, code, name in items:
        if not session.query(DictionaryORM).filter_by(dict_type=dict_type, name=name).first():
            session.add(DictionaryORM(dict_type=dict_type, code=code, name=name))
    session.flush()


def seed_demo_materials(session: Session) -> dict[str, int]:
    demo = [
        {"manufacturer":"Blank","brand":"Blank","material_name":"Грунт-Эмаль Blank Universal","material_type":MaterialType.PRIMER_ENAMEL.value,"binder_type":BinderType.EPOXY.value,"density":1.4,"solids_percent":73.0,"solids_by_volume_percent":73.0,"price_per_kg":552.0,"recommended_dft_min":100,"recommended_dft_max":200,"ral":"-","notes":"Демонстрационный материал (из старого Excel)","is_incomplete":True},
        {"manufacturer":"Blank","brand":"Blank","material_name":"Эмаль Blank Finish","material_type":MaterialType.FINISH.value,"binder_type":BinderType.POLYURETHANE.value,"density":1.3,"solids_percent":58.0,"solids_by_volume_percent":58.0,"price_per_kg":892.0,"recommended_dft_min":60,"recommended_dft_max":100,"ral":"9003","notes":"Демонстрационный материал (из старого Excel)","is_incomplete":True},
        {"manufacturer":"Blank","brand":"Blank","material_name":"Разбавитель для грунта","material_type":MaterialType.THINNER.value,"binder_type":BinderType.OTHER.value,"density":0.9,"solids_percent":0.0,"price_per_kg":None,"notes":"Демонстрационный разбавитель","is_incomplete":True},
        {"manufacturer":"Blank","brand":"Blank","material_name":"Растворитель для эмали","material_type":MaterialType.THINNER.value,"binder_type":BinderType.OTHER.value,"density":0.9,"solids_percent":0.0,"price_per_kg":None,"notes":"Демонстрационный растворитель","is_incomplete":True},
    ]
    result = {}
    now = datetime.now(timezone.utc)
    for data in demo:
        existing = session.query(MaterialORM).filter_by(material_name=data["material_name"]).first()
        if existing:
            changed = False
            for key in ("density", "solids_percent", "solids_by_volume_percent", "price_per_kg", "recommended_dft_min", "recommended_dft_max"):
                value = data.get(key)
                if value is not None and getattr(existing, key, None) is None:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                existing.updated_at = now
            result[data["material_name"]] = existing.id
            continue
        orm = MaterialORM(**data, created_at=now, updated_at=now)
        session.add(orm); session.flush(); result[data["material_name"]] = orm.id
    return result


def _seed_verified_2k_metadata(session: Session, material_name: str, material_id: int) -> None:
    if material_name != "VEKSA PP 11": return
    mix = session.query(MaterialMixORM).filter_by(material_id=material_id).first()
    if not mix:
        session.add(MaterialMixORM(material_id=material_id, mix_ratio_a=4.7, mix_ratio_b=1.0, ratio_basis="mass", working_time_minutes=40.0, notes="Источник SPKEFFA: TDS/карточка VEKSA PP 11."))
    for code, name in (("A", "Компонент A"), ("B", "Компонент B")):
        if not session.query(MaterialComponentORM).filter_by(material_id=material_id, component_code=code).first():
            session.add(MaterialComponentORM(material_id=material_id, component_code=code, name=name, active=True))
    session.flush()


def seed_spkeffa_catalog(session: Session) -> dict[str, int]:
    if not CATALOG_PATH.exists(): return {}
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    result = {}
    now = datetime.now(timezone.utc)
    allowed = {"manufacturer","brand","material_name","material_type","binder_type","density","solids_percent","solids_by_volume_percent","voc","color","ral","price_per_kg","price_per_liter","prices_include_vat","theoretical_coverage","min_application_temperature","max_application_temperature","min_recoat_time_h","max_recoat_time_h","drying_time_h","full_cure_time_h","pot_life_h","induction_time_min","max_relative_humidity","min_dew_point_margin_c","recommended_dft_min","recommended_dft_max","max_single_layer_dft","thinner_required","thinner_name","thinner_percent_min","thinner_percent_max","thinner_basis","packaging_kg","packaging_l","is_two_component","datasheet","datasheet_version","datasheet_date","safety_data_sheet","certificate","certificate_version","test_protocol"}
    preserve_if_unknown = {"density","solids_percent","solids_by_volume_percent","price_per_kg","price_per_liter","packaging_kg","packaging_l","datasheet","datasheet_version","datasheet_date","safety_data_sheet","certificate","certificate_version","test_protocol"}
    for item in payload.get("materials", []):
        name = item["material_name"]
        brand = item.get("brand", "")
        existing = session.query(MaterialORM).filter_by(brand=brand, material_name=name).first()
        fields = {k:v for k,v in item.items() if k in allowed}
        fields["is_incomplete"] = bool(item.get("density") is None or item.get("solids_by_volume_percent") is None or not item.get("datasheet"))
        fields["notes"] = f"Источник: {item.get('source_url', '')}. {item.get('notes', '')}".strip()
        if existing:
            for key, value in fields.items():
                if value is None and key in preserve_if_unknown: continue
                setattr(existing, key, value)
            existing.updated_at = now; material_id = existing.id
        else:
            orm = MaterialORM(**fields, created_at=now, updated_at=now)
            session.add(orm); session.flush(); material_id = orm.id
        result[name] = material_id
        _seed_verified_2k_metadata(session, name, material_id)
    session.flush(); return result


def seed_demo_system(session: Session, name_to_id: dict[str, int]) -> None:
    system_name = "Система Blank Universal + Finish (демо)"
    if session.query(CoatingSystemORM).filter_by(system_name=system_name).first(): return
    system = CoatingSystemORM(system_name=system_name, manufacturer="Blank", description="Демонстрационная двухслойная система из старого Excel-калькулятора", durability="Medium", total_dft_min=160, total_dft_max=300, number_of_layers=2, notes="Демонстрационные данные. Требуется подтверждение TDS.", is_active=True)
    session.add(system); session.flush()
    session.add_all([
        CoatingSystemLayerORM(system_id=system.id, layer_number=1, material_id=name_to_id.get("Грунт-Эмаль Blank Universal"), layer_type=MaterialType.PRIMER_ENAMEL.value, target_dft=200.0, dft_min=100, dft_max=200, thinner_percent=5.0),
        CoatingSystemLayerORM(system_id=system.id, layer_number=2, material_id=name_to_id.get("Эмаль Blank Finish"), layer_type=MaterialType.FINISH.value, target_dft=100.0, dft_min=60, dft_max=100, thinner_percent=5.0),
    ]); session.flush()


def seed_compatibility(session: Session) -> None:
    """Persist only compatibility pairs backed by the source matrix.

    The source table is directional (previous -> applied). Blank cells are
    unknown and therefore are not inserted as permissive rules.
    """
    supported = [BinderType.EPOXY, BinderType.POLYURETHANE, BinderType.ACRYLIC]
    for previous in supported:
        for applied in supported:
            rule = check_binders(previous, applied)
            existing = session.query(LayerCompatibilityORM).filter_by(
                from_binder=previous.value,
                to_binder=applied.value,
            ).first()
            if rule.status is CompatibilityStatus.UNKNOWN:
                if existing:
                    session.delete(existing)
                continue
            if existing is None:
                session.add(LayerCompatibilityORM(
                    from_binder=previous.value,
                    to_binder=applied.value,
                    status=rule.status.value,
                    notes=f"{rule.note}. Источник: {rule.source}.",
                ))
            else:
                existing.status = rule.status.value
                existing.notes = f"{rule.note}. Источник: {rule.source}."
    # These rules existed before the source matrix was introduced and were
    # generic assumptions rather than source-backed entries.
    for from_binder, to_binder in ((BinderType.ALKYD.value, BinderType.EPOXY.value), (BinderType.ALKYD.value, BinderType.POLYURETHANE.value)):
        stale = session.query(LayerCompatibilityORM).filter_by(from_binder=from_binder, to_binder=to_binder).first()
        if stale:
            session.delete(stale)
    session.flush()


def run_seed(session: Session) -> None:
    seed_dictionaries(session); demo_ids = seed_demo_materials(session); catalog_ids = seed_spkeffa_catalog(session); demo_ids.update(catalog_ids); seed_demo_system(session, demo_ids); seed_compatibility(session); session.commit()
    print(f"Seed completed: dictionaries, {len(catalog_ids)} SPKEFFA materials, demo system, compatibility rules.")
