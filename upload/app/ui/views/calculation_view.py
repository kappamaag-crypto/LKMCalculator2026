"""Экран расчёта системы покрытия."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QLineEdit,QDoubleSpinBox,QComboBox,QPushButton,QMessageBox,QTextEdit,QSplitter,QFileDialog
from PySide6.QtCore import Qt,Signal,QTimer
from app.domain.models import Material,ObjectData
from app.domain.enums import MaterialType,BinderType
from app.domain.calculator import LayerInput
from app.services.calculation_service import CalculationService
from app.ui.widgets.layer_table import LayerTableWidget
from app.infrastructure.export.customer_excel_exporter import CustomerExcelExporter
from app.infrastructure.export.pdf_exporter import PDFExporter
from app.config import AppSettings

class CalculationView(QWidget):
    calculation_done=Signal(object)
    def __init__(self,service:CalculationService,parent=None):
        super().__init__(parent); self.service=service; self._materials=[]; self._last_result=None; self._timer=QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(220); self._timer.timeout.connect(self._on_live_recalculate); self._build_ui()
    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(12,12,12,12); root.setSpacing(10); t=QLabel('Расчёт системы покрытия'); t.setProperty('heading',True); root.addWidget(t); sp=QSplitter(Qt.Horizontal)
        left=QWidget(); ll=QVBoxLayout(left); b=QGroupBox('Объект'); f=QFormLayout(b); self.ed_object=QLineEdit(); self.ed_object.setPlaceholderText('Название объекта'); self.ed_customer=QLineEdit(); self.ed_customer.setPlaceholderText('Заказчик'); self.spin_area=QDoubleSpinBox(); self.spin_area.setRange(0,1000000); self.spin_area.setValue(1); self.spin_area.setDecimals(2); self.spin_area.setSuffix(' м²'); f.addRow('Объект:',self.ed_object); f.addRow('Заказчик:',self.ed_customer); f.addRow('Площадь:',self.spin_area); self.spin_area.valueChanged.connect(self._schedule_live_recalculate); ll.addWidget(b); ll.addStretch(); sp.addWidget(left)
        right=QWidget(); rl=QVBoxLayout(right); lb=QGroupBox('Слои системы'); al=QVBoxLayout(lb); row=QHBoxLayout(); self.cmb_material=QComboBox(); self.cmb_material.setMinimumWidth(240); add=QPushButton('Добавить слой'); add.clicked.connect(self._on_add_layer); rem=QPushButton('Удалить'); rem.setProperty('secondary',True); rem.clicked.connect(self._on_remove_layer); clr=QPushButton('Очистить'); clr.setProperty('secondary',True); clr.clicked.connect(self._on_clear_layers)
        for x in (QLabel('Материал:'),self.cmb_material,add,rem,clr):row.addWidget(x)
        row.addStretch(); al.addLayout(row); h=QLabel('После добавления параметры DFT, потери, разбавитель и цена редактируются непосредственно в строке. Результаты обновляются автоматически.'); h.setWordWrap(True); h.setProperty('subheading',True); al.addWidget(h); self.layer_table=LayerTableWidget(); self.layer_table.layer_changed.connect(self._schedule_live_recalculate); al.addWidget(self.layer_table); rl.addWidget(lb)
        buttons=QHBoxLayout(); self.btn_calc=QPushButton('Рассчитать'); self.btn_calc.clicked.connect(self._on_calculate); self.btn_demo=QPushButton('Демо-система'); self.btn_demo.setProperty('secondary',True); self.btn_demo.clicked.connect(self._on_load_demo); self.btn_excel=QPushButton('Excel'); self.btn_excel.setProperty('secondary',True); self.btn_excel.clicked.connect(self._on_export_excel); self.btn_excel.setEnabled(False); self.btn_pdf=QPushButton('PDF'); self.btn_pdf.setProperty('secondary',True); self.btn_pdf.clicked.connect(self._on_export_pdf); self.btn_pdf.setEnabled(False); self.btn_to_cmp=QPushButton('В сравнение'); self.btn_to_cmp.setProperty('secondary',True); self.btn_to_cmp.clicked.connect(self._on_to_comparison); self.btn_to_cmp.setEnabled(False)
        for x in (self.btn_calc,self.btn_demo,self.btn_excel,self.btn_pdf,self.btn_to_cmp):buttons.addWidget(x)
        buttons.addStretch(); rl.addLayout(buttons); rb=QGroupBox('Результат'); rr=QVBoxLayout(rb); self.lbl_summary=QLabel('Выполните расчёт'); self.lbl_summary.setProperty('subheading',True); self.lbl_summary.setWordWrap(True); self.txt_details=QTextEdit(); self.txt_details.setReadOnly(True); self.txt_details.setMaximumHeight(180); rr.addWidget(self.lbl_summary); rr.addWidget(self.txt_details); rl.addWidget(rb); sp.addWidget(right); sp.setStretchFactor(0,1); sp.setStretchFactor(1,2); root.addWidget(sp)
    def set_materials(self,materials:list[Material]):
        self._materials=[m for m in materials if m.material_type!=MaterialType.THINNER]; self.cmb_material.clear()
        for m in self._materials:self.cmb_material.addItem(m.display_name(),m)
    def _current_material(self)->Optional[Material]:return self.cmb_material.currentData()
    def _build_object_data(self):
        return ObjectData(object_name=self.ed_object.text().strip(),customer=self.ed_customer.text().strip(),area_m2=self.spin_area.value())
    def _on_add_layer(self):
        m=self._current_material()
        if m is None:QMessageBox.warning(self,'Внимание','Выберите материал'); return
        default_dft=m.recommended_dft_min if m.recommended_dft_min is not None and m.recommended_dft_min>0 else 100
        self.layer_table.add_layer(LayerInput(material=m,target_dft=default_dft,losses_percent=0,thinner_percent=0))
    def _on_remove_layer(self):self.layer_table.remove_selected()
    def _on_clear_layers(self):
        self._timer.stop(); self.layer_table.clear_layers(); self.lbl_summary.setText('Выполните расчёт'); self.txt_details.clear(); self._last_result=None
        for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp):b.setEnabled(False)
    def _on_load_demo(self):
        if len(self._materials)<2:
            p=Material(manufacturer='Blank',brand='Blank',material_name='Грунт-Эмаль Blank Universal',material_type=MaterialType.PRIMER_ENAMEL,binder_type=BinderType.EPOXY,density=1.4,solids_percent=73,price_per_kg=552,recommended_dft_min=100,recommended_dft_max=200); f=Material(manufacturer='Blank',brand='Blank',material_name='Эмаль Blank Finish',material_type=MaterialType.FINISH,binder_type=BinderType.POLYURETHANE,density=1.3,solids_percent=58,price_per_kg=892,recommended_dft_min=60,recommended_dft_max=100); self.set_materials([p,f])
        else:p=self._materials[0]; f=self._materials[1] if len(self._materials)>1 else p
        self.layer_table.clear_layers(); self.layer_table.add_layer(LayerInput(material=p,target_dft=200,losses_percent=5)); self.layer_table.add_layer(LayerInput(material=f,target_dft=80,losses_percent=5)); self.ed_object.setText('Резервуар РВС-1000 (демо)'); self.ed_customer.setText('ООО Пример'); self.spin_area.setValue(1250)
    def _schedule_live_recalculate(self):
        if self.layer_table.rowCount():self._timer.start()
    @staticmethod
    def _money(v,dec=2):return '—' if v is None else f'{v:,.{dec}f}'.replace(',',' ')
    def _recalculate(self,dialogs=False,notify=False):
        layers=self.layer_table.get_layer_inputs()
        if not layers:
            if dialogs:QMessageBox.warning(self,'Внимание','Добавьте хотя бы один слой')
            return False
        try:result,validation=self.service.calculate_system(self._build_object_data(),layers)
        except (ValueError,TypeError) as e:
            self.lbl_summary.setText(f'Ошибка расчёта: {e}'); self.txt_details.clear()
            if dialogs:QMessageBox.critical(self,'Ошибка расчёта',str(e))
            return False
        if validation.has_errors:
            msg='\n'.join(f'• {e.message}' for e in validation.errors); self.lbl_summary.setText('Расчёт требует исправления входных данных'); self.txt_details.setPlainText(msg)
            for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp):b.setEnabled(False)
            if dialogs:QMessageBox.critical(self,'Ошибки валидации',msg)
            return False
        self._last_result=result; self.layer_table.set_layers(layers,result.layers); self.lbl_summary.setText(f'Толщина: {result.total_dft:.0f} мкм  |  Расход: {result.total_practical_consumption_l:.4f} л/м² / {result.total_practical_consumption_kg:.3f} кг/м²  |  Стоимость: {self._money(result.total_cost_per_m2)} руб/м²  |  Объект: {self._money(result.total_cost,0)} руб'); self.txt_details.setPlainText(self.service.format_summary(result))
        for b in (self.btn_excel,self.btn_pdf,self.btn_to_cmp):b.setEnabled(True)
        if notify:self.calculation_done.emit(result)
        if validation.has_warnings and dialogs:QMessageBox.warning(self,'Предупреждения','\n'.join(f'• {w.message}' for w in validation.warnings))
        return True
    def _on_live_recalculate(self):self._recalculate(False,False)
    def _on_calculate(self):self._recalculate(True,True)
    def _default_export_name(self,ext):
        name=self._last_result.object_data.object_name.strip() if self._last_result else 'Расчёт_ЛКМ_АКЗ'
        for ch in '<>:"/\\|?*':name=name.replace(ch,'_')
        return f'{name}.{ext}'
    def _on_export_excel(self):
        if self._last_result is None:QMessageBox.warning(self,'Внимание','Сначала выполните расчёт'); return
        path,_=QFileDialog.getSaveFileName(self,'Сохранить расчёт в Excel',self._default_export_name('xlsx'),'Excel (*.xlsx)')
        if not path:return
        try:CustomerExcelExporter(AppSettings.load()).export_calculation(self._last_result,Path(path)); QMessageBox.information(self,'Экспорт','Расчёт успешно сохранён в Excel')
        except Exception as e:QMessageBox.critical(self,'Ошибка экспорта Excel',str(e))
    def _on_export_pdf(self):
        if self._last_result is None:QMessageBox.warning(self,'Внимание','Сначала выполните расчёт'); return
        path,_=QFileDialog.getSaveFileName(self,'Сохранить расчёт в PDF',self._default_export_name('pdf'),'PDF (*.pdf)')
        if not path:return
        try:PDFExporter().export_calculation(self._last_result,Path(path)); QMessageBox.information(self,'Экспорт','Расчёт успешно сохранён в PDF')
        except Exception as e:QMessageBox.critical(self,'Ошибка экспорта PDF',str(e))
    def _on_to_comparison(self):
        if self._last_result is not None:self.calculation_done.emit(self._last_result)
