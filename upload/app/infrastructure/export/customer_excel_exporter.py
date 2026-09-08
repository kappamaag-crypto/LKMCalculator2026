"""Экспорт в пользовательский Excel-шаблон.

Шаблон не перестраивается с нуля: существующая книга копируется и заполняется
по найденным подписям. Если шаблон недоступен или его структура не содержит
распознаваемых полей, используется стандартный ExcelExporter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

from app.config import AppSettings
from app.domain.models import SystemCalculationResult, RecommendationResult
from app.infrastructure.export.excel_exporter import ExcelExporter


class CustomerExcelExporter(ExcelExporter):
    """Сохраняет исходный пользовательский шаблон и заполняет его данными."""

    LABELS = {
        "object": ("объект", "название объекта"),
        "customer": ("заказчик",),
        "area": ("площадь", "площадь, м²", "площадь м2"),
        "system": ("система", "система покрытия"),
        "corrosion": ("категория коррозии", "категория"),
        "durability": ("долговечность",),
        "total_dft": ("общая толщина", "суммарная толщина", "толщина dft"),
        "cost_m2": ("стоимость, руб/м²", "стоимость руб/м2", "стоимость м²"),
        "total_cost": ("стоимость объекта", "итого стоимость"),
    }

    def __init__(self, settings: Optional[AppSettings] = None):
        super().__init__(settings)

    @staticmethod
    def _text(value) -> str:
        return str(value).strip().lower() if value is not None else ""

    def _find_label_cell(self, wb, aliases: tuple[str, ...]):
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    text = self._text(cell.value)
                    if any(alias in text for alias in aliases):
                        return ws, cell
        return None, None

    def _put_next_to_label(self, wb, aliases: tuple[str, ...], value) -> bool:
        ws, cell = self._find_label_cell(wb, aliases)
        if cell is None:
            return False
        # Предпочитаем соседнюю ячейку справа; если она объединена/занята,
        # пробуем следующую.
        for offset in (1, 2, 3):
            target = ws.cell(cell.row, cell.column + offset)
            if target.value in (None, ""):
                target.value = value
                return True
        return False

    def _fill_layers(self, wb, result: SystemCalculationResult) -> int:
        """Заполняет таблицу слоёв, если в шаблоне найдена строка заголовков."""
        written = 0
        for ws in wb.worksheets:
            header_row = None
            columns = {}
            for row in ws.iter_rows():
                texts = {cell.column: self._text(cell.value) for cell in row}
                dft_col = next((c for c, t in texts.items() if "dft" in t), None)
                material_col = next((c for c, t in texts.items() if "материал" in t), None)
                if dft_col and material_col:
                    header_row = row[0].row
                    columns = {"material": material_col, "dft": dft_col}
                    columns["wft"] = next((c for c, t in texts.items() if "wft" in t), None)
                    columns["losses"] = next((c for c, t in texts.items() if "потери" in t), None)
                    columns["thinner"] = next((c for c, t in texts.items() if "разб" in t), None)
                    columns["kg_m2"] = next((c for c, t in texts.items() if "кг/м" in t), None)
                    columns["l_m2"] = next((c for c, t in texts.items() if "л/м" in t), None)
                    columns["cost_m2"] = next((c for c, t in texts.items() if "руб/м" in t or "стоимость" in t), None)
                    break
            if header_row is None:
                continue

            for index, layer in enumerate(result.layers, start=1):
                row_no = header_row + index
                values = {
                    "material": layer.material.material_name,
                    "dft": layer.target_dft,
                    "wft": layer.wft,
                    "losses": layer.losses_percent,
                    "thinner": layer.thinner_percent,
                    "kg_m2": layer.practical_consumption_kg,
                    "l_m2": layer.practical_consumption_l,
                    "cost_m2": layer.cost_per_m2 + layer.thinner_cost_per_m2,
                }
                for key, value in values.items():
                    col = columns.get(key)
                    if col:
                        ws.cell(row_no, col, value)
                        written += 1
        return written

    def export_calculation(
        self,
        result: SystemCalculationResult,
        path: str | Path,
        recommendation: Optional[RecommendationResult] = None,
    ) -> Path:
        path = Path(path)
        template = Path(self.settings.excel_template_path)

        if not template.exists() or template.resolve() == path.resolve():
            return super().export_calculation(result, path, recommendation)

        wb = load_workbook(template)
        obj = result.object_data
        values = {
            "object": obj.object_name or None,
            "customer": obj.customer or None,
            "area": obj.area_m2 if obj.area_m2 > 0 else None,
            "system": result.system.system_name or None,
            "corrosion": obj.corrosion_category.value if obj.corrosion_category else None,
            "durability": obj.durability.value if obj.durability else None,
            "total_dft": result.total_dft,
            "cost_m2": result.total_cost_per_m2,
            "total_cost": result.total_cost,
        }

        for key, value in values.items():
            if value is not None:
                self._put_next_to_label(wb, self.LABELS[key], value)

        self._fill_layers(wb, result)
        wb.save(path)
        return path
