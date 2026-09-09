"""Редактор сохранённых систем покрытия."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QLineEdit,QComboBox,QPushButton,QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView
from PySide6.QtCore import Signal
from app.domain.models import Material
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.models import CoatingSystemORM,CoatingSystemLayerORM
from app.infrastructure.database.repositories import CoatingSystemRepository

class SystemsView(QWidget):
    systems_changed=Signal()
    def __init__(self,materials:list[Material],parent=None):
        super().__init__(parent);self._materials=list(materials);self._systems=[];self._current_id=None;self._build_ui();self.set_materials(materials);self.reload()
    def _build_ui(self):
        root=QVBoxLayout(self);top=QHBoxLayout();self.list_systems=QComboBox();self.list_systems.setMinimumWidth(420);self.list_systems.currentIndexChanged.connect(self._load_selected);self.btn_new=QPushButton("Новая система");self.btn_new.clicked.connect(self._new);self.btn_reload=QPushButton("Обновить");self.btn_reload.setProperty("secondary",True);self.btn_reload.clicked.connect(self.reload);top.addWidget(QLabel("Система:"));top.addWidget(self.list_systems,1);top.addWidget(self.btn_new);top.addWidget(self.btn_reload);root.addLayout(top)
        info=QGroupBox("Параметры системы");form=QFormLayout(info);self.ed_name=QLineEdit();self.ed_manufacturer=QLineEdit();self.ed_description=QLineEdit();self.ed_substrate=QLineEdit();self.ed_standards=QLineEdit();self.ed_certificate=QLineEdit();form.addRow("Название:",self.ed_name);form.addRow("Производитель:",self.ed_manufacturer);form.addRow("Описание:",self.ed_description);form.addRow("Основание:",self.ed_substrate);form.addRow("Нормативы:",self.ed_standards);form.addRow("Сертификат:",self.ed_certificate);root.addWidget(info)
        layerbox=QGroupBox("Слои системы");lv=QVBoxLayout(layerbox);buttons=QHBoxLayout();self.cmb_material=QComboBox();self.cmb_material.setMinimumWidth(380);self.btn_add_layer=QPushButton("Добавить слой");self.btn_add_layer.clicked.connect(self._add_layer);self.btn_del_layer=QPushButton("Удалить слой");self.btn_del_layer.setProperty("secondary",True);self.btn_del_layer.clicked.connect(self._delete_layer);buttons.addWidget(QLabel("Материал:"));buttons.addWidget(self.cmb_material);buttons.addWidget(self.btn_add_layer);buttons.addWidget(self.btn_del_layer);buttons.addStretch();lv.addLayout(buttons)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(["№","Материал","DFT мин, мкм","DFT целевой, мкм","DFT макс, мкм","Разбавитель, %"]);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.itemChanged.connect(self._renumber);lv.addWidget(self.table);root.addWidget(layerbox,1)
        bottom=QHBoxLayout();self.btn_save=QPushButton("Сохранить систему");self.btn_save.clicked.connect(self._save);self.btn_delete=QPushButton("Удалить систему");self.btn_delete.setProperty("secondary",True);self.btn_delete.clicked.connect(self._delete_system);bottom.addWidget(self.btn_save);bottom.addWidget(self.btn_delete);bottom.addStretch();bottom.addWidget(QLabel("Изменения применяются к базе только после сохранения."));root.addLayout(bottom)
    def set_materials(self,materials:list[Material]):
        self._materials=list(materials);self.cmb_material.clear()
        for m in self._materials:
            if m.material_type.value != "разбавитель":self.cmb_material.addItem(m.display_name(),m)
    def reload(self):
        try:
            with get_session_factory()() as session:self._systems=list(CoatingSystemRepository(session).list_all(active_only=True))
        except Exception as exc:self._systems=[];QMessageBox.warning(self,"База систем",f"Не удалось загрузить системы: {exc}");return
        self.list_systems.blockSignals(True);self.list_systems.clear();self.list_systems.addItem("— новая система —",None)
        for s in self._systems:self.list_systems.addItem(s.system_name,s.id)
        self.list_systems.blockSignals(False)
        if self._current_id is not None:
            idx=self.list_systems.findData(self._current_id);self.list_systems.setCurrentIndex(idx if idx>=0 else 0)
        else:self._new()
    def _new(self):
        self._current_id=None;self.list_systems.blockSignals(True);self.list_systems.setCurrentIndex(0);self.list_systems.blockSignals(False);self.ed_name.clear();self.ed_manufacturer.clear();self.ed_description.clear();self.ed_substrate.clear();self.ed_standards.clear();self.ed_certificate.clear();self.table.setRowCount(0)
    def _load_selected(self,index):
        sid=self.list_systems.itemData(index)
        if sid is None:
            if self._current_id is not None:self._new()
            return
        orm=next((x for x in self._systems if x.id==sid),None)
        if orm is None:return
        self._current_id=sid;self.ed_name.setText(orm.system_name);self.ed_manufacturer.setText(orm.manufacturer or "");self.ed_description.setText(orm.description or "");self.ed_substrate.setText(orm.substrate or "");self.ed_standards.setText(orm.standards or "");self.ed_certificate.setText(orm.certificate or "");self.table.blockSignals(True);self.table.setRowCount(0)
        for layer in orm.layers:
            material=next((m for m in self._materials if m.id==layer.material_id),None);self._append_row(layer.layer_number,material,layer.dft_min,layer.target_dft,layer.dft_max,layer.thinner_percent)
        self.table.blockSignals(False)
    def _append_row(self,num,material,dmin,target,dmax,thinner):
        r=self.table.rowCount();self.table.insertRow(r);vals=[str(num),material.display_name() if material else "Материал не найден",self._num(dmin),self._num(target),self._num(dmax),self._num(thinner,2)]
        for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(v))
        self.table.item(r,1).setData(32,material)
    @staticmethod
    def _num(v,dec=1):return "" if v is None else f"{v:.{dec}f}"
    def _add_layer(self):
        m=self.cmb_material.currentData()
        if m is None:return
        self._append_row(self.table.rowCount()+1,m,m.recommended_dft_min,m.recommended_dft_min,m.recommended_dft_max,0);self.table.selectRow(self.table.rowCount()-1)
    def _delete_layer(self):
        r=self.table.currentRow()
        if r>=0:self.table.removeRow(r);self._renumber()
    def _renumber(self,*args):
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):self.table.item(r,0).setText(str(r+1))
        self.table.blockSignals(False)
    @staticmethod
    def _float(table,row,col):
        item=table.item(row,col)
        if item is None or not item.text().strip():return None
        try:return float(item.text().replace(",","."))
        except ValueError:raise ValueError(f"Некорректное число в колонке {col+1}")
    def _save(self):
        name=self.ed_name.text().strip()
        if not name:QMessageBox.warning(self,"Система","Укажите название системы");return
        if self.table.rowCount()==0:QMessageBox.warning(self,"Система","Добавьте хотя бы один слой");return
        try:
            with get_session_factory()() as session:
                orm=session.get(CoatingSystemORM,self._current_id) if self._current_id else None
                if orm is None:orm=CoatingSystemORM();session.add(orm)
                orm.system_name=name;orm.manufacturer=self.ed_manufacturer.text().strip();orm.description=self.ed_description.text().strip();orm.substrate=self.ed_substrate.text().strip();orm.standards=self.ed_standards.text().strip();orm.certificate=self.ed_certificate.text().strip();orm.number_of_layers=self.table.rowCount();orm.is_active=True
                orm.layers.clear()
                for r in range(self.table.rowCount()):
                    material=self.table.item(r,1).data(32)
                    if material is None or material.id is None:raise ValueError(f"Материал слоя №{r+1} не найден")
                    dmin=self._float(self.table,r,2);target=self._float(self.table,r,3);dmax=self._float(self.table,r,4);thin=self._float(self.table,r,5) or 0
                    if target is None or target<=0:raise ValueError(f"Укажите целевой DFT для слоя №{r+1}")
                    orm.layers.append(CoatingSystemLayerORM(layer_number=r+1,material_id=material.id,layer_type=material.material_type.value,dft_min=dmin,dft_max=dmax,target_dft=target,thinner_percent=thin))
                session.flush();self._current_id=orm.id;session.commit()
            self.reload();self.list_systems.setCurrentIndex(self.list_systems.findData(self._current_id));self.systems_changed.emit()
        except Exception as exc:QMessageBox.critical(self,"Ошибка сохранения",str(exc))
    def _delete_system(self):
        if self._current_id is None:return
        if QMessageBox.question(self,"Удаление",f"Удалить систему «{self.ed_name.text().strip()}»?")!=QMessageBox.Yes:return
        try:
            with get_session_factory()() as session:CoatingSystemRepository(session).delete(self._current_id,soft=True);session.commit()
            self._current_id=None;self.reload();self.systems_changed.emit()
        except Exception as exc:QMessageBox.critical(self,"Ошибка удаления",str(exc))
