"""Pure helpers for restoring calculation inputs from immutable snapshots."""

from __future__ import annotations

from typing import Any, Optional

from app.domain.enums import ApplicationMethod, BinderType, MaterialType
from app.domain.models import Material


def _enum_or_default(enum_cls, value: Any, default):
    if value is None:
        return default
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return default


def material_from_snapshot(item: dict[str, Any], current: Optional[Material] = None) -> Material:
    """Build a material from the snapshot, without catalog dependency for modern snapshots.

    ``current`` remains an optional compatibility fallback for legacy snapshots that
    predate the self-contained material payload. Explicit values from the snapshot,
    including explicit ``None``, are never replaced by catalog values.
    """
    if not isinstance(item, dict):
        raise ValueError("Некорректные данные материала в снимке истории.")

    base = current or Material()

    def value(key: str, fallback=None):
        return item[key] if key in item else fallback

    return Material(
        id=value("material_id", base.id),
        manufacturer=value("manufacturer", base.manufacturer),
        brand=value("brand", base.brand),
        material_name=value("material_name", base.material_name),
        material_type=_enum_or_default(MaterialType, value("material_type", None), base.material_type),
        binder_type=_enum_or_default(BinderType, value("binder", None), base.binder_type),
        description=value("description", base.description),
        density=value("density", base.density),
        solids_percent=value("solids_percent", base.solids_percent),
        solids_by_volume_percent=value("solids_by_volume_percent", base.solids_by_volume_percent),
        voc=value("voc", base.voc),
        color=value("color", base.color),
        ral=value("ral", base.ral),
        price_per_kg=value("price_per_kg", base.price_per_kg),
        price_per_liter=value("price_per_liter", base.price_per_liter),
        prices_include_vat=value("prices_include_vat", base.prices_include_vat),
        theoretical_coverage=value("theoretical_coverage", base.theoretical_coverage),
        application_method=_enum_or_default(ApplicationMethod, value("application_method", None), base.application_method),
        min_application_temperature=value("min_application_temperature", base.min_application_temperature),
        max_application_temperature=value("max_application_temperature", base.max_application_temperature),
        min_recoat_time_h=value("min_recoat_time_h", base.min_recoat_time_h),
        max_recoat_time_h=value("max_recoat_time_h", base.max_recoat_time_h),
        drying_time_h=value("drying_time_h", base.drying_time_h),
        full_cure_time_h=value("full_cure_time_h", base.full_cure_time_h),
        pot_life_h=value("pot_life_h", base.pot_life_h),
        induction_time_min=value("induction_time_min", base.induction_time_min),
        max_relative_humidity=value("max_relative_humidity", base.max_relative_humidity),
        min_dew_point_margin_c=value("min_dew_point_margin_c", base.min_dew_point_margin_c),
        recommended_dft_min=value("recommended_dft_min", base.recommended_dft_min),
        recommended_dft_max=value("recommended_dft_max", base.recommended_dft_max),
        max_single_layer_dft=value("max_single_layer_dft", base.max_single_layer_dft),
        thinner_required=value("thinner_required", base.thinner_required),
        thinner_name=value("thinner_name", base.thinner_name),
        thinner_percent_min=value("thinner_percent_min", base.thinner_percent_min),
        thinner_percent_max=value("thinner_percent_max", base.thinner_percent_max),
        thinner_basis=value("thinner_basis", base.thinner_basis),
        packaging_kg=value("packaging_kg", base.packaging_kg),
        packaging_l=value("packaging_l", base.packaging_l),
        is_two_component=value("is_two_component", base.is_two_component),
        datasheet=value("datasheet", base.datasheet),
        datasheet_version=value("datasheet_version", base.datasheet_version),
        datasheet_date=value("datasheet_date", base.datasheet_date),
        safety_data_sheet=value("safety_data_sheet", base.safety_data_sheet),
        certificate=value("certificate", base.certificate),
        certificate_version=value("certificate_version", base.certificate_version),
        test_protocol=value("test_protocol", base.test_protocol),
        is_active=value("is_active", base.is_active),
        is_incomplete=value("is_incomplete", base.is_incomplete),
        notes=value("notes", base.notes),
        created_at=base.created_at,
        updated_at=base.updated_at,
    )


def thinner_from_snapshot(item: dict[str, Any], current: Optional[Material] = None) -> Material:
    """Build thinner from snapshot values, with compatibility fallback for legacy data."""
    if not isinstance(item, dict):
        raise ValueError("Некорректные данные разбавителя в снимке истории.")

    thinner_item = dict(item)
    thinner_item["material_id"] = item.get("thinner_id")
    if "thinner_name" in item:
        thinner_item["material_name"] = item.get("thinner_name")
    elif current is not None:
        thinner_item["material_name"] = current.material_name

    for snapshot_key, material_key in (
        ("thinner_density", "density"),
        ("thinner_price_per_kg", "price_per_kg"),
        ("thinner_price_per_liter", "price_per_liter"),
    ):
        if snapshot_key in item:
            thinner_item[material_key] = item[snapshot_key]

    thinner_item["material_type"] = MaterialType.THINNER.value
    return material_from_snapshot(thinner_item, current=current)
