"""Таблица слоёв с горячим редактированием и валидацией."""
from __future__ import annotations
from dataclasses import replace
from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QToolTip
from PySide6.QtCore import Qt,Signal,QTimer
from app.domain.models import LayerResult
from app.domain.calculator import LayerInput

COLUMNS=[("№",40),("Материал",220),("Связующее",100),("2К",45),("Цена, ₽/кг",95),("DFT, мкм",80),("Потери, %",75),("Разб., %",70),("WFT, мкм",80),("Расход, л/м²",105),("Расход, кг/м²",110),("Стоимость, руб/м²",125)]
EDITABLE_COLUMNS={4,5,6,7}

class LayerTableWidget(QTableWidget):
    """Таблица слоёв: редактирование входных данных и расчётных показателей."""
    layer_changed=Signal()
    def __init__(self,parent=None):
        super().__init__(0,len(COLUMNS),parent); self.setHorizontalHeaderLabels([x[0] for x in COLUMNS]); self.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for i,(_,w) in enumerate(COLUMNS):
            if i!=1:self.setColumnWidth(i,w)
        self.setAlternatingRowColors(True); self.setSelectionBehavior(QAbstractItemView.SelectRows); self.setSelectionMode(QAbstractItemView.SingleSelection); self.verticalHeader().setVisible(False); self._layer_inputs=[]; self._updating=False; self._last_valid={}; self.itemChanged.connect(self._changed)
    def _item(self,text,align=Qt.AlignCenter,edit=False):
        x=QTableWidgetItem(str(text)); x.setTextAlignment(align)
        if not edit:x.setFlags(x.flags()&~Qt.ItemIsEditable)
        return x
    def set_layers(self,layers,results=None):
        self._updating=True
        try:
            self._layer_inputs=list(layers); self.setRowCount(len(layers)); self._last_valid.clear()
            for r,li in enumerate(layers):self._fill(r,li,results[r] if results and r<len(results) else None)
        finally:self._updating=False
    def _fill(self,r,li,result):
        self.setItem(r,0,self._item(r+1)); self.setItem(r,1,self._item(li.material.material_name,Qt.AlignLeft|Qt.AlignVCenter)); b=li.material.binder_type.value if hasattr(li.material.binder_type,'value') else str(li.material.binder_type); self.setItem(r,2,self._item(b)); self.setItem(r,3,self._item('Да' if li.material.is_two_component else 'Нет'))
        p=li.material.price_per_kg; price='' if p is None else f'{p:.2f}'; self.setItem(r,4,self._item(price,edit=True)); self.setItem(r,5,self._item(f'{li.target_dft:.0f}',edit=True)); self.setItem(r,6,self._item(f'{li.losses_percent:.0f}',edit=True)); self.setItem(r,7,self._item(f'{li.thinner_percent:.0f}',edit=True))
        for c in EDITABLE_COLUMNS:self._last_valid[(r,c)]=self.item(r,c).text()
        if result:
            cost=f'{result.cost_per_m2+result.thinner_cost_per_m2:.2f}' if result.cost_per_m2 is not None and result.thinner_cost_per_m2 is not None else '—'
            vals=(f'{result.wft:.1f}',f'{result.practical_consumption_l:.4f}',f'{result.practical_consumption_kg:.4f}',cost)
        else: vals=('—','—','—','—')
        for c,v in zip((8,9,10,11),vals):self.setItem(r,c,self._item(v))
    def _error(self,item,message):
        item.setToolTip(message); item.setData(Qt.UserRole,'invalid'); item.setBackground(self.palette().brush(self.palette().ColorRole.BrightText)); QToolTip.showText(self.viewport().mapToGlobal(self.visualItemRect(item).center()),message,self)
    def _clear_error(self,item):
        item.setToolTip(''); item.setData(Qt.UserRole,None); item.setBackground(self.palette().base())
    def _restore_invalid(self,item,message):
        self._error(item,message); old=self._last_valid.get((item.row(),item.column()),''); QTimer.singleShot(700,lambda:self._restore_if_still_invalid(item,old))
    def _restore_if_still_invalid(self,item,old):
        if item is None:return
        if item.data(Qt.UserRole)=='invalid':
            self._updating=True
            try:item.setText(old)
            finally:self._updating=False
            self._clear_error(item)
    def _changed(self,item):
        if self._updating or item.column() not in EDITABLE_COLUMNS:return
        row=item.row()
        if row<0 or row>=len(self._layer_inputs):return
        text=item.text().strip().replace(',','.'); col=item.column()
        if col==4 and text=='':
            li=self._layer_inputs[row]; li.material=replace(li.material,price_per_kg=None,price_per_liter=None); self._last_valid[(row,col)]=''; self._clear_error(item); self.layer_changed.emit(); return
        try:v=float(text)
        except ValueError:
            self._restore_invalid(item,'Введите число. Для цены можно оставить поле пустым — цена будет считаться неизвестной.'); return
        rules={4:(v>=0,'Цена не может быть отрицательной.'),5:(0<v<=2000,'DFT должен быть больше 0 и не превышать 2000 мкм.'),6:(0<=v<=99,'Потери должны быть от 0 до 99 %.'),7:(0<=v<=100,'Разбавитель должен быть от 0 до 100 %.')}
        valid,message=rules[col]
        if not valid:self._restore_invalid(item,message); return
        li=self._layer_inputs[row]
        if col==4:li.material=replace(li.material,price_per_kg=v,price_per_liter=None)
        elif col==5:li.target_dft=v
        elif col==6:li.losses_percent=v
        elif col==7:li.thinner_percent=v
        self._last_valid[(row,col)]=item.text(); self._clear_error(item); self.layer_changed.emit()
    def get_layer_inputs(self):return list(self._layer_inputs)
    def add_layer(self,li):
        self._layer_inputs.append(li); r=self.rowCount(); self.insertRow(r); self._updating=True
        try:self._fill(r,li,None)
        finally:self._updating=False
        self.layer_changed.emit()
    def remove_selected(self):
        r=self.currentRow()
        if r<0 or r>=len(self._layer_inputs):return
        self._layer_inputs.pop(r); self.removeRow(r); self._last_valid={(rr,c):v for (rr,c),v in self._last_valid.items() if rr!=r for v in [v]}
        for i in range(self.rowCount()):self.item(i,0).setText(str(i+1))
        self._last_valid.clear()
        for i in range(self.rowCount()):
            for c in EDITABLE_COLUMNS:self._last_valid[(i,c)]=self.item(i,c).text()
        self.layer_changed.emit()
    def clear_layers(self):self._layer_inputs.clear(); self.setRowCount(0); self._last_valid.clear(); self.layer_changed.emit()
