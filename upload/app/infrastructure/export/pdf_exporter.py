"""PDF-отчёт расчёта ЛКМ / АКЗ с инженерным, коммерческим и полным режимами."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.config import AppSettings
from app.domain.models import SystemCalculationResult, ComparisonResult, RecommendationResult
from app.domain.formulas import FORMULA_VERSION

BLUE=colors.HexColor("#1A56DB"); DARK=colors.HexColor("#1A1A2E"); GRAY=colors.HexColor("#6B7280"); BORDER=colors.HexColor("#D0D4DC")

def _try_register_fonts()->str:
    candidates=["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf","/usr/share/fonts/truetype/freefont/FreeSans.ttf","C:/Windows/Fonts/arial.ttf"]
    for path in candidates:
        if not Path(path).exists(): continue
        try:
            pdfmetrics.registerFont(TTFont("AppFont",path)); bold=path.replace("DejaVuSans.ttf","DejaVuSans-Bold.ttf").replace("Regular","Bold"); pdfmetrics.registerFont(TTFont("AppFont-Bold",bold if Path(bold).exists() else path)); return "AppFont"
        except Exception: continue
    return "Helvetica"

def _area(result)->float:return max(float(result.object_data.area_m2 or 0.0),0.0)
def _cost(value,digits=2)->str:return "—" if value is None else f"{value:.{digits}f}"
def _cost_add(*values):return None if any(v is None for v in values) else sum(values)

class PDFExporter:
    """Экспорт без закупочной, складской и фасовочной информации."""
    def __init__(self,settings:Optional[AppSettings]=None):
        self.settings=settings or AppSettings.load(); self.font=_try_register_fonts(); self.font_bold=f"{self.font}-Bold" if self.font!="Helvetica" else "Helvetica-Bold"; self.styles=self._build_styles()
    @property
    def report_mode(self): return self.settings.report_mode if self.settings.report_mode in {"engineering","commercial","full"} else "engineering"
    def _build_styles(self):
        s=getSampleStyleSheet(); s.add(ParagraphStyle(name="RuTitle",fontName=self.font_bold,fontSize=16,textColor=DARK,spaceAfter=6,alignment=TA_CENTER)); s.add(ParagraphStyle(name="RuHeading",fontName=self.font_bold,fontSize=12,textColor=BLUE,spaceBefore=12,spaceAfter=6,alignment=TA_LEFT)); s.add(ParagraphStyle(name="RuBody",fontName=self.font,fontSize=9,textColor=DARK,spaceAfter=3,leading=12,alignment=TA_LEFT)); s.add(ParagraphStyle(name="RuSmall",fontName=self.font,fontSize=8,textColor=GRAY,spaceAfter=2,leading=10,alignment=TA_LEFT)); s.add(ParagraphStyle(name="RuCell",fontName=self.font,fontSize=8,textColor=DARK,leading=10,alignment=TA_CENTER)); s.add(ParagraphStyle(name="RuCellLeft",fontName=self.font,fontSize=8,textColor=DARK,leading=10,alignment=TA_LEFT)); s.add(ParagraphStyle(name="RuCellBold",fontName=self.font_bold,fontSize=8,textColor=DARK,leading=10,alignment=TA_CENTER)); s.add(ParagraphStyle(name="RuCellBoldLeft",fontName=self.font_bold,fontSize=8,textColor=DARK,leading=10,alignment=TA_LEFT)); s.add(ParagraphStyle(name="RuHeader",fontName=self.font_bold,fontSize=7.5,textColor=colors.white,leading=9,alignment=TA_CENTER)); return s
    def export_calculation(self,result:SystemCalculationResult,path:str|Path,recommendation:Optional[RecommendationResult]=None,comparison:Optional[ComparisonResult]=None)->Path:
        path=Path(path); doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm,title="Расчёт ЛКМ / АКЗ",author=self.settings.organization_name)
        story=self._title(result)+self._section_input(result)+self._section_layers(result)+self._section_totals(result)
        if comparison and len(comparison.systems)>=2: story+=self._section_comparison(comparison)
        if recommendation and recommendation.items: story+=self._section_recommendations(recommendation)
        story+=self._section_notes(); doc.build(story); return path
    def _title(self,result):
        obj=result.object_data; area=_area(result); mode_title={"engineering":"Инженерный расчёт","commercial":"Коммерческий расчёт","full":"Полный расчёт"}[self.report_mode]; items=[Paragraph(mode_title+" — ЛКМ / АКЗ",self.styles["RuTitle"]),HRFlowable(width="100%",thickness=1.5,color=BLUE,spaceAfter=8)]
        logo=Path(self.settings.logo_path).expanduser() if self.settings.logo_path else None
        if logo and logo.exists():
            try: img=Image(str(logo),width=28*mm,height=14*mm); img.hAlign="LEFT"; items += [img,Spacer(1,2*mm)]
            except Exception: pass
        items.append(Paragraph(self.settings.organization_name or "Организация",self.styles["RuBody"]))
        if self.settings.organization_address: items.append(Paragraph(f"<b>Адрес:</b> {self.settings.organization_address}",self.styles["RuSmall"]))
        contact=" · ".join(x for x in (self.settings.organization_phone,self.settings.organization_email) if x)
        if contact: items.append(Paragraph(contact,self.styles["RuSmall"]))
        items += [Paragraph(f"Дата расчёта: {datetime.now():%d.%m.%Y %H:%M}",self.styles["RuSmall"]),Paragraph(f"Версия формул: {FORMULA_VERSION}",self.styles["RuSmall"]),Paragraph(f"<b>Объект:</b> {obj.object_name or '—'}",self.styles["RuBody"]),Paragraph(f"<b>Заказчик:</b> {obj.customer or '—'}",self.styles["RuBody"]),Paragraph(f"<b>Площадь:</b> {area:.2f} м²",self.styles["RuBody"]),Paragraph(f"<b>Система:</b> {result.system.system_name or 'Пользовательская система'}",self.styles["RuBody"]),Spacer(1,4*mm)]; return items
    def _section_input(self,result):
        obj=result.object_data; area=_area(result); data=[["Параметр","Значение"],["Объект",obj.object_name or "—"],["Заказчик",obj.customer or "—"],["Проект",obj.project or "—"],["№ расчёта",obj.calculation_number or "—"],["Площадь",f"{area:.2f} м²"],["Система",result.system.system_name or "Пользовательская система"]]
        return [Paragraph("1. Исходные данные расчёта",self.styles["RuHeading"]),self._table(data,[75*mm,95*mm],alignments=["LEFT","LEFT"]),Spacer(1,3*mm)]
    def _section_layers(self,result):
        mode=self.report_mode
        if mode=="engineering": data=[["№","Материал","DFT","WFT","Теор. кг/м²","Практ. кг/м²","Теор. л/м²","Практ. л/м²","Стоимость системы, руб/м²"]]; widths=[7,45,15,15,19,19,19,19,22]
        elif mode=="commercial": data=[["№","Материал","Цена, руб/кг","Цена, руб/л","Расход, кг/м²","Расход на объект, кг","Стоимость, руб/м²","Стоимость объекта, руб"]]; widths=[7,43,20,20,20,24,23,23]
        else: data=[["№","Материал","DFT","WFT","Теор. кг/м²","Практ. кг/м²","Теор. л/м²","Практ. л/м²","Цена, руб/кг","Цена, руб/л","Стоимость, руб/м²","Стоимость объекта, руб"]]; widths=[7,30,11,11,15,15,15,15,14,14,17,16]
        for i,lr in enumerate(result.layers,1):
            name=lr.material.display_name() if hasattr(lr.material,"display_name") else lr.material.material_name; total_m2=_cost_add(lr.cost_per_m2,lr.thinner_cost_per_m2); area=_area(result)
            if mode=="engineering": row=[str(i),Paragraph(name,self.styles["RuCellLeft"]),f"{lr.target_dft:.0f}",f"{lr.wft:.1f}",f"{lr.theoretical_consumption_kg:.3f}",f"{lr.practical_consumption_kg:.3f}",f"{lr.theoretical_consumption_l:.3f}",f"{lr.practical_consumption_l:.3f}",_cost(total_m2)]
            elif mode=="commercial": row=[str(i),Paragraph(name,self.styles["RuCellLeft"]),_cost(lr.material.price_per_kg),_cost(lr.material.price_per_liter),f"{lr.practical_consumption_kg:.3f}",f"{lr.practical_consumption_kg*area:.2f}",_cost(total_m2),_cost(lr.total_cost)]
            else: row=[str(i),Paragraph(name,self.styles["RuCellLeft"]),f"{lr.target_dft:.0f}",f"{lr.wft:.1f}",f"{lr.theoretical_consumption_kg:.3f}",f"{lr.practical_consumption_kg:.3f}",f"{lr.theoretical_consumption_l:.3f}",f"{lr.practical_consumption_l:.3f}",_cost(lr.material.price_per_kg),_cost(lr.material.price_per_liter),_cost(total_m2),_cost(lr.total_cost)]
            data.append(row)
        if mode=="engineering": total=["",Paragraph("ИТОГО",self.styles["RuCellBoldLeft"]),f"{result.total_dft:.0f}","",f"{result.total_theoretical_consumption_kg:.3f}",f"{result.total_practical_consumption_kg:.3f}",f"{result.total_theoretical_consumption_l:.3f}",f"{result.total_practical_consumption_l:.3f}",_cost(result.total_cost_per_m2)]
        elif mode=="commercial": total=["",Paragraph("ИТОГО",self.styles["RuCellBoldLeft"]),"","",f"{result.total_practical_consumption_kg:.3f}",f"{result.total_practical_consumption_kg*_area(result):.2f}",_cost(result.total_cost_per_m2),_cost(result.total_cost)]
        else: total=["",Paragraph("ИТОГО",self.styles["RuCellBoldLeft"]),f"{result.total_dft:.0f}","",f"{result.total_theoretical_consumption_kg:.3f}",f"{result.total_practical_consumption_kg:.3f}",f"{result.total_theoretical_consumption_l:.3f}",f"{result.total_practical_consumption_l:.3f}","","",_cost(result.total_cost_per_m2),_cost(result.total_cost)]
        data.append(total); aligns=["CENTER","LEFT"]+["CENTER"]*(len(data[0])-2)
        return [Paragraph("2. Состав системы и показатели слоёв",self.styles["RuHeading"]),self._table(data,[x*mm for x in widths],highlight_last=True,alignments=aligns),Spacer(1,3*mm)]
    def _section_totals(self,result):
        area=_area(result); mode=self.report_mode; thinner_kg=sum(l.thinner_consumption_kg for l in result.layers); thinner_l=sum(l.thinner_consumption_l for l in result.layers)
        if mode=="engineering": data=[["Показатель","Значение"],["Количество слоёв",str(len(result.layers))],["Общая толщина DFT",f"{result.total_dft:.0f} мкм"],["Теоретический расход ЛКМ",f"{result.total_theoretical_consumption_kg:.3f} кг/м²"],["Теоретический расход ЛКМ",f"{result.total_theoretical_consumption_l:.3f} л/м²"],["Практический расход ЛКМ",f"{result.total_practical_consumption_kg:.3f} кг/м²"],["Практический расход ЛКМ",f"{result.total_practical_consumption_l:.3f} л/м²"],["Расход разбавителя",f"{thinner_kg:.3f} кг/м² ({thinner_l:.3f} л/м²)"],["Стоимость системы",f"{_cost(result.total_cost_per_m2)} руб/м²"]]
        elif mode=="commercial": data=[["Показатель","Значение"],["Система",result.system.system_name or "Пользовательская система"],["Площадь объекта",f"{area:.2f} м²"],["Стоимость системы",f"{_cost(result.total_cost_per_m2)} руб/м²"],["Стоимость объекта",f"{_cost(result.total_cost)} руб"],["В том числе стоимость разбавителя",f"{_cost(result.total_thinner_cost)} руб"]]
        else: data=[["Показатель","Значение"],["Количество слоёв",str(len(result.layers))],["Общая толщина DFT",f"{result.total_dft:.0f} мкм"],["Теоретический расход ЛКМ",f"{result.total_theoretical_consumption_kg:.3f} кг/м² ({result.total_theoretical_consumption_l:.3f} л/м²)"],["Практический расход ЛКМ",f"{result.total_practical_consumption_kg:.3f} кг/м² ({result.total_practical_consumption_l:.3f} л/м²)"],["Расход разбавителя",f"{thinner_kg:.3f} кг/м² ({thinner_l:.3f} л/м²)"],["Стоимость системы",f"{_cost(result.total_cost_per_m2)} руб/м²"],["Стоимость объекта",f"{_cost(result.total_cost)} руб"],["В том числе стоимость разбавителя",f"{_cost(result.total_thinner_cost)} руб"]]
        return [Paragraph("3. Итоговые показатели",self.styles["RuHeading"]),self._table(data,[90*mm,80*mm],alignments=["LEFT","CENTER"]),Spacer(1,3*mm)]
    def _section_comparison(self,comparison):
        systems=comparison.systems; data=[["Показатель"]+[(s.system.system_name or f"Сис.{i+1}") for i,s in enumerate(systems)]]; rows=[("Слоёв",[str(len(s.layers)) for s in systems]),("DFT, мкм",[f"{s.total_dft:.0f}" for s in systems]),("Теор. кг/м²",[f"{s.total_theoretical_consumption_kg:.3f}" for s in systems]),("Практ. кг/м²",[f"{s.total_practical_consumption_kg:.3f}" for s in systems]),("Стоимость, руб/м²",[_cost(s.total_cost_per_m2) for s in systems]),("Стоимость объекта, руб",[_cost(s.total_cost,0) for s in systems])]
        if self.report_mode=="commercial": rows=[r for r in rows if r[0] in {"Стоимость, руб/м²","Стоимость объекта, руб"}]
        elif self.report_mode=="engineering": rows=[r for r in rows if r[0]!="Стоимость объекта, руб"]
        for label,values in rows:data.append([label]+values)
        n=len(systems); return [Paragraph("4. Сравнение альтернативных систем",self.styles["RuHeading"]),self._table(data,[35*mm]+[(140/n)*mm]*n,alignments=["LEFT"]+["CENTER"]*n),Spacer(1,3*mm)]
    def _section_recommendations(self,rec):
        data=[["Место","Система","Score","Ключевые причины"]]
        for item in rec.items[:5]: data.append([str(item.rank),Paragraph(item.system.system_name or "—",self.styles["RuCellLeft"]),f"{item.score:.0f}",Paragraph("; ".join(item.reasons[:3])[:100] or "—",self.styles["RuCellLeft"])])
        return [Paragraph("5. Рекомендации",self.styles["RuHeading"]),Paragraph(rec.message or "—",self.styles["RuBody"]),self._table(data,[15*mm,50*mm,15*mm,90*mm],alignments=["CENTER","LEFT","CENTER","LEFT"]),Paragraph(rec.disclaimer or "",self.styles["RuSmall"]),Spacer(1,3*mm)]
    def _section_notes(self): return [Paragraph("Примечание",self.styles["RuHeading"]),Paragraph("Режим отчёта определён в настройках. Закупочная потребность, фасовка, остатки и складские операции в отчёт не включаются.",self.styles["RuSmall"])]
    def _table(self,data,widths,highlight_last=False,alignments=None):
        rows=[]
        for r,row in enumerate(data):
            converted=[]
            for c,value in enumerate(row):
                if isinstance(value,Paragraph): converted.append(value); continue
                style="RuHeader" if r==0 else ("RuCell" if not alignments or alignments[c]!="LEFT" else "RuCellLeft"); converted.append(Paragraph(str(value),self.styles[style]))
            rows.append(converted)
        table=Table(rows,colWidths=widths,repeatRows=1,hAlign="LEFT"); commands=[("GRID",(0,0),(-1,-1),0.4,BORDER),("BACKGROUND",(0,0),(-1,0),BLUE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4)]
        if highlight_last: commands.append(("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#EAF2FF")))
        table.setStyle(TableStyle(commands)); return table
