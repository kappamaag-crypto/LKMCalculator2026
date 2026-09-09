"""Domain models (pure Python dataclasses, no ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .enums import MaterialType, BinderType, CorrosionCategory, DurabilityLevel, SurfaceType, PreparationGrade, ApplicationMethod, EnvironmentType


@dataclass
class Material:
    id: Optional[int] = None
    manufacturer: str = ""
    brand: str = ""
    material_name: str = ""
    material_type: MaterialType = MaterialType.OTHER
    binder_type: BinderType = BinderType.UNKNOWN
    description: str = ""
    density: Optional[float] = None
    solids_percent: Optional[float] = None
    solids_by_volume_percent: Optional[float] = None
    voc: Optional[float] = None
    color: str = ""
    ral: str = ""
    price_per_kg: Optional[float] = None
    price_per_liter: Optional[float] = None
    prices_include_vat: bool = True
    theoretical_coverage: Optional[float] = None
    application_method: Optional[ApplicationMethod] = None
    min_application_temperature: Optional[float] = None
    max_application_temperature: Optional[float] = None
    min_recoat_time_h: Optional[float] = None
    max_recoat_time_h: Optional[float] = None
    drying_time_h: Optional[float] = None
    full_cure_time_h: Optional[float] = None
    pot_life_h: Optional[float] = None
    induction_time_min: Optional[float] = None
    max_relative_humidity: Optional[float] = None
    min_dew_point_margin_c: Optional[float] = None
    surface_types: list[SurfaceType] = field(default_factory=list)
    corrosion_categories: list[CorrosionCategory] = field(default_factory=list)
    durability_levels: list[DurabilityLevel] = field(default_factory=list)
    environments: list[EnvironmentType] = field(default_factory=list)
    recommended_dft_min: Optional[float] = None
    recommended_dft_max: Optional[float] = None
    max_single_layer_dft: Optional[float] = None
    thinner_required: bool = False
    thinner_name: str = ""
    thinner_percent_min: Optional[float] = None
    thinner_percent_max: Optional[float] = None
    thinner_basis: str = "BY_PAINT_VOLUME"
    packaging_kg: Optional[float] = None
    packaging_l: Optional[float] = None
    is_two_component: bool = False
    datasheet: str = ""
    datasheet_version: str = ""
    datasheet_date: Optional[str] = None
    safety_data_sheet: str = ""
    certificate: str = ""
    certificate_version: str = ""
    test_protocol: str = ""
    is_active: bool = True
    is_incomplete: bool = False
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def display_name(self) -> str:
        parts = [p for p in (self.manufacturer, self.brand, self.material_name) if p]
        return " ".join(parts) if parts else self.material_name or "Без названия"


@dataclass
class LayerDefinition:
    material_id: Optional[int] = None
    material: Optional[Material] = None
    layer_number: int = 1
    layer_type: MaterialType = MaterialType.OTHER
    dft_min: Optional[float] = None
    dft_max: Optional[float] = None
    # None означает «DFT не задан», 0 — это уже явно заданное нулевое значение.
    target_dft: Optional[float] = None
    # 0 % разбавления — валидное значение «без разбавления», поэтому не трактуется как UNKNOWN.
    thinner_percent: float = 0.0
    thinner_material_id: Optional[int] = None
    thinner_basis: Optional[str] = None
    losses_percent: Optional[float] = None
    notes: str = ""


@dataclass
class LayerResult:
    material: Material
    target_dft: float
    losses_percent: float = 0.0
    thinner_percent: float = 0.0
    thinner: Optional[Material] = None
    thinner_basis: str = "BY_PAINT_VOLUME"
    wft: float = 0.0
    theoretical_coverage: float = 0.0
    practical_coverage: float = 0.0
    theoretical_consumption_l: float = 0.0
    practical_consumption_l: float = 0.0
    theoretical_consumption_kg: float = 0.0
    practical_consumption_kg: float = 0.0
    cost_per_m2: Optional[float] = None
    thinner_consumption_l: float = 0.0
    thinner_consumption_kg: float = 0.0
    thinner_cost_per_m2: Optional[float] = None
    total_consumption_kg: float = 0.0
    total_consumption_l: float = 0.0
    total_cost: Optional[float] = None


@dataclass
class CoatingSystem:
    id: Optional[int] = None
    system_name: str = ""
    manufacturer: str = ""
    description: str = ""
    corrosion_categories: list[CorrosionCategory] = field(default_factory=list)
    durability: Optional[DurabilityLevel] = None
    environments: list[EnvironmentType] = field(default_factory=list)
    surface_types: list[SurfaceType] = field(default_factory=list)
    substrate: str = ""
    total_dft_min: Optional[float] = None
    total_dft_target: Optional[float] = None
    total_dft_max: Optional[float] = None
    number_of_layers: int = 0
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    application_methods: list[ApplicationMethod] = field(default_factory=list)
    standards: str = ""
    certificate: str = ""
    technical_document: str = ""
    notes: str = ""
    is_active: bool = True
    layers: list[LayerDefinition] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ObjectData:
    object_name: str = ""
    customer: str = ""
    project: str = ""
    calculation_number: str = ""
    # None означает «площадь не задана»; положительное значение — реальная площадь расчёта.
    area_m2: Optional[float] = None
    structure_type: str = ""
    substrate: str = ""
    application_method: Optional[ApplicationMethod] = None
    corrosion_category: Optional[CorrosionCategory] = None
    durability: Optional[DurabilityLevel] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity: Optional[float] = None
    environment: Optional[EnvironmentType] = None
    uv_exposure: bool = False
    water_contact: bool = False
    chemical_contact: bool = False
    surface_type: Optional[SurfaceType] = None
    preparation: Optional[PreparationGrade] = None
    roughness: Optional[float] = None
    surface_temperature: Optional[float] = None
    air_temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    dew_point: Optional[float] = None
    dew_point_margin_c: Optional[float] = None
    notes: str = ""


@dataclass
class SystemCalculationResult:
    system: CoatingSystem
    object_data: ObjectData
    layers: list[LayerResult] = field(default_factory=list)
    total_dft: float = 0.0
    total_theoretical_consumption_kg: float = 0.0
    total_practical_consumption_kg: float = 0.0
    total_theoretical_consumption_l: float = 0.0
    total_practical_consumption_l: float = 0.0
    total_cost_per_m2: Optional[float] = None
    total_cost: Optional[float] = None
    total_thinner_cost: Optional[float] = None
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComparisonResult:
    object_data: ObjectData
    systems: list[SystemCalculationResult] = field(default_factory=list)
    cheapest_index: Optional[int] = None
    most_expensive_index: Optional[int] = None
    thinnest_index: Optional[int] = None
    thickest_index: Optional[int] = None
    fewest_layers_index: Optional[int] = None
    best_balance_index: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RecommendationItem:
    system: CoatingSystem
    score: float
    breakdown: object | None = None
    rank: int = 0
    status: str = ""
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class RecommendationResult:
    object_data: ObjectData
    items: list[RecommendationItem] = field(default_factory=list)
    insufficient_data: bool = False
    message: str = ""
    disclaimer: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class MaterialComponent:
    id: Optional[int] = None
    material_id: Optional[int] = None
    component_code: str = "A"
    name: str = ""
    density_kg_l: Optional[float] = None
    price_per_kg: Optional[float] = None
    price_per_liter: Optional[float] = None
    packaging_kg: Optional[float] = None
    packaging_l: Optional[float] = None
    active: bool = True


@dataclass(frozen=True)
class MaterialMix:
    material_id: int
    mix_ratio_a: float
    mix_ratio_b: float
    ratio_basis: str = "mass"
    working_time_minutes: Optional[float] = None
    induction_time_minutes: Optional[float] = None
    temperature_reference: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class Package:
    id: Optional[int] = None
    material_id: Optional[int] = None
    component_id: Optional[int] = None
    package_name: str = ""
    net_weight_kg: Optional[float] = None
    net_volume_l: Optional[float] = None
    units_per_set: int = 1
    package_type: str = "single"
    is_component_package: bool = False
    active: bool = True


@dataclass(frozen=True)
class ChemicalExposure:
    id: Optional[int] = None
    object_id: Optional[int] = None
    medium_name: str = ""
    concentration_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    contact_type: str = "NONE"
    duration: str = ""
    frequency: str = ""
    ph: Optional[float] = None
    immersion: bool = False
    notes: str = ""


@dataclass(frozen=True)
class MaterialCompatibility:
    id: Optional[int] = None
    material_a_id: Optional[int] = None
    material_b_id: Optional[int] = None
    compatibility: str = "UNKNOWN"
    conditions: str = ""
    source_document: str = ""
    notes: str = ""


@dataclass(frozen=True)
class CalculationSnapshot:
    id: Optional[int] = None
    calculation_id: Optional[int] = None
    created_at: Optional[datetime] = None
    project_name: str = ""
    object_data_json: str = "{}"
    system_data_json: str = "{}"
    materials_data_json: str = "{}"
    formula_version: str = "3.0"
    calculator_version: str = "3.0.0"
    result_json: str = "{}"


@dataclass(frozen=True)
class CommercialCalculation:
    material_cost: float = 0.0
    labor_cost: float = 0.0
    surface_prep_cost: float = 0.0
    equipment_cost: float = 0.0
    inspection_cost: float = 0.0
    logistics_cost: float = 0.0
    overhead_percent: float = 0.0
    margin_percent: float = 0.0
    subtotal: float = 0.0
    profit: float = 0.0
    vat_percent: float = 0.0
    vat_amount: float = 0.0
    total_price: float = 0.0
    price_per_m2: float = 0.0


@dataclass(frozen=True)
class LossProfile:
    id: Optional[int] = None
    application_method: str = ""
    equipment_type: str = ""
    surface_geometry: str = ""
    structure_complexity: str = ""
    loss_percent_min: Optional[float] = None
    loss_percent_default: Optional[float] = None
    loss_percent_max: Optional[float] = None
    transfer_efficiency: Optional[float] = None
    notes: str = ""
