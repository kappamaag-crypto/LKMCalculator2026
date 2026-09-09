"""Application configuration."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "database.sqlite"
SETTINGS_PATH = DATA_DIR / "settings.json"
EXCEL_TEMPLATE_PATH = PROJECT_ROOT.parent / "КалькуляторЭКСЕЛЛЬ.xlsx"


@dataclass
class AppSettings:
    """User-configurable application settings."""

    organization_name: str = "Организация"
    organization_address: str = ""
    organization_phone: str = ""
    organization_email: str = ""
    logo_path: str = ""

    currency: str = "RUB"
    vat_rate: float = 20.0
    prices_include_vat: bool = True

    # Режим состава отчётов: engineering / commercial / full.
    # По умолчанию — инженерный, чтобы коммерческие цены не попадали
    # в инженерные отчёты без явного выбора пользователя.
    report_mode: str = "engineering"

    default_losses_percent: float = 0.0
    default_area_unit: str = "м²"
    export_dir: str = str(Path.home() / "Documents" / "LKM_Calculations")
    excel_template_path: str = str(EXCEL_TEMPLATE_PATH)

    language: str = "ru"

    weight_conditions: float = 0.30
    weight_corrosion: float = 0.20
    weight_durability: float = 0.15
    weight_temperature: float = 0.10
    weight_compatibility: float = 0.10
    weight_technology: float = 0.05
    weight_cost: float = 0.10

    def save(self, path: Path | None = None) -> None:
        path = path or SETTINGS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path | None = None) -> "AppSettings":
        path = path or SETTINGS_PATH
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def ensure_directories() -> None:
    """Create required directories if they do not exist."""
    for d in (DATA_DIR, BACKUP_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
