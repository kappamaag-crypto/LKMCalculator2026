"""Таблица слоёв с горячим редактированием и инженерными подсказками."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QToolTip

from app.domain.calculator import LayerInput

COLUMNS = [("№",40),("Материал",220),("Связующее",100),("2К",45),("Цена, ₽/кг",95),("DFT, мкм",80),("Потери, %",75),("Разб., %",70),("WFT, мкм",80),("Расход, л/м²",105),("Расход, кг/м²",110),("Стоимость, руб/м²",125)]
EDITABLE_COLUMNS={4,5,6,7}

class LayerTableWidget(QTableWidget):
    """Таблица слоёв: входные параметры и расчётные показатели."""
    layer_changed=Signal()
    def __init__(self,parent=None):
        super().__init__(0,len(COLUMNS),parent);self.setHorizontalHeaderLabels([x[0] for x in COLUMNS]);self.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.horizontalHeader().setDefaultAlignment(Qt.AlignCenter);self.setWordWrap(False);self.setTextElideMode(Qt.ElideRight)
        for i,(_,width) in enumerate(COLUMNS):
            if i!=1:self.setColumnWidth(i,width)
        self.horizontalHeader().setMinimumSectionSize(40);self.setAlternatingRowColors(True);self.setSelectionBehavior(QAbstractItemView.SelectRows);self.setSelectionMode(QAbstractItemView.SingleSelection);self.verticalHeader().setVisible(False);self._layer_inputs=[];self._updating=False;self._last_valid={};self.itemChanged.connect(self._changed)
    def _item(self,text,align=Qt.AlignCenter,edit=False,tooltip=None):
        item=QTableWidgetItem(str(text));item.setTextAlignment(align)
        if not edit:item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if tooltip:item.setToolTip(tooltip)
        return item
    @staticmethod
    def _dft_text(value):return "" if value is None else f"{value:.0f}"
    @staticmethod
    def _percent_text(value):return "" if value is None else f"{value:.0f}"
    @staticmethod
    def _dft_hint(material):
        minimum=getattr(material,"recommended_dft_min",None);maximum=getattr(material,"recommended_dft_max",None);hard_max=getattr(material,"hard_max_dft",None)
        if minimum is not None and maximum is not None:return f"Рекомендуемый DFT: {minimum:g}–{maximum:g} мкм."
        if minimum is not None:return f"Рекомендуемый DFT: от {minimum:g} мкм."
        if maximum is not None:return f"Рекомендуемый DFT: до {maximum:g} мкм."
        if hard_max is not None:return f"Жёсткий максимум DFT: {hard_max:g} мкм."
        return "Рекомендация по DFT для материала не задана."
    @staticmethod
    def _dft_state(material,dft):
        if dft is None:return "invalid","DFT не задан. Укажите толщину сухого слоя в мкм."
        minimum=getattr(material,"recommended_dft_min",None);maximum=getattr(material,"recommended_dft_max",None);hard_max=getattr(material,"hard_max_dft",None)
        if hard_max is not None and dft>hard_max:return "error",f"DFT {dft:g} мкм превышает жёсткий максимум {hard_max:g} мкм."
        if minimum is not None and dft<minimum:return "warning",f"DFT {dft:g} мкм ниже рекомендуемого минимума {minimum:g} мкм."
        if maximum is not None and dft>maximum:return "warning",f"DFT {dft:g} мкм выше рекомендуемого максимума {maximum:g} мкм."
        return "ok",LayerTableWidget._dft_hint(material)
    def set_layers(self,layers,results=None):
        self._updating=True
        try:self._layer_inputs=list(layers);self.setRowCount(len(layers));self._last_valid.clear();[self._fill(row,layer,results[row] if results and row<len(results) else None) for row,layer in enumerate(layers)]
        finally:self._updating=False
    def _fill(self,row,layer,result):
        material=layer.material;name=material.display_name() if hasattr(material,"display_name") else material.material_name;self.setItem(row,0,self._item(row+1));self.setItem(row,1,self._item(name,Qt.AlignLeft|Qt.AlignVCenter,tooltip=name));binder=material.binder_type.value if hasattr(material.binder_type,"value") else str(material.binder_type);self.setItem(row,2,self._item(binder,tooltip=binder));self.setItem(row,3,self._item("Да" if material.is_two_component else "Нет"));price="" if material.price_per_kg is None else f"{material.price_per_kg:.2f}";self.setItem(row,4,self._item(price,edit=True));dft_item=self._item(self._dft_text(layer.target_dft),edit=True);state,hint=self._dft_state(material,layer.target_dft);dft_item.setToolTip(hint);dft_item.setData(Qt.UserRole,state);self.setItem(row,5,dft_item);self.setItem(row,6,self._item(self._percent_text(layer.losses_percent),edit=True));self.setItem(row,7,self._item(self._percent_text(layer.thinner_percent),edit=True))
        for column in EDITABLE_COLUMNS:self._last_valid[(row,column)]=self.item(row,column).text()
        if result:
            cost=f"{result.cost_per_m2+result.thinner_cost_per_m2:.2f}" if result.cost_per_m2 is not None and result.thinner_cost_per_m2 is not None else "—";values=(f"{result.wft:.1f}",f"{result.practical_consumption_l:.4f}",f"{result.practical_consumption_kg:.4f}",cost)
        else:values=("—","—","—","—")
        for column,value in zip((8,9,10,11),values):self.setItem(row,column,self._item(value))
    def _error(self,item,message):
        item.setToolTip(message);item.setData(Qt.UserRole,"invalid");item.setBackground(self.palette().brush(self.palette().ColorRole.BrightText));QToolTip.showText(self.viewport().mapToGlobal(self.visualItemRect(item).center()),message,self)
    def _clear_error(self,item):item.setToolTip("");item.setData(Qt.UserRole,None);item.setBackground(self.palette().base())
    def _restore_invalid(self,item,message):
        self._error(item,message);old=self._last_valid.get((item.row(),item.column()),"");QTimer.singleShot(700,lambda:self._restore_if_still_invalid(item,old))
    def _restore_if_still_invalid(self,item,old):
        if item is not None and item.data(Qt.UserRole)=="invalid":
            self._updating=True
            try:item.setText(old)
            finally:self._updating=False
            self._clear_error(item)
    def _changed(self,item):
        if self._updating or item.column() not in EDITABLE_COLUMNS:return
        row=item.row()
        if row<0 or row>=len(self._layer_inputs):return
        text=item.text().strip().replace(",",".");column=item.column()
        if column==4 and text=="":
            layer=self._layer_inputs[row];layer.material=replace(layer.material,price_per_kg=None,price_per_liter=None);self._last_valid[(row,column)]="";self._clear_error(item);self.layer_changed.emit();return
        try:value=float(text)
        except ValueError:self._restore_invalid(item,"Введите число. Для цены можно оставить поле пустым — цена будет считаться неизвестной.");return
        rules={4:(value>=0,"Цена не может быть отрицательной."),5:(0<value<=2000,"DFT должен быть больше 0 и не превышать 2000 мкм."),6:(0<=value<=99,"Потери должны быть от 0 до 99 %."),7:(0<=value<100,"Разбавитель должен быть от 0 до 99,99 %." )};valid,message=rules[column]
        if not valid:self._restore_invalid(item,message);return
        layer=self._layer_inputs[row]
        if column==4:layer.material=replace(layer.material,price_per_kg=value,price_per_liter=None)
        elif column==5:
            layer.target_dft=value;state,hint=self._dft_state(layer.material,value);item.setData(Qt.UserRole,state);item.setToolTip(hint)
        elif column==6:layer.losses_percent=value
        elif column==7:layer.thinner_percent=value
        self._last_valid[(row,column)]=item.text()
        if column!=5:self._clear_error(item)
        self.layer_changed.emit()
    def get_layer_inputs(self):return list(self._layer_inputs)
    def add_layer(self,layer):
        self._layer_inputs.append(layer);row=self.rowCount();self.insertRow(row);self._updating=True
        try:self._fill(row,layer,None)
        finally:self._updating=False
        self.layer_changed.emit()
    def remove_selected(self):
        row=self.currentRow()
        if row<0 or row>=len(self._layer_inputs):return
        self._layer_inputs.pop(row);self.removeRow(row)
        for index in range(self.rowCount()):self.item(index,0).setText(str(index+1))
        self._last_valid.clear()
        for index in range(self.rowCount()):
            for column in EDITABLE_COLUMNS:self._last_valid[(index,column)]=self.item(index,column).text()
        self.layer_changed.emit()
    def clear_layers(self):self._layer_inputs.clear();self.setRowCount(0);self._last_valid.clear();self.layer_changed.emit()
