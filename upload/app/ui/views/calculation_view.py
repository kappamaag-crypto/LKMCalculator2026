"""Экран расчёта системы покрытия."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QLineEdit,QDoubleSpinBox,QComboBox,QPushButton,QMessageBox,QTextEdit,QSplitter,QFileDialog,QDialog
from PySide6.QtCore import Qt,Signal,QTimer
from app.domain.models import Material,ObjectData,CoatingSystem
from app.domain.enums import MaterialType
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.services.snapshot_service import material_from_snapshot, thinner_from_snapshot
from app.services.snapshot_utils import snapshot_number
from app.ui.widgets.layer_table import LayerTableWidget
from app.ui.dialogs.ad_hoc_material_dialog import AdHocMaterialDialog
from app.infrastructure.export.customer_excel_exporter import CustomerExcelExporter
from app.infrastructure.export.pdf_exporter import PDFExporter
from app.config import AppSettings

class CalculationView(QWidget):
    calculation_done=Signal(object);add_to_comparison=Signal(object);material_added=Signal(object)
    def __init__(self,service:CalculationService,parent=None):
        super().__init__(parent);self.service=service;self.settings=AppSettings.load();self._materials=[];self._all_materials=[];self._systems=[];self._last_result=None;self._restored_system_name="";self._area_unknown=False;self._timer=QTimer(self);self._timer.setSingleShot(True);self._timer.setInterval(220);self._timer.timeout.connect(self._on_live_recalculate);self._build_ui()
    def set_settings(self,settings:AppSettings):
        self.settings=settings
    def _build_ui(self):
        root=QVBoxLayout(self);root.setContentsMargins(12,12,12,12);root.setSpacing(10);t=QLabel("Расчёт системы покрытия");t.setProperty("heading",True);root.addWidget(t);sp=QSplitter(Qt.Horizontal)
        left=QWidget();ll=QVBoxLayout(left);b=QGroupBox("Объект");f=QFormLayout(b);self.ed_object=QLineEdit();self.ed_customer=QLineEdit();self.ed_project=QLineEdit();self.ed_calc_number=QLineEdit();self.ed_system_name=QLineEdit();self.ed_system_name.setPlaceholderText("Название системы");self.spin_area=QDoubleSpinBox();self.spin_area.setRange(0.01,1000000);self.spin_area.setValue(1);self.spin_area.setDecimals(2);self.spin_area.setSuffix(" м²")
        f.addRow("Объект:",self.ed_object);f.addRow("Заказчик:",self.ed_customer);f.addRow("Проект:",self.ed_project);f.addRow("№ расчёта:",self.ed_calc_number);f.addRow("Система:",self.ed_system_name);f.addRow("Площадь:",self.spin_area);self.spin_area.valueChanged.connect(self._on_area_changed)
        sysbox=QGroupBox("Сохранённая система");sf=QVBoxLayout(sysbox);self.cmb_system=QComboBox();self.cmb_system.addItem("— выбрать систему из базы —",None);self.btn_load_system=QPushButton("Загрузить систему в расчёт");self.btn_load_system.clicked.connect(self._on_load_saved_system);sf.addWidget(self.cmb_system);sf.addWidget(self.btn_load_system);ll.addWidget(b);ll.addWidget(sysbox);ll.addStretch();sp.addWidget(left)
        right=QWidget();rl=QVBoxLayout(right);lb=QGroupBox("Слои системы");al=QVBoxLayout(lb);row=QHBoxLayout();self.cmb_material=QComboBox();self.cmb_material.setMinimumWidth(240);add=QPushButton("Добавить слой");add.clicked.connect(self._on_add_layer);add_material=QPushButton("+ Материал");add_material.setToolTip("Добавить материал прямо в текущий расчёт и сохранить его в БД");add_material.clicked.connect(self._on_add_material);rem=QPushButton("Удалить");rem.setProperty("secondary",True);rem.clicked.connect(self._on_remove_layer);clr=QPushButton("Очистить");clr.setProperty("secondary",True);clr.clicked.connect(self._on_clear_layers)
        for x in (QLabel("Материал:"),self.cmb_material,add,add_material,rem,clr):row.addWidget(x)
        row.addStretch();al.addLayout(row);h=QLabel("Материал можно выбрать из базы или добавить прямо здесь. После добавления параметры DFT, потери, разбавитель и цена редактируются непосредственно в строке. Результаты обновляются автоматически.");h.setWordWrap(True);h.setProperty("subheading",True);al.addWidget(h);self.layer_table=LayerTableWidget();self.layer_table.layer_changed.connect(self._schedule_live_recalculate);al.addWidget(self.layer_table);rl.addWidget(lb)
        buttons=QHBoxLayout();self.btn_calc=QPushButton("Рассчитать");self.btn_calc.clicked.connect(self._on_calculate);self.btn_demo=QPushButton("Демо-система");self.btn_demo.setProperty("secondary",True);self.btn_demo.clicked.connect(self._on_load_demo);self.btn_excel=QPushButton("Excel");self.btn_excel.setProperty("secondary",True);self.btn_excel.clicked.connect(self._on_export_excel);self.btn_excel.setEnabled(False);self.btn_pdf=QPushButton("PDF");self.btn_pdf.setProperty("secondary",True);self.btn_pdf.clicked.connect(self._on_export_pdf);self.btn_pdf.setEnabled(False);self.btn_to_cmp=QPushButton("Добавить в сравнение");self.btn_to_cmp.setProperty("secondary",True);self.btn_to_cmp.clicked.connect(self._on_to_comparison);self.btn_to_cmp.setEnabled(False)
        for x in (self.btn_calc,self.btn_demo,self.btn_excel,self.btn_pdf,self.btn_to_cmp):buttons.addWidget(x)
        buttons.addStretch();rl.addLayout(buttons);rb=QGroupBox("Результат");rr=QVBoxLayout(rb);self.lbl_summary=QLabel("Выполните расчёт");self.lbl_summary.setProperty("subheading",True);self.lbl_summary.setWordWrap(True);self.txt_details=QTextEdit();self.txt_details.setReadOnly(True);self.txt_details.setMaximumHeight(210);rr.addWidget(self.lbl_summary);rr.addWidget(self.txt_details);rl.addWidget(rb);sp.addWidget(right);sp.setStretchFactor(0,1);sp.setStretchFactor(1,2);root.addWidget(sp)
    def _on_area_changed(self):self._area_unknown=False;self._schedule_live_recalculate()
    def set_materials(self,materials:list):
        self._all_materials=list(materials);self._materials=[m for m in materials if m.material_type!=MaterialType.THINNER];self.cmb_material.clear();[self.cmb_material.addItem(m.display_name(),m) for m in self._materials];self._refresh_systems()
    def _on_add_material(self):
        dialog=AdHocMaterialDialog(self)
        if dialog.exec()!=QDialog.Accepted:return
        material=dialog.material()
        if material is None:return
        self._all_materials=[m for m in self._all_materials if m.id!=material.id];self._materials=[m for m in self._materials if m.id!=material.id]
        if material.material_type!=MaterialType.THINNER:
            self._all_materials.append(material);self._materials.append(material);self.cmb_material.addItem(material.display_name(),material);self.cmb_material.setCurrentIndex(self.cmb_material.count()-1)
            default_dft=material.recommended_dft_min if material.recommended_dft_min is not None and material.recommended_dft_min>0 else 100
            self.layer_table.add_layer(LayerInput(material=material,target_dft=default_dft,losses_percent=self.settings.default_losses_percent,thinner_percent=0))
        self.material_added.emit(material);self.status_message(f"Материал «{material.display_name()}» сохранён в БД и автоматически добавлен в текущий расчёт")
    def set_systems(self,systems:list[CoatingSystem]):self._systems=list(systems or []);self._refresh_systems()
    def _refresh_systems(self):
        if not hasattr(self,'cmb_system'):return
        current=self.cmb_system.currentData() if self.cmb_system.count() else None;self.cmb_system.blockSignals(True);self.cmb_system.clear();self.cmb_system.addItem("— выбрать систему из базы —",None)
        for system in self._systems:self.cmb_system.addItem(system.system_name or f"Система #{system.id or ''}",system)
        if current is not None:
            idx=self.cmb_system.findData(current)
            if idx>=0:self.cmb_system.setCurrentIndex(idx)
        self.cmb_system.blockSignals(False)
    def _on_load_saved_system(self):
        system=self.cmb_system.currentData()
        if system is None:QMessageBox.warning(self,"Система","Выберите сохранённую систему из базы данных");return
        missing=[];layers=[]
        for ld in sorted(system.layers,key=lambda x:x.layer_number):
            material=ld.material
            if material is None:missing.append(f"слой №{ld.layer_number}");continue
            target=ld.target_dft if ld.target_dft is not None else ld.dft_min
            if target is None:missing.append(f"DFT слоя №{ld.layer_number}");continue
            thinner=None
            if ld.thinner_material_id:thinner=next((m for m in self._all_materials if m.id==ld.thinner_material_id),None)
            layers.append(LayerInput(material=material,target_dft=target,losses_percent=ld.losses_percent if ld.losses_percent is not None else self.settings.default_losses_percent,thinner_percent=ld.thinner_percent or 0,thinner=thinner,thinner_basis=ld.thinner_basis))
        if not layers:QMessageBox.warning(self,"Система","В выбранной системе нет пригодных для расчёта слоёв");return
        self._timer.stop();self.layer_table.clear_layers();[self.layer_table.add_layer(x) for x in layers];self.ed_system_name.setText(system.system_name);self._restored_system_name=system.system_name;self._last_result=None;[b.setEnabled(False) for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp)]
        ok=self._recalculate(False,False)
        if missing:QMessageBox.warning(self,"Система загружена не полностью","Не удалось восстановить: "+", ".join(missing))
        if ok:self.status_message(f"Загружена система «{system.system_name}» и пересчитана под текущую площадь")
    def status_message(self,text):
        parent=self.window()
        if hasattr(parent,'statusBar'):parent.statusBar().showMessage(text,10000)
    def _current_material(self)->Optional[object]:return self.cmb_material.currentData()
    def _build_object_data(self):return ObjectData(object_name=self.ed_object.text().strip(),customer=self.ed_customer.text().strip(),project=self.ed_project.text().strip(),calculation_number=self.ed_calc_number.text().strip(),area_m2=None if self._area_unknown else self.spin_area.value())
    def _build_system(self)->CoatingSystem:return CoatingSystem(system_name=self.ed_system_name.text().strip() or self._restored_system_name or "Пользовательская система")
    def _on_add_layer(self):
        m=self._current_material()
        if m is None:QMessageBox.warning(self,"Внимание","Выберите материал");return
        default_dft=m.recommended_dft_min if m.recommended_dft_min is not None and m.recommended_dft_min>0 else 100;self.layer_table.add_layer(LayerInput(material=m,target_dft=default_dft,losses_percent=self.settings.default_losses_percent,thinner_percent=0))
    def _on_remove_layer(self):self.layer_table.remove_selected()
    def _on_clear_layers(self):
        self._timer.stop();self.layer_table.clear_layers();self.lbl_summary.setText("Выполните расчёт");self.txt_details.clear();self._last_result=None;self._restored_system_name="";self.ed_system_name.clear();[b.setEnabled(False) for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp)]
    def _on_load_demo(self):
        if len(self._materials)<2:self.set_materials(self._materials)
        if len(self._materials)<2:return
        p=self._materials[0];f=self._materials[1];self.layer_table.clear_layers();self.layer_table.add_layer(LayerInput(material=p,target_dft=200,losses_percent=self.settings.default_losses_percent));self.layer_table.add_layer(LayerInput(material=f,target_dft=80,losses_percent=self.settings.default_losses_percent));self.ed_object.setText("Резервуар РВС-1000 (демо)");self.ed_customer.setText("ООО Пример");self.ed_system_name.setText("Blank Universal + Finish");self.spin_area.setValue(1250);self._area_unknown=False;self._restored_system_name="Blank Universal + Finish";self._recalculate(False,False)
    def _schedule_live_recalculate(self):
        if self.layer_table.rowCount():self._timer.start()
    @staticmethod
    def _money(v,dec=2):return "—" if v is None else f"{v:,.{dec}f}".replace(","," ")
    @staticmethod
    def _snapshot_number(value):return snapshot_number(value)
    def _recalculate(self,dialogs=False,notify=False):
        layers=self.layer_table.get_layer_inputs()
        if not layers:
            if dialogs:QMessageBox.warning(self,"Внимание","Добавьте хотя бы один слой")
            return False
        try:result,validation=self.service.calculate_system(self._build_object_data(),layers,system=self._build_system())
        except (ValueError,TypeError) as e:self.lbl_summary.setText(f"Ошибка расчёта: {e}");self.txt_details.clear();return False
        if validation.has_errors:
            msg="\n".join(f"• {e.message}" for e in validation.errors);self.lbl_summary.setText("Расчёт требует исправления входных данных");self.txt_details.setPlainText(msg);[b.setEnabled(False) for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp)];return False
        self._last_result=result;area=result.object_data.area_m2;object_paint_l=result.total_practical_consumption_l*area;object_paint_kg=result.total_practical_consumption_kg*area;self.layer_table.set_layers(layers,result.layers);self.lbl_summary.setText(f"Толщина: {result.total_dft:.0f} мкм | ЛКМ: {result.total_practical_consumption_l:.4f} л/м² / {result.total_practical_consumption_kg:.3f} кг/м² | На объект: {object_paint_l:.2f} л / {object_paint_kg:.2f} кг | Стоимость: {self._money(result.total_cost_per_m2)} руб/м² | Объект: {self._money(result.total_cost,0)} руб");self.txt_details.setPlainText(self.service.format_summary(result));[b.setEnabled(True) for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp)]
        if notify:self.calculation_done.emit(result)
        return True
    def _on_live_recalculate(self):self._recalculate(False,False)
    def _on_calculate(self):self._recalculate(True,True)
    def _on_to_comparison(self):
        if self._last_result is None:
            if not self._recalculate(True,True):return
        self.add_to_comparison.emit(self._last_result)
    def restore_snapshot(self,snapshot:dict)->bool:
        if not isinstance(snapshot,dict):raise ValueError("Некорректный формат снимка истории")
        obj=snapshot.get("object") or {};self._timer.stop();self.ed_object.setText(str(obj.get("object_name") or ""));self.ed_customer.setText(str(obj.get("customer") or ""));self.ed_project.setText(str(obj.get("project") or ""));self.ed_calc_number.setText(str(obj.get("calculation_number") or ""));area=snapshot_number(obj.get("area_m2"));self.spin_area.setValue(area if area is not None and area>=0.01 else 0.01);self._area_unknown=area is None or area<0.01;self._restored_system_name=str(snapshot.get("system_name") or "Пользовательская система");self.ed_system_name.setText(self._restored_system_name);materials_by_id={m.id:m for m in self._all_materials if m.id is not None};materials_by_name={m.material_name:m for m in self._all_materials if m.material_name};layers=[];missing=[]
        for index,item in enumerate(snapshot.get("layers") or [],1):
            current=materials_by_id.get(item.get("material_id")) or materials_by_name.get(item.get("material_name"));material=material_from_snapshot(item,current);thinner=None;thinner_percent=snapshot_number(item.get("thinner_percent") if "thinner_percent" in item else 0)
            if thinner_percent and thinner_percent>0:thinner=thinner_from_snapshot(item,materials_by_id.get(item.get("thinner_id")) or materials_by_name.get(item.get("thinner_name")))
            target_dft=snapshot_number(item.get("target_dft"));losses_percent=snapshot_number(item.get("losses_percent") if "losses_percent" in item else self.settings.default_losses_percent)
            if target_dft is None:missing.append(f"DFT слоя №{index}")
            layers.append(LayerInput(material=material,target_dft=target_dft,losses_percent=losses_percent,thinner_percent=thinner_percent or 0,thinner=thinner,thinner_basis=item.get("thinner_basis")))
        self.layer_table.clear_layers();[self.layer_table.add_layer(x) for x in layers];self._last_result=None;[b.setEnabled(False) for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp)];return self._recalculate(False,False)
    def _default_export_name(self,ext):
        name=self._last_result.object_data.object_name.strip() if self._last_result else "Расчёт_ЛКМ_АКЗ"
        for ch in '<>:"/\\|?*':name=name.replace(ch,"_")
        return f"{name}.{ext}"
    def _export_initial_path(self,ext):
        export_dir=Path(self.settings.export_dir).expanduser() if self.settings.export_dir else Path.home()/"Documents"/"LKM_Calculations"
        try:export_dir.mkdir(parents=True,exist_ok=True)
        except OSError:export_dir=Path.home()
        return str(export_dir/self._default_export_name(ext))
    def _on_export_excel(self):
        if self._last_result is None:return
        path,_=QFileDialog.getSaveFileName(self,"Сохранить расчёт в Excel",self._export_initial_path("xlsx"),"Excel (*.xlsx)")
        if not path:return
        try:CustomerExcelExporter(self.settings).export_calculation(self._last_result,Path(path));QMessageBox.information(self,"Экспорт","Расчёт успешно сохранён в Excel")
        except Exception as e:QMessageBox.critical(self,"Ошибка экспорта Excel",str(e))
    def _on_export_pdf(self):
        if self._last_result is None:return
        path,_=QFileDialog.getSaveFileName(self,"Сохранить расчёт в PDF",self._export_initial_path("pdf"),"PDF (*.pdf)")
        if not path:return
        try:PDFExporter(self.settings).export_calculation(self._last_result,Path(path));QMessageBox.information(self,"Экспорт","Расчёт успешно сохранён в PDF")
        except Exception as e:QMessageBox.critical(self,"Ошибка экспорта PDF",str(e))