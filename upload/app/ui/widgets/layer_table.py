"""Таблица слоёв с горячим редактированием расчётных параметров."""
from __future__ import annotations
from dataclasses import replace
from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView
from PySide6.QtCore import Qt,Signal,QTimer
from app.domain.models import LayerResult
from app.domain.calculator import LayerInput
COLUMNS=[("№",40),("Материал",220),("Связующее",100),("2К",45),("Цена, ₽/кг",95),("DFT, мкм",80),("Потери, %",75),("Разб., %",70),("WFT, мкм",80),("Расход, кг/м²",100),("Стоимость, руб/м²",120)]
class LayerTableWidget(QTableWidget):
    layer_changed=Signal()
    def __init__(self,parent=None):
        super().__init__(0,len(COLUMNS),parent); self.setHorizontalHeaderLabels([x[0] for x in COLUMNS]); self.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for i,(_,w) in enumerate(COLUMNS):
            if i!=1:self.setColumnWidth(i,w)
        self.setAlternatingRowColors(True); self.setSelectionBehavior(QAbstractItemView.SelectRows); self.setSelectionMode(QAbstractItemView.SingleSelection); self.verticalHeader().setVisible(False); self._layer_inputs=[]; self._updating=False; self._timer=QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(250); self._timer.timeout.connect(self._auto_recalculate); self.itemChanged.connect(self._changed)
    def _item(self,text,align=Qt.AlignCenter,edit=False):
        x=QTableWidgetItem(str(text)); x.setTextAlignment(align)
        if not edit:x.setFlags(x.flags()&~Qt.ItemIsEditable)
        return x
    def set_layers(self,layers,results=None):
        self._updating=True
        try:
            self._layer_inputs=list(layers); self.setRowCount(len(layers))
            for r,li in enumerate(layers):self._fill(r,li,results[r] if results and r<len(results) else None)
        finally:self._updating=False
    def _fill(self,r,li,result):
        self.setItem(r,0,self._item(r+1)); self.setItem(r,1,self._item(li.material.material_name,Qt.AlignLeft|Qt.AlignVCenter)); b=li.material.binder_type.value if hasattr(li.material.binder_type,'value') else str(li.material.binder_type); self.setItem(r,2,self._item(b)); self.setItem(r,3,self._item('Да' if li.material.is_two_component else 'Нет')); p=li.material.price_per_kg; self.setItem(r,4,self._item('' if p is None else f'{p:.2f}',edit=True)); self.setItem(r,5,self._item(f'{li.target_dft:.0f}',edit=True)); self.setItem(r,6,self._item(f'{li.losses_percent:.0f}',edit=True)); self.setItem(r,7,self._item(f'{li.thinner_percent:.0f}',edit=True))
        if result: cost=f'{result.cost_per_m2+result.thinner_cost_per_m2:.2f}' if result.cost_per_m2 is not None and result.thinner_cost_per_m2 is not None else '—'; vals=(f'{result.wft:.1f}',f'{result.practical_consumption_kg:.3f}',cost)
        else: vals=('—','—','—')
        for c,v in zip((8,9,10),vals):self.setItem(r,c,self._item(v))
    def _changed(self,item):
        if self._updating or item.column() not in {4,5,6,7}:return
        try:v=float(item.text().strip().replace(',','.'))
        except ValueError:return
        li=self._layer_inputs[item.row()]
        if item.column()==4 and v>=0:li.material=replace(li.material,price_per_kg=v,price_per_liter=None)
        elif item.column()==5 and v>0:li.target_dft=v
        elif item.column()==6 and 0<=v<=99:li.losses_percent=v
        elif item.column()==7 and 0<=v<=100:li.thinner_percent=v
        else:return
        self.layer_changed.emit(); self._timer.start()
    def _auto_recalculate(self):
        w=self.parentWidget()
        while w:
            b=getattr(w,'btn_calc',None)
            if b is not None:b.click(); return
            w=w.parentWidget()
    def get_layer_inputs(self):return list(self._layer_inputs)
    def add_layer(self,li):
        self._layer_inputs.append(li); r=self.rowCount(); self.insertRow(r); self._updating=True
        try:self._fill(r,li,None)
        finally:self._updating=False
        self.layer_changed.emit(); self._timer.start()
    def remove_selected(self):
        r=self.currentRow()
        if r<0 or r>=len(self._layer_inputs):return
        self._layer_inputs.pop(r); self.removeRow(r)
        for i in range(self.rowCount()):self.item(i,0).setText(str(i+1))
        self.layer_changed.emit(); self._timer.start()
    def clear_layers(self):self._timer.stop(); self._layer_inputs.clear(); self.setRowCount(0); self.layer_changed.emit()
