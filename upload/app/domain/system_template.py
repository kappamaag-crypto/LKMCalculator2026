"""Draft System Template model assembled from reviewed catalogue rows."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class TemplateLayer:
    layer_number: int
    material_name: str = "UNKNOWN"
    material_id: Optional[int] = None
    dft_min: Optional[float] = None
    dft_target: Optional[float] = None
    dft_max: Optional[float] = None
    source_path: str = ""
    source_sheet: str = ""
    source_row: Optional[int] = None
    source_sha256: str = ""

@dataclass(frozen=True)
class SystemTemplateDraft:
    name: str
    manufacturer: str = ""
    description: str = ""
    substrate: str = ""
    source_path: str = ""
    source_sheet: str = ""
    source_row: Optional[int] = None
    source_sha256: str = ""
    layers: tuple[TemplateLayer, ...] = ()
    notes: str = ""
    status: str = "DRAFT"
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Название System Template не может быть пустым")
        if self.status not in {"DRAFT", "REVIEW", "CONFIRMED"}:
            raise ValueError("Недопустимый статус System Template")
        numbers = [layer.layer_number for layer in self.layers]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("Номера слоёв должны идти последовательно начиная с 1")
        for layer in self.layers:
            if not layer.material_name.strip():
                raise ValueError("Материал слоя не может быть пустым")
            if any(value is not None and value < 0 for value in (layer.dft_min, layer.dft_target, layer.dft_max)):
                raise ValueError("Толщина слоя не может быть отрицательной")
            if layer.dft_min is not None and layer.dft_max is not None and layer.dft_min > layer.dft_max:
                raise ValueError("Минимальная толщина слоя больше максимальной")
            if layer.source_path and not layer.source_sha256:
                raise ValueError("Для указанного источника слоя требуется SHA-256")

    @property
    def layer_count(self) -> int:
        return len(self.layers)

    @property
    def has_unknown_materials(self) -> bool:
        return any(layer.material_id is None for layer in self.layers)

    @property
    def provenance_complete(self) -> bool:
        return bool(self.source_path and self.source_sha256 and all(layer.source_path and layer.source_sha256 for layer in self.layers))
