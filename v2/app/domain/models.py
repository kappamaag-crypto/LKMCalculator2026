"""Domain models (pure Python dataclasses, no ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .enums import (
    MaterialType,
    BinderType,
    CorrosionCategory,
    DurabilityLevel,
    SurfaceType,
    PreparationGrade,
    ApplicationMethod,
    EnvironmentType,
    CompatibilityStatus,
)


@dataclass
class Material:
    id: Optional[int] = None
    manufacturer: str = ""
    brand: str = ""
    material_name: str = ""
    material_type: MaterialType = MaterialType.OTHER
    binder_type: BinderType = BinderType.UNKNOWN
    description: str = ""
    density: float = 0.0
    solids_percent: float = 0.0
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
    packaging_kg: Optional[float] = None
    packaging_l: Optional[float] = None
    is_active: bool = True
    is_incomplete: bool = False
    notes: str = ""
    datasheet: str = ""
    certificate: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def display_name(self) -> str:
        parts = [p for p in (self.manufacturer, self.brand, self.material_name) if p]
        return " ".join(parts) if parts else self.material_name or "\u0411\u0435\u0437 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f"


@dataclass
class LayerDefinition:
    material_id: Optional[int] = None
    material: Optional[Material] = None
    layer_number: int = 1
    layer_type: MaterialType = MaterialType.OTHER
    dft_min: Optional[float] = None
    dft_max: Optional[float] = None
    target_dft: float = 0.0
    thinner_percent: float = 0.0
    thinner_material_id: Optional[int] = None
    notes: str = ""


@dataclass
class LayerResult:
    material: Material
    target_dft: float
    losses_percent: float = 0.0
    thinner_percent: float = 0.0
    thinner: Optional[Material] = None
    wft: float = 0.0
    theoretical_coverage: float = 0.0
    practical_coverage: float = 0.0
    theoretical_consumption_l: float = 0.0
    practical_consumption_l: float = 0.0
    theoretical_consumption_kg: float = 0.0
    practical_consumption_kg: float = 0.0
    cost_per_m2: float = 0.0
    thinner_consumption_l: float = 0.0
    thinner_consumption_kg: float = 0.0
    thinner_cost_per_m2: float = 0.0
    total_consumption_kg: float = 0.0
    total_consumption_l: float = 0.0
    total_cost: float = 0.0
    packages_count: int = 0
    purchase_kg: float = 0.0
    remainder_kg: float = 0.0


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
    area_m2: float = 0.0
    elements_count: int = 1
    area_per_element: float = 0.0
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
    total_cost_per_m2: float = 0.0
    total_cost: float = 0.0
    total_thinner_cost: float = 0.0
    total_purchase_cost: float = 0.0
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
    rank: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class RecommendationResult:
    object_data: ObjectData
    items: list[RecommendationItem] = field(default_factory=list)
    insufficient_data: bool = False
    message: str = ""
    disclaimer: str = (
        "\u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u043e\u0434\u0431\u043e\u0440 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u0410\u041a\u0417. \u041e\u043a\u043e\u043d\u0447\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0432\u044b\u0431\u043e\u0440 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e "
        "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0442\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u043e\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0435\u0439 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f, \u043f\u0440\u043e\u0435\u043a\u0442\u043d\u044b\u043c\u0438 "
        "\u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f\u043c\u0438 \u0438 \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u044b\u043c\u0438 \u043d\u043e\u0440\u043c\u0430\u0442\u0438\u0432\u043d\u044b\u043c\u0438 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043c\u0438."
    )
    created_at: datetime = field(default_factory=datetime.now)
