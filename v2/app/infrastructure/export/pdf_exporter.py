"""PDF-экспорт расчёта (reportlab)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from app.domain.models import SystemCalculationResult, ComparisonResult, RecommendationResult
from app.config import AppSettings


class PDFExporter:
    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings()
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name="RusTitle", fontSize=16, leading=20, spaceAfter=8, textColor=colors.HexColor("#1a1a2e")))
        self.styles.add(ParagraphStyle(name="RusHeading", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a56db")))
        self.styles.add(ParagraphStyle(name="RusBody", fontSize=9, leading=12))
        self.styles.add(ParagraphStyle(name="RusSmall", fontSize=8, leading=10, textColor=colors.HexColor("#6b7280")))

    def export_calculation(self, result: SystemCalculationResult, path: str | Path) -> Path:
        path = Path(path)
        doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
        story = []
        story.extend(self._title_page(result))
        story.extend(self._section_layers(result))
        story.extend(self._section_totals(result))
        story.extend(self._section_notes())
        doc.build(story)
        return path

    def _title_page(self, result: SystemCalculationResult) -> list:
        obj = result.object_data
        elems = [
            Paragraph("\u041a\u0430\u043b\u044c\u043a\u0443\u043b\u044f\u0442\u043e\u0440 \u041b\u041a\u041c / \u0410\u041a\u0417 \u2014 \u041e\u0442\u0447\u0451\u0442 р\u0430\u0441\u0447\u0451\u0442\u0430", self.styles["RusTitle"]),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a56db")),
            Spacer(1, 6),
            Paragraph(f"<b>\u041e\u0431\u044a\u0435\u043a\u0442:</b> {obj.object_name or '\u2014'}", self.styles["RusBody"]),
            Paragraph(f"<b>\u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a:</b> {obj.customer or '\u2014'}", self.styles["RusBody"]),
            Paragraph(f"<b>\u041f\u043b\u043e\u0449\u0430\u0434\u044c:</b> {obj.area_m2} \u043c\u00b2", self.styles["RusBody"]),
            Paragraph(f"<b>\u0421\u0438\u0441\u0442\u0435\u043c\u0430:</b> {result.system.system_name or '\u2014'}", self.styles["RusBody"]),
            Paragraph(f"<b>\u0414\u0430\u0442\u0430:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}", self.styles["RusBody"]),
            Spacer(1, 10),
        ]
        return elems

    def _section_layers(self, result: SystemCalculationResult) -> list:
        elems = [Paragraph("\u0421\u043b\u043e\u0438 с\u0438\u0441\u0442\u0435\u043c\u044b", self.styles["RusHeading"])]
        data = [["\u2116", "\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b", "DFT", "WFT", "\u043a\u0433/\u043c\u00b2", "\u0440\u0443\u0431/\u043c\u00b2"]]
        for i, lr in enumerate(result.layers, 1):
            data.append([
                str(i), lr.material.material_name[:30],
                f"{lr.target_dft:.0f}", f"{lr.wft:.1f}",
                f"{lr.practical_consumption_kg:.3f}", f"{lr.cost_per_m2:.2f}",
            ])
        t = Table(data, colWidths=[20, 150, 40, 40, 50, 55])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d4dc")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 8))
        return elems

    def _section_totals(self, result: SystemCalculationResult) -> list:
        elems = [Paragraph("\u0418\u0442\u043e\u0433\u0438", self.styles["RusHeading"])]
        data = [
            ["\u0421\u043b\u043e\u0451\u0432", str(len(result.layers))],
            ["DFT, \u043c\u043a\u043c", f"{result.total_dft:.0f}"],
            ["\u0420\u0430\u0441\u0445\u043e\u0434, \u043a\u0433/\u043c\u00b2", f"{result.total_practical_consumption_kg:.3f}"],
            ["\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c, \u0440\u0443\u0431/\u043c\u00b2", f"{result.total_cost_per_m2:.2f}"],
            ["\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043e\u0431\u044a\u0435\u043a\u0442\u0430, \u0440\u0443\u0431", f"{result.total_cost:,.0f}".replace(",", " ")],
        ]
        t = Table(data, colWidths=[150, 100])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d4dc")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        elems.append(t)
        return elems

    def _section_notes(self) -> list:
        return [
            Spacer(1, 12),
            Paragraph(
                "\u0420\u0430\u0441\u0447\u0451\u0442 \u043d\u043e\u0441\u0438\u0442 \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440. "
                "\u041e\u043a\u043e\u043d\u0447\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0432\u044b\u0431\u043e\u0440 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u0410\u041a\u0417 \u2014 \u043f\u043e TDS \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f \u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u043d\u044b\u043c \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f\u043c.",
                self.styles["RusSmall"],
            ),
        ]
