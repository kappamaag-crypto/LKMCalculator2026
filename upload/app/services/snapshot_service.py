"""Pure helpers for restoring calculation inputs from immutable snapshots."""

from __future__ import annotations

from typing import Any, Optional

from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material


def _enum_or_default(enum_cls, value: Any, default):
    if value is None:
        return default
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return default


def material_from_snapshot(item: dict[str, Any], current: Optional[Material] = None) -> Material:
    """Build a calculation material from snapshot values, never current catalog values.

    Current catalog data is used only as a fallback for fields absent from legacy
    snapshots and for non-critical metadata. Calculation-critical engineering
    properties are always taken from the snapshot when present.
    """
    if not isinstance(item, dict):
        raise ValueError("Некорректные данные материала в снимке истории.")

    def value(key: str, fallback=None):
        return item[key] if key in item else fallback

    base = current or Material()
    return Material(
        id=value("material_id", base.id),
        manufacturer=value("manufacturer", base.manufacturer),
        brand=value("brand", base.brand),
        material_name=value("material_name", base.material_name),
        material_type=_enum_or_default(MaterialType, value("material_type", None), base.material_type),
        binder_type=_enum_or_default(BinderType, value("binder", None), base.binder_type),
        description=base.description,
        density=value("density", base.density),
        solids_percent=value("solids_percent", base.solids_percent),
        solids_by_volume_percent=value("solids_by_volume_percent", base.solids_by_volume_percent),
        voc=base.voc,
        color=base.color,
        ral=base.ral,
        price_per_kg=value("price_per_kg", base.price_per_kg),
        price_per_liter=value("price_per_liter", base.price_per_liter),
        prices_include_vat=base.prices_include_vat,
        theoretical_coverage=base.theoretical_coverage,
        application_method=base.application_method,
        min_application_temperature=base.min_application_temperature,
        max_application_temperature=base.max_application_temperature,
        min_recoat_time_h=base.min_recoat_time_h,
        max_recoat_time_h=base.max_recoat_time_h,
        drying_time_h=base.drying_time_h,
        full_cure_time_h=base.full_cure_time_h,
        pot_life_h=base.pot_life_h,
        induction_time_min=base.induction_time_min,
        max_relative_humidity=base.max_relative_humidity,
        min_dew_point_margin_c=base.min_dew_point_margin_c,
        recommended_dft_min=base.recommended_dft_min,
        recommended_dft_max=base.recommended_dft_max,
        max_single_layer_dft=base.max_single_layer_dft,
        thinner_required=base.thinner_required,
        thinner_name=base.thinner_name,
        thinner_percent_min=base.thinner_percent_min,
        thinner_percent_max=base.thinner_percent_max,
        thinner_basis=value("thinner_basis", base.thinner_basis),
        packaging_kg=base.packaging_kg,
        packaging_l=base.packaging_l,
        is_two_component=base.is_two_component,
        datasheet=base.datasheet,
        datasheet_version=base.datasheet_version,
        datasheet_date=base.datasheet_date,
        safety_data_sheet=base.safety_data_sheet,
        certificate=base.certificate,
        certificate_version=base.certificate_version,
        test_protocol=base.test_protocol,
        is_active=base.is_active,
        is_incomplete=base.is_incomplete,
        notes=base.notes,
        created_at=base.created_at,
        updated_at=base.updated_at,
    )


def thinner_from_snapshot(item: dict[str, Any], current: Optional[Material] = None) -> Material:
    """Build thinner from snapshot values, with catalog fallback only for absent legacy fields."""
    if not isinstance(item, dict):
        raise ValueError("Некорректные данные разбавителя в снимке истории.")

    thinner_item = dict(item)
    thinner_item["material_id"] = item.get("thinner_id")
    if "thinner_name" in item:
        thinner_item["material_name"] = item.get("thinner_name")
    elif current is not None:
        thinner_item["material_name"] = current.material_name

    # Do not manufacture None values for legacy snapshots: an absent field is
    # deliberately allowed to fall back to the current catalog row. An explicit
    # None in a modern snapshot remains None and therefore means "unknown".
    for snapshot_key, material_key in (
        ("thinner_density", "density"),
        ("thinner_price_per_kg", "price_per_kg"),
        ("thinner_price_per_liter", "price_per_liter"),
    ):
        if snapshot_key in item:
            thinner_item[material_key] = item[snapshot_key]

    thinner_item["material_type"] = MaterialType.THINNER.value
    return material_from_snapshot(thinner_item, current=current)
