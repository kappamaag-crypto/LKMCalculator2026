"""Инженерный Excel-экспорт систем покрытия без складских и закупочных данных."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.domain.models import ComparisonResult, SystemCalculationResult


class EngineeringExcelExporter:
    """Экспортирует техническое представление расчёта/сравнения систем."""

    def export_comparison(self, comparison: ComparisonResult, path: str | Path) -> Path:
        path = Path(path)
        wb = Workbook()
        ws = wb.active
        ws.title = "Сравнение систем"

        obj = comparison.object_data
        ws.append(["ИНЖЕНЕРНОЕ СРАВНЕНИЕ СИСТЕМ ПОКРЫТИЯ"])
        ws["A1"].font = Font(bold=True, size=14)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(2, len(comparison.systems) + 1))
        ws.append(["Объект", obj.object_name or ""])
        ws.append(["Заказчик", obj.customer or ""])
        ws.append(["Проект", obj.project or ""])
        ws.append(["Площадь, м²", obj.area_m2 if obj.area_m2 is not None else ""])
        ws.append([])

        systems = comparison.systems
        headers = ["Показатель"] + [s.system.system_name or f"Система {i + 1}" for i, s in enumerate(systems)]
        ws.append(headers)
        header_row = ws.max_row
        for cell in ws[header_row]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        rows = [
            ("Количество слоёв", [len(s.layers) for s in systems]),
            ("Общая толщина, мкм", [s.total_dft for s in systems]),
            ("Расход ЛКМ, кг/м²", [s.total_practical_consumption_kg for s in systems]),
            ("Расход ЛКМ, л/м²", [s.total_practical_consumption_l for s in systems]),
        ]
        for label, values in rows:
            ws.append([label] + ["" if v is None else v for v in values])

        ws.append([])
        ws.append(["СЛОИ СИСТЕМ"])
        ws[ws.max_row][0].font = Font(bold=True)

        max_layers = max((len(s.layers) for s in systems), default=0)
        ws.append(["Слой"] + [s.system.system_name or f"Система {i + 1}" for i, s in enumerate(systems)])
        layer_header = ws.max_row
        for cell in ws[layer_header]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        for index in range(max_layers):
            values = []
            for result in systems:
                if index < len(result.layers):
                    layer = result.layers[index]
                    values.append(f"{layer.material.display_name()} — {layer.target_dft:.0f} мкм")
                else:
                    values.append("")
            ws.append([f"Слой {index + 1}"] + values)

        ws.freeze_panes = "B8"
        for column in range(1, ws.max_column + 1):
            max_len = 0
            for row in ws.iter_rows(min_col=column, max_col=column):
                value = row[0].value
                if value is not None:
                    max_len = max(max_len, len(str(value)))
            ws.column_dimensions[get_column_letter(column)].width = min(max(max_len + 2, 14), 42)

        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ws.max_column)}{header_row + len(rows)}"
        wb.save(path)
        return path

    def export_system(self, result: SystemCalculationResult, path: str | Path) -> Path:
        comparison = ComparisonResult(object_data=result.object_data, systems=[result])
        return self.export_comparison(comparison, path)
