"""
Профессиональный экспорт расчёта / сравнения в Excel (openpyxl).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.models import (
    SystemCalculationResult,
    ComparisonResult,
    ObjectData,
    RecommendationResult,
)
from app.config import AppSettings


# Стили
HEADER_FONT = Font(name="Arial", bold=True, size=12, color="FFFFFF")
TITLE_FONT = Font(name="Arial", bold=True, size=16, color="1A1A2E")
SUBTITLE_FONT = Font(name="Arial", bold=True, size=11, color="374151")
NORMAL_FONT = Font(name="Arial", size=10)
BOLD_FONT = Font(name="Arial", bold=True, size=10)
THIN = Border(
    left=Side(style="thin", color="D0D4DC"),
    right=Side(style="thin", color="D0D4DC"),
    top=Side(style="thin", color="D0D4DC"),
    bottom=Side(style="thin", color="D0D4DC"),
)
HEADER_FILL = PatternFill("solid", fgColor="1A56DB")
ALT_FILL = PatternFill("solid", fgColor="F3F4F6")
GREEN_FILL = PatternFill("solid", fgColor="D1FAE5")
YELLOW_FILL = PatternFill("solid", fgColor="FEF3C7")
TOTAL_FILL = PatternFill("solid", fgColor="DBEAFE")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _auto_width(ws: Worksheet, min_width: int = 10, max_width: int = 40) -> None:
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        length = max((len(str(c.value or "")) for c in col), default=min_width)
        ws.column_dimensions[letter].width = min(max(length + 2, min_width), max_width)


def _write_header_row(ws: Worksheet, row: int, headers: list[str]) -> None:
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = THIN


def _cell(ws: Worksheet, row: int, col: int, value, bold: bool = False, fill=None, align=CENTER):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = BOLD_FONT if bold else NORMAL_FONT
    cell.alignment = align
    cell.border = THIN
    if fill:
        cell.fill = fill
    return cell


class ExcelExporter:
    """Экспорт в многолистовый Excel-файл."""

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings()

    def export_calculation(
        self,
        result: SystemCalculationResult,
        path: str | Path,
        recommendation: Optional[RecommendationResult] = None,
    ) -> Path:
        """Экспорт одного расчёта."""
        path = Path(path)
        wb = Workbook()

        self._sheet_input(wb.active, result)
        self._sheet_layers(wb.create_sheet("Слои"), result)
        self._sheet_materials(wb.create_sheet("Материалы"), result)
        self._sheet_summary(wb.create_sheet("Итоги"), result)

        if recommendation and recommendation.items:
            self._sheet_recommendations(wb.create_sheet("Рекомендации"), recommendation)

        wb.save(path)
        return path

    def export_comparison(
        self,
        comparison: ComparisonResult,
        path: str | Path,
    ) -> Path:
        """Экспорт сравнения систем."""
        path = Path(path)
        wb = Workbook()

        ws = wb.active
        ws.title = "Сравнение"
        self._sheet_comparison(ws, comparison)

        # Отдельный лист по каждой системе
        for i, sys_result in enumerate(comparison.systems):
            name = (sys_result.system.system_name or f"Система {i+1}")[:28]
            self._sheet_layers(wb.create_sheet(name), sys_result)

        wb.save(path)
        return path

    # ------------------------------------------------------------------
    def _title_block(self, ws: Worksheet, title: str, obj: ObjectData, start_row: int = 1) -> int:
        ws.cell(row=start_row, column=1, value=title).font = TITLE_FONT
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)

        row = start_row + 1
        ws.cell(row=row, column=1, value=self.settings.organization_name).font = SUBTITLE_FONT
        row += 1
        ws.cell(row=row, column=1, value=f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}").font = NORMAL_FONT
        row += 1
        if obj.calculation_number:
            ws.cell(row=row, column=1, value=f"№ расчёта: {obj.calculation_number}").font = NORMAL_FONT
            row += 1
        if obj.object_name:
            ws.cell(row=row, column=1, value=f"Объект: {obj.object_name}").font = NORMAL_FONT
            row += 1
        if obj.customer:
            ws.cell(row=row, column=1, value=f"Заказчик: {obj.customer}").font = NORMAL_FONT
            row += 1
        area = obj.area_m2
        if area <= 0 and obj.area_per_element > 0:
            area = obj.area_per_element * obj.elements_count
        ws.cell(row=row, column=1, value=f"Площадь: {area:.2f} м²").font = NORMAL_FONT
        row += 2
        return row

    def _sheet_input(self, ws: Worksheet, result: SystemCalculationResult) -> None:
        ws.title = "Исходные данные"
        obj = result.object_data
        row = self._title_block(ws, "Расчёт расхода ЛКМ / подбор системы АКЗ", obj)

        ws.cell(row=row, column=1, value="Условия эксплуатации").font = SUBTITLE_FONT
        row += 1
        fields = [
            ("Категория коррозии", obj.corrosion_category.value if obj.corrosion_category else "—"),
            ("Долговечность", obj.durability.value if obj.durability else "—"),
            ("Поверхность", obj.surface_type.value if obj.surface_type else "—"),
            ("Среда", obj.environment.value if obj.environment else "—"),
            ("T мин, °C", obj.temperature_min if obj.temperature_min is not None else "—"),
            ("T макс, °C", obj.temperature_max if obj.temperature_max is not None else "—"),
            ("Система", result.system.system_name or "Пользовательская"),
        ]
        for label, val in fields:
            _cell(ws, row, 1, label, bold=True, align=LEFT)
            _cell(ws, row, 2, val, align=LEFT)
            row += 1

        row += 1
        ws.cell(row=row, column=1, value="Примечание:").font = BOLD_FONT
        row += 1
        ws.cell(
            row=row, column=1,
            value="Предварительный расчёт. Окончательный выбор системы — по TDS производителя и проектным требованиям."
        ).font = NORMAL_FONT
        _auto_width(ws)

    def _sheet_layers(self, ws: Worksheet, result: SystemCalculationResult) -> None:
        if ws.title == "Sheet":
            ws.title = "Слои"
        row = 1
        ws.cell(row=row, column=1, value=f"Слои системы: {result.system.system_name}").font = TITLE_FONT
        row += 2

        headers = [
            "№", "Материал", "Связующее", "DFT, мкм", "WFT, мкм",
            "Потери, %", "Разб., %",
            "Укрыв. теор., м²/л", "Укрыв. практ., м²/л",
            "Расход теор., кг/м²", "Расход практ., кг/м²",
            "Расход практ., л/м²",
            "Стоимость, руб/м²",
            "Кол-во на объект, кг", "Стоимость на объект, руб",
            "Упаковок", "Закупка, кг",
        ]
        _write_header_row(ws, row, headers)
        row += 1

        for i, lr in enumerate(result.layers):
            fill = ALT_FILL if i % 2 else None
            binder = lr.material.binder_type.value if hasattr(lr.material.binder_type, "value") else str(lr.material.binder_type)
            values = [
                i + 1,
                lr.material.material_name,
                binder,
                lr.target_dft,
                lr.wft,
                lr.losses_percent,
                lr.thinner_percent,
                lr.theoretical_coverage,
                lr.practical_coverage,
                lr.theoretical_consumption_kg,
                lr.practical_consumption_kg,
                lr.practical_consumption_l,
                lr.cost_per_m2,
                lr.total_consumption_kg,
                lr.total_cost,
                lr.packages_count or "",
                lr.purchase_kg or "",
            ]
            for col, v in enumerate(values, 1):
                _cell(ws, row, col, v, fill=fill)
            row += 1

        # Итого
        _cell(ws, row, 1, "", bold=True, fill=TOTAL_FILL)
        _cell(ws, row, 2, "ИТОГО", bold=True, fill=TOTAL_FILL, align=LEFT)
        _cell(ws, row, 4, result.total_dft, bold=True, fill=TOTAL_FILL)
        _cell(ws, row, 11, result.total_practical_consumption_kg, bold=True, fill=TOTAL_FILL)
        _cell(ws, row, 12, result.total_practical_consumption_l, bold=True, fill=TOTAL_FILL)
        _cell(ws, row, 13, result.total_cost_per_m2, bold=True, fill=TOTAL_FILL)
        _cell(ws, row, 15, result.total_cost, bold=True, fill=TOTAL_FILL)

        ws.freeze_panes = "A4"
        _auto_width(ws, min_width=8, max_width=28)

    def _sheet_materials(self, ws: Worksheet, result: SystemCalculationResult) -> None:
        row = 1
        ws.cell(row=row, column=1, value="Спецификация материалов").font = TITLE_FONT
        row += 2
        headers = [
            "Материал", "Производитель", "Плотность, кг/л", "Сухой остаток, %",
            "Цена, руб/кг", "Фасовка, кг", "Кол-во, кг", "Упаковок", "Закупка, кг", "Стоимость, руб",
        ]
        _write_header_row(ws, row, headers)
        row += 1

        for i, lr in enumerate(result.layers):
            fill = ALT_FILL if i % 2 else None
            price = lr.material.price_per_kg or 0
            purchase_cost = (lr.purchase_kg or lr.total_consumption_kg) * price
            values = [
                lr.material.material_name,
                lr.material.manufacturer or "—",
                lr.material.density,
                lr.material.solids_percent,
                price,
                lr.material.packaging_kg or "—",
                lr.total_consumption_kg,
                lr.packages_count or "—",
                lr.purchase_kg or lr.total_consumption_kg,
                round(purchase_cost, 2),
            ]
            for col, v in enumerate(values, 1):
                _cell(ws, row, col, v, fill=fill)
            row += 1

        _auto_width(ws)

    def _sheet_summary(self, ws: Worksheet, result: SystemCalculationResult) -> None:
        row = self._title_block(ws, "Итоговый расчёт", result.object_data)
        ws.cell(row=row, column=1, value="Сводка").font = SUBTITLE_FONT
        row += 1

        items = [
            ("Система", result.system.system_name or "Пользовательская"),
            ("Количество слоёв", len(result.layers)),
            ("Общая толщина DFT, мкм", result.total_dft),
            ("Расход теоретический, кг/м²", result.total_theoretical_consumption_kg),
            ("Расход практический, кг/м²", result.total_practical_consumption_kg),
            ("Расход практический, л/м²", result.total_practical_consumption_l),
            ("Стоимость материала, руб/м²", result.total_cost_per_m2),
            ("Стоимость объекта, руб", result.total_cost),
            ("Стоимость закупки (с фасовкой), руб", result.total_purchase_cost),
        ]
        for label, val in items:
            _cell(ws, row, 1, label, bold=True, align=LEFT, fill=ALT_FILL)
            _cell(ws, row, 2, val, align=LEFT)
            row += 1

        row += 2
        ws.cell(row=row, column=1, value="Ограничения и примечания").font = SUBTITLE_FONT
        row += 1
        ws.cell(
            row=row, column=1,
            value=(
                "1. Расчёт выполнен по формулам теоретического/практического расхода ЛКМ.\n"
                "2. Коэффициент потерь: K = 100 / (100 − потери%).\n"
                "3. Предварительный подбор. Окончательный выбор системы — по технической "
                "документации производителя, проектным требованиям и нормативным документам.\n"
                "4. Цены указаны согласно данным в базе на момент расчёта."
            )
        ).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=1, end_row=row + 4, end_column=4)
        _auto_width(ws)

    def _sheet_comparison(self, ws: Worksheet, comparison: ComparisonResult) -> None:
        row = self._title_block(ws, "Сравнение систем покрытия", comparison.object_data)
        systems = comparison.systems
        n = len(systems)

        headers = ["Показатель"] + [
            (s.system.system_name or f"Система {i+1}")[:25] for i, s in enumerate(systems)
        ]
        _write_header_row(ws, row, headers)
        row += 1

        rows_data = [
            ("Количество слоёв", [len(s.layers) for s in systems]),
            ("Общая толщина, мкм", [s.total_dft for s in systems]),
            ("Расход, кг/м²", [s.total_practical_consumption_kg for s in systems]),
            ("Расход, л/м²", [s.total_practical_consumption_l for s in systems]),
            ("Стоимость, руб/м²", [s.total_cost_per_m2 for s in systems]),
            ("Стоимость объекта, руб", [s.total_cost for s in systems]),
        ]

        for label, values in rows_data:
            _cell(ws, row, 1, label, bold=True, align=LEFT)
            min_v = min(values) if values else 0
            for c, v in enumerate(values):
                fill = GREEN_FILL if v == min_v and label.startswith(("Стоимость", "Расход", "Количество")) else None
                _cell(ws, row, c + 2, v, fill=fill)
            row += 1

        row += 2
        if comparison.cheapest_index is not None:
            name = systems[comparison.cheapest_index].system.system_name
            ws.cell(row=row, column=1, value=f"Самая дешёвая: {name}").font = BOLD_FONT
            row += 1
        if comparison.best_balance_index is not None:
            name = systems[comparison.best_balance_index].system.system_name
            ws.cell(row=row, column=1, value=f"Лучший баланс цена/защита: {name}").font = BOLD_FONT

        _auto_width(ws)

    def _sheet_recommendations(self, ws: Worksheet, rec: RecommendationResult) -> None:
        row = 1
        ws.cell(row=row, column=1, value="Рекомендации по системам АКЗ").font = TITLE_FONT
        row += 2
        ws.cell(row=row, column=1, value=rec.message).font = NORMAL_FONT
        row += 2

        headers = ["Место", "Система", "Score", "Причины", "Предупреждения"]
        _write_header_row(ws, row, headers)
        row += 1

        for item in rec.items:
            values = [
                item.rank,
                item.system.system_name,
                item.score,
                "; ".join(item.reasons[:5]),
                "; ".join(item.warnings[:3]) if item.warnings else "—",
            ]
            for col, v in enumerate(values, 1):
                fill = GREEN_FILL if item.rank == 1 else None
                _cell(ws, row, col, v, fill=fill, align=LEFT if col > 2 else CENTER)
            row += 1

        row += 2
        ws.cell(row=row, column=1, value=rec.disclaimer).font = Font(name="Arial", size=9, italic=True, color="92400E")
        ws.merge_cells(start_row=row, start_column=1, end_row=row + 2, end_column=5)
        _auto_width(ws, max_width=50)