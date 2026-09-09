"""PDF-отчёт инженерного расчёта ЛКМ / АКЗ v3."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config import AppSettings
from app.domain.models import SystemCalculationResult, ComparisonResult, RecommendationResult
from app.domain.formulas import FORMULA_VERSION

BLUE = colors.HexColor("#1A56DB")
DARK = colors.HexColor("#1A1A2E")
GRAY = colors.HexColor("#6B7280")
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


def _area(result: SystemCalculationResult) -> float:
    return max(float(result.object_data.area_m2 or 0.0), 0.0)


def _cost(value: Optional[float], digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _total_cost(material_cost: Optional[float], thinner_cost: Optional[float]) -> Optional[float]:
    if material_cost is None or thinner_cost is None:
        return None
    return material_cost + thinner_cost


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
        styles.add(ParagraphStyle(name="RuHeading", fontName=self.font_bold, fontSize=12, textColor=BLUE, spaceBefore=12, spaceAfter=6, alignment=TA_LEFT))
        styles.add(ParagraphStyle(name="RuBody", fontName=self.font, fontSize=9, textColor=DARK, spaceAfter=3, leading=12, alignment=TA_LEFT))
        styles.add(ParagraphStyle(name="RuSmall", fontName=self.font, fontSize=8, textColor=GRAY, spaceAfter=2, leading=10, alignment=TA_LEFT))
        styles.add(ParagraphStyle(name="RuCell", fontName=self.font, fontSize=8, textColor=DARK, leading=10, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="RuCellLeft", fontName=self.font, fontSize=8, textColor=DARK, leading=10, alignment=TA_LEFT))
        styles.add(ParagraphStyle(name="RuCellBold", fontName=self.font_bold, fontSize=8, textColor=DARK, leading=10, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="RuCellBoldLeft", fontName=self.font_bold, fontSize=8, textColor=DARK, leading=10, alignment=TA_LEFT))
        styles.add(ParagraphStyle(name="RuHeader", fontName=self.font_bold, fontSize=7.5, textColor=colors.white, leading=9, alignment=TA_CENTER))
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
        area = _area(result)
        return [
            Paragraph("Расчёт расхода лакокрасочных материалов<br/>и подбор системы АКЗ", self.styles["RuTitle"]),
            HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=8),
            Paragraph(self.settings.organization_name or "Организация", self.styles["RuBody"]),
            Paragraph(f"Дата расчёта: {datetime.now():%d.%m.%Y %H:%M}", self.styles["RuSmall"]),
            Paragraph(f"Версия формул: {FORMULA_VERSION}", self.styles["RuSmall"]),
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
        ]
        return [Paragraph("1. Исходные параметры", self.styles["RuHeading"]), self._table(data, [75 * mm, 95 * mm], alignments=["LEFT", "LEFT"]), Spacer(1, 3 * mm)]

    def _section_layers(self, result):
        data = [["№", "Материал", "DFT", "WFT", "Теор. кг/м²", "Практ. кг/м²", "Теор. л/м²", "Практ. л/м²", "Стоимость, руб/м²"]]
        for i, lr in enumerate(result.layers, 1):
            total_cost = _total_cost(lr.cost_per_m2, lr.thinner_cost_per_m2)
            material_name = lr.material.display_name() if hasattr(lr.material, "display_name") else lr.material.material_name
            data.append([
                str(i), Paragraph(material_name, self.styles["RuCellLeft"]),
                f"{lr.target_dft:.0f}", f"{lr.wft:.1f}",
                f"{lr.theoretical_consumption_kg:.3f}", f"{lr.practical_consumption_kg:.3f}",
                f"{lr.theoretical_consumption_l:.3f}", f"{lr.practical_consumption_l:.3f}", _cost(total_cost),
            ])
        thinner_kg_m2 = sum(lr.thinner_consumption_kg for lr in result.layers)
        thinner_l_m2 = sum(lr.thinner_consumption_l for lr in result.layers)
        data.append(["", Paragraph("ИТОГО", self.styles["RuCellBoldLeft"]), f"{result.total_dft:.0f}", "",
                     f"{result.total_theoretical_consumption_kg:.3f}", f"{result.total_practical_consumption_kg:.3f}",
                     f"{result.total_theoretical_consumption_l:.3f}", f"{result.total_practical_consumption_l:.3f}", _cost(result.total_cost_per_m2)])
        return [Paragraph("2. Состав системы и расчёт слоёв", self.styles["RuHeading"]),
                self._table(data, [7*mm, 45*mm, 15*mm, 15*mm, 19*mm, 19*mm, 19*mm, 19*mm, 22*mm], highlight_last=True,
                            alignments=["CENTER", "LEFT", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER"]),
                Spacer(1, 3 * mm)]

    def _section_totals(self, result):
        area = _area(result)
        thinner_l_m2 = sum(lr.thinner_consumption_l for lr in result.layers)
        thinner_kg_m2 = sum(lr.thinner_consumption_kg for lr in result.layers)
        theoretical_kg_m2 = result.total_theoretical_consumption_kg
        theoretical_l_m2 = result.total_theoretical_consumption_l
        data = [
            ["Показатель", "Значение"],
            ["Количество слоёв", str(len(result.layers))],
            ["Общая толщина DFT", f"{result.total_dft:.0f} мкм"],
            ["Теоретический расход ЛКМ", f"{theoretical_kg_m2:.3f} кг/м²"],
            ["Теоретический расход ЛКМ", f"{theoretical_l_m2:.3f} л/м²"],
            ["Теоретический расход ЛКМ на объект", f"{theoretical_kg_m2 * area:.2f} кг ({theoretical_l_m2 * area:.2f} л)"],
            ["Практический расход ЛКМ", f"{result.total_practical_consumption_kg:.3f} кг/м²"],
            ["Практический расход ЛКМ", f"{result.total_practical_consumption_l:.3f} л/м²"],
            ["Практический расход ЛКМ на объект", f"{result.total_practical_consumption_kg * area:.2f} кг ({result.total_practical_consumption_l * area:.2f} л)"],
            ["Расход разбавителя", f"{thinner_kg_m2:.3f} кг/м² ({thinner_l_m2:.3f} л/м²)"],
            ["Разбавитель на объект", f"{thinner_kg_m2 * area:.2f} кг ({thinner_l_m2 * area:.2f} л)"],
            ["Стоимость материала + разбавителя", f"{_cost(result.total_cost_per_m2)} руб/м²" if result.total_cost_per_m2 is not None else "—"],
            ["Стоимость объекта", f"{result.total_cost:,.2f} руб".replace(",", " ") if result.total_cost is not None else "—"],
            ["В том числе стоимость разбавителя", f"{result.total_thinner_cost:,.2f} руб".replace(",", " ") if result.total_thinner_cost is not None else "—"],
        ]
        return [Paragraph("3. Итоговые показатели", self.styles["RuHeading"]), self._table(data, [90*mm, 80*mm], alignments=["LEFT", "CENTER"]), Spacer(1, 3*mm)]

    def _section_comparison(self, comparison):
        systems = comparison.systems
        data = [["Показатель"] + [(s.system.system_name or f"Сис.{i+1}") for i, s in enumerate(systems)]]
        for label, values in [
            ("Слоёв", [str(len(s.layers)) for s in systems]),
            ("DFT, мкм", [f"{s.total_dft:.0f}" for s in systems]),
            ("Теор. кг/м²", [f"{s.total_theoretical_consumption_kg:.3f}" for s in systems]),
            ("Практ. кг/м²", [f"{s.total_practical_consumption_kg:.3f}" for s in systems]),
            ("Теор. л/м²", [f"{s.total_theoretical_consumption_l:.3f}" for s in systems]),
            ("Практ. л/м²", [f"{s.total_practical_consumption_l:.3f}" for s in systems]),
            ("руб/м²", [_cost(s.total_cost_per_m2) for s in systems]),
            ("Объект, руб", [f"{s.total_cost:,.0f}".replace(",", " ") if s.total_cost is not None else "—" for s in systems]),
        ]:
            data.append([label] + values)
        n = len(systems)
        return [Paragraph("4. Сравнение альтернативных систем", self.styles["RuHeading"]),
                self._table(data, [35*mm] + [(140/n)*mm]*n, alignments=["LEFT"] + ["CENTER"]*n), Spacer(1, 3*mm)]

    def _section_recommendations(self, rec):
        data = [["Место", "Система", "Score", "Ключевые причины"]]
        for item in rec.items[:5]:
            system_name = item.system.system_name or "—"
            data.append([str(item.rank), Paragraph(system_name, self.styles["RuCellLeft"]),
                         f"{item.score:.0f}", Paragraph("; ".join(item.reasons[:3])[:100] or "—", self.styles["RuCellLeft"])])
        return [Paragraph("5. Рекомендации", self.styles["RuHeading"]), Paragraph(rec.message or "—", self.styles["RuBody"]),
                self._table(data, [15*mm, 50*mm, 15*mm, 90*mm], alignments=["CENTER", "LEFT", "CENTER", "LEFT"]), Paragraph(rec.disclaimer or "", self.styles["RuSmall"]), Spacer(1, 3*mm)]

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
                Paragraph(f"Калькулятор ЛКМ / АКЗ v3.0 • Формулы {FORMULA_VERSION} • {datetime.now():%d.%m.%Y %H:%M}", self.styles["RuSmall"])]

    def _table(self, data, col_widths=None, header=True, highlight_last=False, alignments=None):
        processed = []
        for i, row in enumerate(data):
            converted = []
            for c in row:
                if isinstance(c, Paragraph):
                    converted.append(c)
                else:
                    style_name = "RuHeader" if header and i == 0 else "RuCell"
                    converted.append(Paragraph(str(c), self.styles[style_name]))
            processed.append(converted)
        table = Table(processed, colWidths=col_widths, repeatRows=1 if header else 0)
        commands = [
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("GRID", (0,0), (-1,-1), 0.4, BORDER),
            ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ]
        if alignments:
            for col, alignment in enumerate(alignments):
                commands.append(("ALIGN", (col, 0), (col, -1), alignment))
        if header:
            commands += [("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white)]
        if highlight_last and len(data) > 1:
            commands += [("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#DBEAFE"))]
        table.setStyle(TableStyle(commands))
        return table
