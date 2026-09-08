"""
Профессиональный PDF-отчёт расчёта ЛКМ / АКЗ (reportlab).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.domain.models import SystemCalculationResult, ComparisonResult, RecommendationResult, ObjectData
from app.config import AppSettings

# Цвета
BLUE = colors.HexColor("#1A56DB")
DARK = colors.HexColor("#1A1A2E")
GRAY = colors.HexColor("#6B7280")
LIGHT_GRAY = colors.HexColor("#F3F4F6")
GREEN = colors.HexColor("#D1FAE5")
BORDER = colors.HexColor("#D0D4DC")


def _try_register_fonts() -> str:
    """Попытка зарегистрировать шрифт с поддержкой кириллицы."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("AppFont", path))
                bold_path = path.replace("Regular", "Bold").replace(".ttf", "-Bold.ttf")
                if "DejaVuSans.ttf" in path:
                    bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                if Path(bold_path).exists():
                    pdfmetrics.registerFont(TTFont("AppFont-Bold", bold_path))
                else:
                    pdfmetrics.registerFont(TTFont("AppFont-Bold", path))
                return "AppFont"
            except Exception:
                continue
    return "Helvetica"


class PDFExporter:
    """Экспорт расчёта в PDF."""

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings()
        self.font = _try_register_fonts()
        self.font_bold = f"{self.font}-Bold" if self.font != "Helvetica" else "Helvetica-Bold"
        self.styles = self._build_styles()

    def _build_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="RuTitle", fontName=self.font_bold, fontSize=16,
            textColor=DARK, spaceAfter=6, alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name="RuHeading", fontName=self.font_bold, fontSize=12,
            textColor=BLUE, spaceBefore=12, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="RuBody", fontName=self.font, fontSize=9,
            textColor=DARK, spaceAfter=3, leading=12, alignment=TA_JUSTIFY,
        ))
        styles.add(ParagraphStyle(
            name="RuSmall", fontName=self.font, fontSize=8,
            textColor=GRAY, spaceAfter=2, leading=10,
        ))
        styles.add(ParagraphStyle(
            name="RuDisclaimer", fontName=self.font, fontSize=8,
            textColor=colors.HexColor("#92400E"), spaceBefore=8, spaceAfter=4,
            leading=11, backColor=colors.HexColor("#FEF3C7"),
            borderPadding=6,
        ))
        styles.add(ParagraphStyle(
            name="RuCell", fontName=self.font, fontSize=8,
            textColor=DARK, leading=10,
        ))
        styles.add(ParagraphStyle(
            name="RuCellBold", fontName=self.font_bold, fontSize=8,
            textColor=DARK, leading=10,
        ))
        return styles

    def export_calculation(
        self,
        result: SystemCalculationResult,
        path: str | Path,
        recommendation: Optional[RecommendationResult] = None,
        comparison: Optional[ComparisonResult] = None,
    ) -> Path:
        path = Path(path)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title="Расчёт ЛКМ / АКЗ",
            author=self.settings.organization_name,
        )
        story = []
        story.extend(self._title_page(result))
        story.append(Spacer(1, 6 * mm))
        story.extend(self._section_input(result))
        story.append(Spacer(1, 4 * mm))
        story.extend(self._section_layers(result))
        story.append(Spacer(1, 4 * mm))
        story.extend(self._section_totals(result))
        if comparison and len(comparison.systems) >= 2:
            story.append(Spacer(1, 4 * mm))
            story.extend(self._section_comparison(comparison))
        if recommendation and recommendation.items:
            story.append(Spacer(1, 4 * mm))
            story.extend(self._section_recommendations(recommendation))
        story.append(Spacer(1, 6 * mm))
        story.extend(self._section_notes())
        doc.build(story)
        return path

    # ------------------------------------------------------------------
    def _title_page(self, result: SystemCalculationResult) -> list:
        obj = result.object_data
        elements = []
        elements.append(Paragraph(
            "Расчёт расхода лакокрасочных материалов<br/>и подбор системы АКЗ",
            self.styles["RuTitle"],
        ))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=8))
        org = self.settings.organization_name or "Организация"
        elements.append(Paragraph(org, self.styles["RuBody"]))
        elements.append(Paragraph(
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            self.styles["RuSmall"],
        ))
        if obj.calculation_number:
            elements.append(Paragraph(f"№ расчёта: {obj.calculation_number}", self.styles["RuSmall"]))
        if obj.object_name:
            elements.append(Paragraph(f"<b>Объект:</b> {obj.object_name}", self.styles["RuBody"]))
        if obj.customer:
            elements.append(Paragraph(f"<b>Заказчик:</b> {obj.customer}", self.styles["RuBody"]))
        area = obj.area_m2
        if area <= 0 and obj.area_per_element > 0:
            area = obj.area_per_element * obj.elements_count
        elements.append(Paragraph(f"<b>Площадь:</b> {area:.2f} м²", self.styles["RuBody"]))
        elements.append(Paragraph(
            f"<b>Система:</b> {result.system.system_name or 'Пользовательская'}",
            self.styles["RuBody"],
        ))
        return elements

    def _section_input(self, result: SystemCalculationResult) -> list:
        obj = result.object_data
        elements = [Paragraph("1. Условия эксплуатации", self.styles["RuHeading"])]
        data = [
            ["Параметр", "Значение"],
            ["Категория коррозии", obj.corrosion_category.value if obj.corrosion_category else "—"],
            ["Долговечность", obj.durability.value if obj.durability else "—"],
            ["Поверхность", obj.surface_type.value if obj.surface_type else "—"],
            ["Среда", obj.environment.value if obj.environment else "—"],
            ["T мин / T макс, °C", f"{obj.temperature_min or '—'} / {obj.temperature_max or '—'}"],
        ]
        elements.append(self._table(data, col_widths=[70 * mm, 100 * mm]))
        return elements

    def _section_layers(self, result: SystemCalculationResult) -> list:
        elements = [Paragraph("2. Состав системы и расчёт слоёв", self.styles["RuHeading"])]
        header = ["№", "Материал", "DFT\nмкм", "WFT\nмкм", "Расход\nкг/м²", "Стоим.\nруб/м²", "На объект\nкг"]
        data = [header]
        for i, lr in enumerate(result.layers):
            data.append([
                str(i + 1),
                Paragraph(lr.material.material_name[:40], self.styles["RuCell"]),
                f"{lr.target_dft:.0f}",
                f"{lr.wft:.1f}",
                f"{lr.practical_consumption_kg:.3f}",
                f"{lr.cost_per_m2:.2f}",
                f"{lr.total_consumption_kg:.1f}",
            ])
        data.append([
            "", Paragraph("<b>ИТОГО</b>", self.styles["RuCellBold"]),
            f"{result.total_dft:.0f}", "",
            f"{result.total_practical_consumption_kg:.3f}",
            f"{result.total_cost_per_m2:.2f}",
            f"{sum(lr.total_consumption_kg for lr in result.layers):.1f}",
        ])
        elements.append(self._table(
            data,
            col_widths=[10*mm, 55*mm, 18*mm, 18*mm, 22*mm, 22*mm, 25*mm],
            header=True,
            highlight_last=True,
        ))
        return elements

    def _section_totals(self, result: SystemCalculationResult) -> list:
        elements = [Paragraph("3. Итоговые показатели", self.styles["RuHeading"])]
        data = [
            ["Показатель", "Значение"],
            ["Количество слоёв", str(len(result.layers))],
            ["Общая толщина DFT", f"{result.total_dft:.0f} мкм"],
            ["Расход практический", f"{result.total_practical_consumption_kg:.3f} кг/м²"],
            ["Расход практический", f"{result.total_practical_consumption_l:.3f} л/м²"],
            ["Стоимость материала", f"{result.total_cost_per_m2:.2f} руб/м²"],
            ["Стоимость объекта", f"{result.total_cost:,.2f} руб".replace(",", " ")],
            ["Стоимость закупки (с фасовкой)", f"{result.total_purchase_cost:,.2f} руб".replace(",", " ")],
        ]
        elements.append(self._table(data, col_widths=[90 * mm, 80 * mm]))
        return elements

    def _section_comparison(self, comparison: ComparisonResult) -> list:
        elements = [Paragraph("4. Сравнение альтернативных систем", self.styles["RuHeading"])]
        systems = comparison.systems
        header = ["Показатель"] + [(s.system.system_name or f"Сис.{i+1}")[:18] for i, s in enumerate(systems)]
        data = [header]
        rows = [
            ("Слоёв", [str(len(s.layers)) for s in systems]),
            ("DFT, мкм", [f"{s.total_dft:.0f}" for s in systems]),
            ("кг/м²", [f"{s.total_practical_consumption_kg:.3f}" for s in systems]),
            ("руб/м²", [f"{s.total_cost_per_m2:.1f}" for s in systems]),
            ("Объект, руб", [f"{s.total_cost:,.0f}".replace(",", " ") for s in systems]),
        ]
        for label, vals in rows:
            data.append([label] + vals)
        n = len(systems)
        col_w = [35 * mm] + [(140 / n) * mm] * n
        elements.append(self._table(data, col_widths=col_w, header=True))
        if comparison.cheapest_index is not None:
            name = systems[comparison.cheapest_index].system.system_name
            elements.append(Paragraph(f"Самая дешёвая: {name}", self.styles["RuSmall"]))
        if comparison.best_balance_index is not None:
            name = systems[comparison.best_balance_index].system.system_name
            elements.append(Paragraph(f"Лучший баланс цена/защита: {name}", self.styles["RuSmall"]))
        return elements

    def _section_recommendations(self, rec: RecommendationResult) -> list:
        elements = [Paragraph("5. Рекомендации", self.styles["RuHeading"])]
        elements.append(Paragraph(rec.message, self.styles["RuBody"]))
        header = ["Место", "Система", "Score", "Ключевые причины"]
        data = [header]
        for item in rec.items[:5]:
            reasons = "; ".join(item.reasons[:3]) if item.reasons else "—"
            data.append([
                str(item.rank),
                Paragraph(item.system.system_name[:35], self.styles["RuCell"]),
                f"{item.score:.0f}",
                Paragraph(reasons[:80], self.styles["RuCell"]),
            ])
        elements.append(self._table(
            data, col_widths=[15*mm, 50*mm, 15*mm, 90*mm], header=True,
        ))
        elements.append(Paragraph(rec.disclaimer, self.styles["RuDisclaimer"]))
        return elements

    def _section_notes(self) -> list:
        elements = [Paragraph("Ограничения и примечания", self.styles["RuHeading"])]
        notes = (
            "1. Расчёт выполнен по формулам теоретического и практического расхода ЛКМ. "
            "Коэффициент потерь: K = 100 / (100 − потери%).<br/>"
            "2. <b>Предварительный подбор системы АКЗ.</b> Окончательный выбор необходимо "
            "подтвердить технической документацией производителя, проектными требованиями "
            "и применимыми нормативными документами.<br/>"
            "3. Цены указаны согласно данным в базе на момент расчёта. "
            "НДС учитывается в соответствии с настройками.<br/>"
            "4. Программа не заменяет проектные решения и экспертизу ответственного специалиста."
        )
        elements.append(Paragraph(notes, self.styles["RuBody"]))
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        elements.append(Paragraph(
            f"Сформировано: Калькулятор ЛКМ / АКЗ • {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            self.styles["RuSmall"],
        ))
        return elements

    def _table(
        self,
        data: list,
        col_widths=None,
        header: bool = True,
        highlight_last: bool = False,
    ) -> Table:
        # Convert plain strings in header
        processed = []
        for i, row in enumerate(data):
            processed.append([
                Paragraph(str(c), self.styles["RuCellBold"] if (header and i == 0) else self.styles["RuCell"])
                if not isinstance(c, Paragraph) else c
                for c in row
            ])
        t = Table(processed, colWidths=col_widths, repeatRows=1 if header else 0)
        style_cmds = [
            ("FONTNAME", (0, 0), (-1, -1), self.font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        if header:
            style_cmds += [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), self.font_bold),
            ]
            if len(data) > 2:
                for r in range(2, len(data), 2):
                    if not (highlight_last and r == len(data) - 1):
                        style_cmds.append(("BACKGROUND", (0, r), (-1, r), LIGHT_GRAY))
        if highlight_last and len(data) > 1:
            style_cmds.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")))
            style_cmds.append(("FONTNAME", (0, -1), (-1, -1), self.font_bold))
        t.setStyle(TableStyle(style_cmds))
        return t