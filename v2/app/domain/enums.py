"""Domain enumerations."""

from __future__ import annotations

from enum import Enum, IntEnum


class MaterialType(str, Enum):
    PRIMER = "грунт"
    PRIMER_ENAMEL = "грунт-эмаль"
    ENAMEL = "эмаль"
    INTERMEDIATE = "промежуточное покрытие"
    FINISH = "финишное покрытие"
    EPOXY = "эпоксидное покрытие"
    POLYURETHANE = "полиуретановое покрытие"
    ZINC_RICH = "цинконаполненный грунт"
    ACRYLIC = "акриловое покрытие"
    ALKYD = "алкидное покрытие"
    SPECIAL = "специализированное покрытие"
    THINNER = "разбавитель"
    OTHER = "прочее"


class BinderType(str, Enum):
    EPOXY = "эпоксид"
    POLYURETHANE = "полиуретан"
    ACRYLIC = "акрил"
    ALKYD = "алкид"
    ZINC_ETHYL_SILICATE = "цинк-этилсиликат"
    EPOXY_ESTER = "эпоксидный эфир"
    OTHER = "прочее"
    UNKNOWN = "не указано"


class CorrosionCategory(str, Enum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"
    CX = "CX"
    IM1 = "Im1"
    IM2 = "Im2"
    IM3 = "Im3"
    IM4 = "Im4"


class DurabilityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class SurfaceType(str, Enum):
    NEW_STEEL = "новая сталь"
    PREVIOUSLY_PAINTED = "ранее окрашенная сталь"
    GALVANIZED = "оцинкованная сталь"
    STAINLESS = "нержавеющая сталь"
    REPAIR = "ремонтное покрытие"
    OTHER = "прочее"


class PreparationGrade(str, Enum):
    SA_1 = "Sa 1"
    SA_2 = "Sa 2"
    SA_2_5 = "Sa 2½"
    SA_3 = "Sa 3"
    ST_2 = "St 2"
    ST_3 = "St 3"
    MANUAL = "ручная подготовка"
    MECHANICAL = "механическая подготовка"
    OTHER = "прочее"


class ApplicationMethod(str, Enum):
    AIRLESS = "безвоздушное распыление"
    AIR = "пневматическое распыление"
    BRUSH = "кисть"
    ROLLER = "валик"
    DIPPING = "окунание"
    OTHER = "прочее"


class EnvironmentType(str, Enum):
    OUTDOOR = "наружная"
    INDOOR = "внутренняя"
    INDUSTRIAL = "промышленная"
    MARINE = "морская"
    CHEMICAL = "химическая"
    URBAN = "городская"
    RURAL = "сельская"


class CompatibilityStatus(str, Enum):
    ALLOWED = "разрешено"
    WARNING = "предупреждение"
    FORBIDDEN = "запрещено"
    UNKNOWN = "нет подтвержденных данных"


class PriceMode(str, Enum):
    PER_KG = "за кг"
    PER_LITER = "за литр"
