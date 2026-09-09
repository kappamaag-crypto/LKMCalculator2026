"""Экспорт расчёта в рабочий пользовательский Excel-шаблон.

Ключевое правило: Excel здесь является формой представления. Все инженерные
значения приходят из SystemCalculationResult; расчётные формулы v3
не дублируются в Excel.
"""
from __future__ import annotations

from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import range_boundaries

from app.config import AppSettings
from app.domain.formulas import FORMULA_VERSION
from app.domain.models import SystemCalculationResult, RecommendationResult
from app.infrastructure.export.excel_exporter import ExcelExporter


class CustomerExcelExporter(ExcelExporter):
    """Заполняет знакомую заказчику форму ``База``.

    Старый шаблон рассчитан на два слоя. Для 3+ слоёв форма расширяется
    программно: добавляются строки слоёв и строк разбавителей, стили/границы
    наследуются от исходных строк, итоговая строка переносится вниз.
    """

    _SECTION_1 = {"layer_start": 7, "thinner_start": 9, "total_row": 11}
    _SECTION_2 = {"layer_start": 21, "thinner_start": 23, "total_row": 25}

    def __init__(self, settings: Optional[AppSettings] = None):
        super().__init__(settings)

    @property
    def report_mode(self) -> str:
        mode = self.settings.report_mode
        return mode if mode in {"engineering", "commercial", "full"} else "engineering"

    @staticmethod
    def _binder(value) -> str:
        return value.value if hasattr(value, "value") else str(value or "")

    @staticmethod
    def _copy_row_style(ws, source_row: int, target_row: int, min_col: int = 2, max_col: int = 18) -> None:
        ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height
        ws.row_dimensions[target_row].hidden = ws.row_dimensions[source_row].hidden
        for col in range(min_col, max_col + 1):
            src = ws.cell(source_row, col)
            dst = ws.cell(target_row, col)
            if src.has_style:
                dst._style = copy(src._style)
            dst.number_format = src.number_format
            dst.protection = copy(src.protection)
            dst.alignment = copy(src.alignment)
            dst.font = copy(src.font)
            dst.fill = copy(src.fill)
            dst.border = copy(src.border)

    def _expand_section(self, ws, layer_start: int, thinner_start: int, total_row: int, layer_count: int) -> int:
        """Расширяет один 2-слойный блок до ``layer_count`` слоёв.

        Возвращает число добавленных строк в блоке (2 на каждый дополнительный
        слой: одна строка слоя + одна строка разбавителя).
        """
        extra = max(layer_count - 2, 0)
        if not extra:
            return 0

        original_merges = list(ws.merged_cells.ranges)
        for merged in original_merges:
            ws.unmerge_cells(str(merged))

        # Дополнительные строки слоёв вставляются перед строками разбавителей.
        ws.insert_rows(thinner_start, extra)
        shifted_total = total_row + extra
        # Дополнительные строки разбавителей вставляются перед итогом.
        ws.insert_rows(shifted_total, extra)

        # Восстанавливаем все исходные объединения с учётом обеих вставок.
        for merged in original_merges:
            min_col, min_row, max_col, max_row = range_boundaries(str(merged))
            for idx, amount in ((thinner_start, extra), (shifted_total, extra)):
                if min_row >= idx:
                    min_row += amount
                    max_row += amount
                elif max_row >= idx:
                    max_row += amount
            ws.merge_cells(start_row=min_row, start_column=min_col, end_row=max_row, end_column=max_col)

        # Новые строки наследуют оформление соседних строк шаблона.
        for row in range(layer_start + 2, layer_start + 2 + extra):
            self._copy_row_style(ws, layer_start + 1, row)
        new_thinner_start = thinner_start + extra
        for row in range(new_thinner_start + 2, new_thinner_start + 2 + extra):
            self._copy_row_style(ws, new_thinner_start + 1, row)

        return 2 * extra

    def _prepare_base_sheet(self, wb, layer_count: int):
        if "База" not in wb.sheetnames:
            return None, 0
        ws = wb["База"]
        if layer_count <= 2:
            return ws, 0

        extra = layer_count - 2
        # Верхний блок сдвигает весь нижний блок на 2*extra строк.
        self._expand_section(
            ws,
            self._SECTION_1["layer_start"],
            self._SECTION_1["thinner_start"],
            self._SECTION_1["total_row"],
            layer_count,
        )
        shift = 2 * extra
        self._expand_section(
            ws,
            self._SECTION_2["layer_start"] + shift,
            self._SECTION_2["thinner_start"] + shift,
            self._SECTION_2["total_row"] + shift,
            layer_count,
        )
        return ws, shift

    @staticmethod
    def _clear_row(ws, row: int) -> None:
        for col in range(2, 19):
            cell = ws.cell(row, col)
            if not isinstance(cell, MergedCell):
                cell.value = None

    @staticmethod
    def _layer_total_cost(layer) -> Optional[float]:
        if layer.cost_per_m2 is None and layer.thinner_cost_per_m2 is None:
            return None
        return (layer.cost_per_m2 or 0.0) + (layer.thinner_cost_per_m2 or 0.0)

    def _write_layer_row(self, ws, row: int, layer, area: float) -> None:
        material = layer.material
        values = [
            area,
            material.display_name(),
            self._binder(material.binder_type),
            material.ral or material.color or "-",
            material.density,
            material.solids_by_volume_percent,
            layer.wft,
            layer.target_dft,
            layer.theoretical_coverage,
            layer.losses_percent,
            layer.practical_coverage,
            material.price_per_kg if self.report_mode != "engineering" else None,
            material.price_per_liter if self.report_mode != "engineering" else None,
            layer.theoretical_consumption_l,
            layer.theoretical_consumption_kg,
            layer.practical_consumption_kg,
            self._layer_total_cost(layer),
        ]
        for col, value in enumerate(values, 2):
            ws.cell(row, col).value = value

    def _write_thinner_row(self, ws, row: int, layer) -> None:
        self._clear_row(ws, row)
        if layer.thinner is None and not layer.thinner_percent:
            return
        thinner = layer.thinner
        ws.cell(row, 2).value = f"Разбавитель для {layer.material.display_name()}"
        ws.cell(row, 6).value = thinner.density if thinner is not None else None
        ws.cell(row, 7).value = layer.thinner_percent
        ws.cell(row, 13).value = thinner.price_per_kg if self.report_mode != "engineering" and thinner else None
        ws.cell(row, 14).value = thinner.price_per_liter if self.report_mode != "engineering" and thinner else None
        ws.cell(row, 15).value = layer.thinner_consumption_l
        ws.cell(row, 16).value = layer.thinner_consumption_kg
        ws.cell(row, 17).value = layer.thinner_consumption_kg
        ws.cell(row, 18).value = layer.thinner_cost_per_m2

    def _write_totals(self, ws, row: int, result) -> None:
        self._clear_row(ws, row)
        ws.cell(row, 3).value = "Толщина покрытия (мкм)"
        ws.cell(row, 9).value = result.total_dft
        ws.cell(row, 10).value = "Общее количество ЛКМ"
        ws.cell(row, 15).value = result.total_theoretical_consumption_l
        ws.cell(row, 16).value = result.total_theoretical_consumption_kg
        ws.cell(row, 17).value = result.total_practical_consumption_kg
        ws.cell(row, 18).value = result.total_cost_per_m2

    def _write_block(self, ws, result, layer_start: int, thinner_start: int, total_row: int) -> None:
        area = max(float(result.object_data.area_m2 or 0.0), 0.0)
        for i, layer in enumerate(result.layers):
            layer_row = layer_start + i
            self._clear_row(ws, layer_row)
            self._write_layer_row(ws, layer_row, layer, area)

        for i, layer in enumerate(result.layers):
            self._write_thinner_row(ws, thinner_start + i, layer)

        self._write_totals(ws, total_row, result)

    def _write_metadata(self, ws, result, section2_header_row: int = 16) -> None:
        obj = result.object_data
        ws.cell(2, 2).value = f"Объект: {obj.object_name}" if obj.object_name else None
        ws.cell(2, 5).value = f"Заказчик: {obj.customer}" if obj.customer else None
        ws.cell(2, 13).value = f"Площадь: {float(obj.area_m2 or 0):.2f} м²" if obj.area_m2 else None
        ws.cell(section2_header_row, 2).value = f"Система АКЗ: {result.system.system_name or 'Пользовательская система'}"
        ws.cell(section2_header_row, 18).value = f"Дата: {datetime.now():%d.%m.%Y} | {FORMULA_VERSION}"

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
        layer_count = len(result.layers)
        ws, shift = self._prepare_base_sheet(wb, layer_count)
        if ws is None:
            return super().export_calculation(result, path, recommendation)

        extra = max(layer_count - 2, 0)
        self._write_block(ws, result, 7, 9 + extra, 11 + 2 * extra)
        self._write_block(ws, result, 21 + shift, 23 + shift + extra, 25 + 2 * shift)
        self._write_metadata(ws, result, section2_header_row=16 + shift)

        wb.save(path)
        return path
