"""Экран сравнения систем покрытия."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QAbstractItemView,QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QBrush
from app.domain.models import ComparisonResult,ObjectData
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.infrastructure.export.engineering_excel_exporter import EngineeringExcelExporter

class ComparisonView(QWidget):
    def __init__(self,service:CalculationService,parent=None):
        super().__init__(parent);self.service=service;self._systems_data=[];self._object=ObjectData(area_m2=1.0);self._last_comparison=None;self._build_ui()
    def _build_ui(self):
        root=QVBoxLayout(self);root.setContentsMargins(12,12,12,12);title=QLabel("Сравнение систем");title.setProperty("heading",True);root.addWidget(title)
        sub=QLabel("Сравнивайте инженерные и коммерческие показатели систем. Складские остатки и закупочная информация не включаются.");sub.setProperty("subheading",True);sub.setWordWrap(True);root.addWidget(sub)
        row=QHBoxLayout();self.btn_compare=QPushButton("Сравнить");self.btn_compare.clicked.connect(self._on_compare);self.btn_export=QPushButton("Экспорт сравнения");self.btn_export.setProperty("secondary",True);self.btn_export.setEnabled(False);self.btn_export.clicked.connect(self._on_export);self.btn_clear=QPushButton("Очистить");self.btn_clear.setProperty("secondary",True);self.btn_clear.clicked.connect(self._on_clear);self.lbl_count=QLabel("Систем: 0")
        for x in (self.btn_compare,self.btn_export,self.btn_clear,self.lbl_count):row.addWidget(x)
        row.addStretch();root.addLayout(row)
        self.table=QTableWidget(0,1);self.table.setHorizontalHeaderLabels(["Показатель"]);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.table.setAlternatingRowColors(True);self.table.setSelectionMode(QAbstractItemView.NoSelection);self.table.verticalHeader().setVisible(False);root.addWidget(self.table);self.lbl_legend=QLabel();self.lbl_legend.setProperty("subheading",True);root.addWidget(self.lbl_legend)
    def set_object(self,obj:ObjectData):self._object=obj
    def add_system(self,name,layers):
        if len(self._systems_data)>=10:QMessageBox.warning(self,"Лимит","Максимум 10 систем для сравнения");return
        self._systems_data.append((name or f"Система {len(self._systems_data)+1}",list(layers)));self._last_comparison=None;self.btn_export.setEnabled(False);self.lbl_count.setText(f"Систем: {len(self._systems_data)}")
    def add_from_calculation(self,result):
        layers=[LayerInput(material=lr.material,target_dft=lr.target_dft,losses_percent=lr.losses_percent,thinner_percent=lr.thinner_percent,thinner=lr.thinner) for lr in result.layers];self.add_system(result.system.system_name or f"Система {len(self._systems_data)+1}",layers)
        if result.object_data.area_m2 and result.object_data.area_m2>0:self._object=result.object_data
    def _on_clear(self):
        self._systems_data.clear();self._last_comparison=None;self.table.setRowCount(0);self.table.setColumnCount(1);self.table.setHorizontalHeaderLabels(["Показатель"]);self.lbl_count.setText("Систем: 0");self.lbl_legend.clear();self.btn_export.setEnabled(False)
    def _on_compare(self):
        if len(self._systems_data)<2:QMessageBox.warning(self,"Внимание","Добавьте не менее 2 систем");return
        try:self._last_comparison=self.service.compare_systems(self._object,self._systems_data)
        except ValueError as exc:QMessageBox.warning(self,"Расчёт невозможен",str(exc));return
        self._fill_table(self._last_comparison);self.btn_export.setEnabled(True)
    def _on_export(self):
        if self._last_comparison is None:return
        path,_=QFileDialog.getSaveFileName(self,"Сохранить сравнение","Сравнение_систем_ЛКМ.xlsx","Excel (*.xlsx)")
        if not path:return
        try:EngineeringExcelExporter().export_comparison(self._last_comparison,Path(path));QMessageBox.information(self,"Экспорт","Сравнение сохранено в Excel")
        except Exception as exc:QMessageBox.critical(self,"Ошибка экспорта",str(exc))
    @staticmethod
    def _format_value(value):
        if value is None:return "—"
        if isinstance(value,float):return f"{value:,.2f}".replace(","," ") if abs(value)<1000 else f"{value:,.0f}".replace(","," ")
        return str(value)
    def _fill_table(self,comparison:ComparisonResult):
        systems=comparison.systems;headers=["Показатель"]+[(s.system.system_name or f"Система {i+1}")[:30] for i,s in enumerate(systems)];self.table.setColumnCount(len(headers));self.table.setHorizontalHeaderLabels(headers)
        thinner_m2=[(s.total_thinner_cost/s.object_data.area_m2) if s.total_thinner_cost is not None and s.object_data.area_m2 else None for s in systems]
        total_materials_thinner_m2=[(s.total_cost_per_m2+t) if s.total_cost_per_m2 is not None and t is not None else None for s,t in zip(systems,thinner_m2)]
        rows=[
            ("Количество слоёв",[len(s.layers) for s in systems],False),
            ("Общая толщина, мкм",[s.total_dft for s in systems],False),
            ("Расход ЛКМ, кг/м²",[s.total_practical_consumption_kg for s in systems],True),
            ("Расход ЛКМ, л/м²",[s.total_practical_consumption_l for s in systems],True),
            ("Стоимость ЛКМ, руб/м²",[s.total_cost_per_m2 for s in systems],True),
            ("Стоимость ЛКМ на объект, руб",[s.total_cost for s in systems],True),
            ("Разбавитель, руб/м²",thinner_m2,True),
            ("ЛКМ + разбавитель, руб/м²",total_materials_thinner_m2,True),
        ];self.table.setRowCount(len(rows));green=QBrush(QColor("#d1fae5"));red=QBrush(QColor("#fee2e2"))
        for r,(label,values,highlight) in enumerate(rows):
            self.table.setItem(r,0,QTableWidgetItem(label));numeric=[v for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)];mn=min(numeric) if numeric else None;mx=max(numeric) if numeric else None
            for c,v in enumerate(values):
                item=QTableWidgetItem(self._format_value(v));item.setTextAlignment(Qt.AlignCenter)
                if highlight and numeric and isinstance(v,(int,float)):
                    if v==mn:item.setBackground(green)
                    elif v==mx and mn!=mx:item.setBackground(red)
                self.table.setItem(r,c+1,item)
        self.table.resizeColumnsToContents();self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        parts=[]
        if comparison.thinnest_index is not None:parts.append(f"Минимальная толщина: {headers[comparison.thinnest_index+1]}")
        if comparison.cheapest_index is not None:parts.append(f"Минимальная стоимость: {headers[comparison.cheapest_index+1]}")
        if comparison.best_balance_index is not None:parts.append(f"Лучший баланс: {headers[comparison.best_balance_index+1]}")
        self.lbl_legend.setText("  |  ".join(parts))
