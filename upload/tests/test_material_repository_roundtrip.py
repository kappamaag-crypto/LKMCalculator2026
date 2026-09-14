from app.domain.enums import ApplicationMethod, BinderType, MaterialType
from app.domain.models import Material
from app.infrastructure.database.models import MaterialORM
from app.infrastructure.database.repositories import material_domain_to_orm, material_orm_to_domain


ENGINEERING_FIELDS = [
    "manufacturer", "brand", "material_name", "material_type", "binder_type", "description",
    "density", "solids_percent", "solids_by_volume_percent", "voc", "color", "ral",
    "price_per_kg", "price_per_liter", "prices_include_vat", "theoretical_coverage",
    "application_method", "min_application_temperature", "max_application_temperature",
    "min_recoat_time_h", "max_recoat_time_h", "drying_time_h", "full_cure_time_h",
    "pot_life_h", "induction_time_min", "max_relative_humidity", "min_dew_point_margin_c",
    "recommended_dft_min", "recommended_dft_max", "max_single_layer_dft", "thinner_required",
    "thinner_name", "thinner_percent_min", "thinner_percent_max", "thinner_basis",
    "packaging_kg", "packaging_l", "is_two_component", "datasheet", "datasheet_version",
    "datasheet_date", "safety_data_sheet", "certificate", "certificate_version", "test_protocol",
    "is_active", "is_incomplete", "notes",
]


def test_material_engineering_fields_round_trip_without_loss():
    source = Material(
        id=42, manufacturer="Производитель", brand="Brand-X", material_name="Material-X",
        material_type=MaterialType.EPOXY, binder_type=BinderType.EPOXY,
        description="Полная инженерная карточка", density=1.37, solids_percent=68.5,
        solids_by_volume_percent=59.25, voc=310.0, color="серый", ral="RAL 7042",
        price_per_kg=607.25, price_per_liter=832.10, prices_include_vat=False,
        theoretical_coverage=4.25, application_method=ApplicationMethod.AIRLESS,
        min_application_temperature=-10.0, max_application_temperature=40.0,
        min_recoat_time_h=6.5, max_recoat_time_h=72.0, drying_time_h=3.25,
        full_cure_time_h=168.0, pot_life_h=2.0, induction_time_min=15.0,
        max_relative_humidity=85.0, min_dew_point_margin_c=3.0,
        recommended_dft_min=80.0, recommended_dft_max=150.0, max_single_layer_dft=250.0,
        thinner_required=True, thinner_name="Разбавитель-X", thinner_percent_min=5.0,
        thinner_percent_max=15.0, thinner_basis="BY_PAINT_VOLUME", packaging_kg=20.0,
        packaging_l=18.5, is_two_component=True, datasheet="TDS-X", datasheet_version="3.1",
        datasheet_date="2026-09-01", safety_data_sheet="SDS-X", certificate="CERT-X",
        certificate_version="2.0", test_protocol="TP-X", is_active=False, is_incomplete=True,
        notes="Проверено инженером",
    )

    orm = material_domain_to_orm(source, MaterialORM())
    restored = material_orm_to_domain(orm)

    for field in ENGINEERING_FIELDS:
        assert getattr(restored, field) == getattr(source, field), field


def test_material_engineering_none_values_remain_unknown_not_zero():
    source = Material(
        material_name="Incomplete", density=None, solids_percent=None,
        solids_by_volume_percent=None, voc=None, theoretical_coverage=None,
        application_method=None, min_application_temperature=None,
        max_application_temperature=None, min_recoat_time_h=None,
        max_recoat_time_h=None, drying_time_h=None, full_cure_time_h=None,
        pot_life_h=None, induction_time_min=None, max_relative_humidity=None,
        min_dew_point_margin_c=None, recommended_dft_min=None,
        recommended_dft_max=None, max_single_layer_dft=None,
        thinner_percent_min=None, thinner_percent_max=None, packaging_kg=None,
        packaging_l=None, datasheet_date=None,
    )

    restored = material_orm_to_domain(material_domain_to_orm(source, MaterialORM()))

    for field in (
        "density", "solids_percent", "solids_by_volume_percent", "voc", "theoretical_coverage",
        "application_method", "min_application_temperature", "max_application_temperature",
        "min_recoat_time_h", "max_recoat_time_h", "drying_time_h", "full_cure_time_h",
        "pot_life_h", "induction_time_min", "max_relative_humidity", "min_dew_point_margin_c",
        "recommended_dft_min", "recommended_dft_max", "max_single_layer_dft",
        "thinner_percent_min", "thinner_percent_max", "packaging_kg", "packaging_l", "datasheet_date",
    ):
        assert getattr(restored, field) is None, field
