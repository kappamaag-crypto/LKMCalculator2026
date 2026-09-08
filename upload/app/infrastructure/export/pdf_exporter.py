"""PDF-отчёт инженерного расчёта ЛКМ / АКЗ v3."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config import AppSettings
from app.domain.models import SystemCalculationResult, ComparisonResult, RecommendationResult

BLUE = colors.HexColor("#1A56DB")
DARK = colors.HexColor("#1A1A2E")
GRAY = colors.HexColor("#6B7280")
LIGHT_GRAY = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#D0D4DC")


def _try_register_fonts() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if not Path(path).exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("AppFont", path))
            bold = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf").replace("Regular", "Bold")
            pdfmetrics.registerFont(TTFont("AppFont-Bold", bold if Path(bold).exists() else path))
            return "AppFont"
        except Exception:
            continue
    return "Helvetica"


class PDFExporter:
    """Экспорт расчёта без закупки, фасовки, остатков и складского учёта."""

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings()
        self.font = _try_register_fonts()
        self.font_bold = f"{self.font}-Bold" if self.font != "Helvetica" else "Helvetica-Bold"
        self.styles = self._build_styles()

    def _build_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="RuTitle", fontName=self.font_bold, fontSize=16, textColor=DARK, spaceAfter=6, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="RuHeading", fontName=self.font_bold, fontSize=12, textColor=BLUE, spaceBefore=12, spaceAfter=6))
        styles.add(ParagraphStyle(name="RuBody", fontName=self.font, fontSize=9, textColor=DARK, spaceAfter=3, leading=12, alignment=TA_JUSTIFY))
        styles.add(ParagraphStyle(name="RuSmall", fontName=self.font, fontSize=8, textColor=GRAY, spaceAfter=2, leading=10))
        styles.add(ParagraphStyle(name="RuCell", fontName=self.font, fontSize=8, textColor=DARK, leading=10))
        styles.add(ParagraphStyle(name="RuCellBold", fontName=self.font_bold, fontSize=8, textColor=DARK, leading=10))
        return styles

    def export_calculation(self, result: SystemCalculationResult, path: str | Path,
                           recommendation: Optional[RecommendationResult] = None,
                           comparison: Optional[ComparisonResult] = None) -> Path:
        path = Path(path)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                                topMargin=15 * mm, bottomMargin=15 * mm,
                                title="Расчёт ЛКМ / АКЗ", author=self.settings.organization_name)
        story = self._title(result)
        story += self._section_input(result)
        story += self._section_layers(result)
        story += self._section_totals(result)
        if comparison and len(comparison.systems) >= 2:
            story += self._section_comparison(comparison)
        if recommendation and recommendation.items:
            story += self._section_recommendations(recommendation)
        story += self._section_notes()
        doc.build(story)
        return path

    def _title(self, result):
        obj = result.object_data
        area = obj.area_m2 if obj.area_m2 > 0 else obj.area_per_element * obj.elements_count
        return [
            Paragraph("Расчёт расхода лакокрасочных материалов<br/>и подбор системы АКЗ", self.styles["RuTitle"]),
            HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=8),
            Paragraph(self.settings.organization_name or "Организация", self.styles["RuBody"]),
            Paragraph(f"Дата: {datetime.now():%d.%m.%Y %H:%M}", self.styles["RuSmall"]),
            Paragraph(f"<b>Объект:</b> {obj.object_name or '—'}", self.styles["RuBody"]),
            Paragraph(f"<b>Заказчик:</b> {obj.customer or '—'}", self.styles["RuBody"]),
            Paragraph(f"<b>Площадь:</b> {area:.2f} м²", self.styles["RuBody"]),
            Paragraph(f"<b>Система:</b> {result.system.system_name or 'Пользовательская'}", self.styles["RuBody"]),
            Spacer(1, 4 * mm),
        ]

    def _section_input(self, result):
        obj = result.object_data
        data = [
            ["Параметр", "Значение"],
            ["Категория коррозии", obj.corrosion_category.value if obj.corrosion_category else "—"],
            ["Долговечность", obj.durability.value if obj.durability else "—"],
            ["Поверхность", obj.surface_type.value if obj.surface_type else "—"],
            ["Среда", obj.environment.value if obj.environment else "—"],
            ["T мин / T макс, °C", f"{obj.temperature_min if obj.temperature_min is not None else '—'} / {obj.temperature_max if obj.temperature_max is not None else '—'}"],
            ["Влажность, %", str(obj.relative_humidity) if obj.relative_humidity is not None else "—"],
            ["Точка росы, °C", str(obj.dew_point) if obj.dew_point is not None else "—"],
        ]
        return [Paragraph("1. Исходные условия", self.styles["RuHeading"]), self._table(data, [75 * mm, 95 * mm]), Spacer(1, 3 * mm)]

    def _section_layers(self, result):
        data = [["№", "Материал", "DFT, мкм", "WFT, мкм", "Расход кг/м²", "Расход л/м²", "Стоимость руб/м²", "На объект, кг"]]
        for i, lr in enumerate(result.layers, 1):
            data.append([
                str(i), Paragraph(lr.material.material_name[:40], self.styles["RuCell"]),
                f"{lr.target_dft:.0f}", f"{lr.wft:.1f}", f"{lr.practical_consumption_kg:.3f}",
                f"{lr.practical_consumption_l:.3f}", f"{lr.cost_per_m2 + lr.thinner_cost_per_m2:.2f}",
                f"{lr.total_consumption_kg:.2f}",
            ])
        data.append(["", Paragraph("<b>ИТОГО</b>", self.styles["RuCellBold"]), f"{result.total_dft:.0f}", "",
                     f"{result.total_practical_consumption_kg:.3f}", f"{result.total_practical_consumption_l:.3f}",
                     f"{result.total_cost_per_m2:.2f}", f"{sum(x.total_consumption_kg for x in result.layers):.2f}"])
        return [Paragraph("2. Состав системы и расчёт слоёв", self.styles["RuHeading"]),
                self._table(data, [9*mm, 45*mm, 18*mm, 18*mm, 23*mm, 22*mm, 25*mm, 25*mm], highlight_last=True),
                Spacer(1, 3 * mm)]

    def _section_totals(self, result):
        data = [
            ["Показатель", "Значение"],
            ["Количество слоёв", str(len(result.layers))],
            ["Общая толщина DFT", f"{result.total_dft:.0f} мкм"],
            ["Практический расход", f"{result.total_practical_consumption_kg:.3f} кг/м²"],
            ["Практический расход", f"{result.total_practical_consumption_l:.3f} л/м²"],
            ["Стоимость материала + разбавителя", f"{result.total_cost_per_m2:.2f} руб/м²"],
            ["Стоимость выполнения объекта", f"{result.total_cost:,.2f} руб".replace(",", " ")],
            ["В том числе стоимость разбавителя", f"{result.total_thinner_cost:,.2f} руб".replace(",", " ")],
        ]
        return [Paragraph("3. Итоговые показатели", self.styles["RuHeading"]), self._table(data, [90*mm, 80*mm]), Spacer(1, 3 * mm)]

    def _section_comparison(self, comparison):
        systems = comparison.systems
        data = [["Показатель"] + [(s.system.system_name or f"Сис.{i+1}")[:18] for i, s in enumerate(systems)]]
        for label, values in [
            ("Слоёв", [str(len(s.layers)) for s in systems]),
            ("DFT, мкм", [f"{s.total_dft:.0f}" for s in systems]),
            ("кг/м²", [f"{s.total_practical_consumption_kg:.3f}" for s in systems]),
            ("л/м²", [f"{s.total_practical_consumption_l:.3f}" for s in systems]),
            ("руб/м²", [f"{s.total_cost_per_m2:.2f}" for s in systems]),
            ("Объект, руб", [f"{s.total_cost:,.0f}".replace(",", " ") for s in systems]),
        ]:
            data.append([label] + values)
        n = len(systems)
        return [Paragraph("4. Сравнение альтернативных систем", self.styles["RuHeading"]),
                self._table(data, [35*mm] + [(140/n)*mm]*n), Spacer(1, 3*mm)]

    def _section_recommendations(self, rec):
        data = [["Место", "Система", "Score", "Ключевые причины"]]
        for item in rec.items[:5]:
            data.append([str(item.rank), Paragraph(item.system.system_name[:35], self.styles["RuCell"]),
                         f"{item.score:.0f}", Paragraph("; ".join(item.reasons[:3])[:100] or "—", self.styles["RuCell"])])
        return [Paragraph("5. Рекомендации", self.styles["RuHeading"]), Paragraph(rec.message or "—", self.styles["RuBody"]),
                self._table(data, [15*mm, 50*mm, 15*mm, 90*mm]), Paragraph(rec.disclaimer or "", self.styles["RuSmall"]), Spacer(1, 3*mm)]

    def _section_notes(self):
        text = (
            "Расчёт предназначен для определения теоретического и практического расхода ЛКМ, "
            "разбавителя и стоимости покрытия. Количество упаковок, закупочная потребность, "
            "остатки и складские операции программой не рассчитываются. Подбор системы АКЗ "
            "является предварительным и должен быть подтверждён ТДС производителя, проектом "
            "и применимыми нормативными документами."
        )
        return [Paragraph("Примечания", self.styles["RuHeading"]), Paragraph(text, self.styles["RuBody"]),
                HRFlowable(width="100%", thickness=0.5, color=BORDER),
                Paragraph(f"Калькулятор ЛКМ / АКЗ v3.0 • {datetime.now():%d.%m.%Y %H:%M}", self.styles["RuSmall"])]

    def _table(self, data, col_widths=None, header=True, highlight_last=False):
        processed = []
        for i, row in enumerate(data):
            processed.append([c if isinstance(c, Paragraph) else Paragraph(str(c), self.styles["RuCellBold"] if header and i == 0 else self.styles["RuCell"]) for c in row])
        table = Table(processed, colWidths=col_widths, repeatRows=1 if header else 0)
        commands = [
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("GRID", (0,0), (-1,-1), 0.4, BORDER),
            ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ]
        if header:
            commands += [("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white)]
        if highlight_last and len(data) > 1:
            commands += [("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#DBEAFE"))]
        table.setStyle(TableStyle(commands))
        return table
