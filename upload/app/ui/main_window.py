"""Главное окно приложения."""
from __future__ import annotations
from PySide6.QtWidgets import QMainWindow,QTabWidget,QStatusBar,QMessageBox,QDialog
from PySide6.QtGui import QAction
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app import __version__,__app_name__
from app.config import AppSettings
from app.domain.models import Material,CoatingSystem,LayerDefinition
from app.domain.enums import MaterialType,BinderType,DurabilityLevel
from app.domain.engineering_context import EngineeringContext
from app.services.calculation_service import CalculationService
from app.services.recommendation_service import RecommendationService
from app.ui.styles import APP_STYLE
from app.ui.views.calculation_view import CalculationView
from app.ui.views.recommendation_view import RecommendationView
from app.ui.views.comparison_view import ComparisonView
from app.ui.views.history_view import HistoryView
from app.ui.views.materials_view import MaterialsView
from app.ui.views.two_component_view import TwoComponentView
from app.ui.views.systems_view import SystemsView
from app.ui.views.settings_view import SettingsView
from app.ui.dialogs.engineering_context_dialog import EngineeringContextDialog
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.repositories import MaterialRepository
from app.infrastructure.database.models import CoatingSystemORM

def _demo_materials():
    return [Material(id=1,manufacturer="Blank",brand="Blank",material_name="Грунт-Эмаль Blank Universal",material_type=MaterialType.PRIMER_ENAMEL,binder_type=BinderType.EPOXY,density=1.4,solids_percent=73,solids_by_volume_percent=73,price_per_kg=552,recommended_dft_min=100,recommended_dft_max=200,packaging_kg=20),Material(id=2,manufacturer="Blank",brand="Blank",material_name="Эмаль Blank Finish",material_type=MaterialType.FINISH,binder_type=BinderType.POLYURETHANE,density=1.3,solids_percent=58,solids_by_volume_percent=58,price_per_kg=892,recommended_dft_min=60,recommended_dft_max=100,packaging_kg=20),Material(id=3,manufacturer="Blank",brand="Blank",material_name="Цинконаполненный грунт",material_type=MaterialType.ZINC_RICH,binder_type=BinderType.EPOXY,density=2.5,solids_percent=65,solids_by_volume_percent=65,price_per_kg=1200,recommended_dft_min=40,recommended_dft_max=80,packaging_kg=25),Material(id=4,manufacturer="Blank",brand="Blank",material_name="Разбавитель универсальный",material_type=MaterialType.THINNER,density=.9,price_per_kg=150)]
def _load_materials_from_db(fallback):
    try:
        with get_session_factory()() as session:materials=MaterialRepository(session).list_all(active_only=True)
        return materials or fallback
    except Exception:return fallback
def _enum_or_none(enum_cls,value):
    if not value:return None
    try:return enum_cls(value)
    except (ValueError,TypeError):return None
def _load_systems_from_db(materials,fallback):
    try:
        material_by_id={m.id:m for m in materials if m.id is not None}
        with get_session_factory()() as session:
            stmt=(select(CoatingSystemORM).options(selectinload(CoatingSystemORM.layers)).where(CoatingSystemORM.is_active.is_(True)).order_by(CoatingSystemORM.system_name))
            rows=session.scalars(stmt).unique().all();systems=[]
            for orm in rows:
                layers=[]
                for layer in sorted(orm.layers,key=lambda x:x.layer_number):
                    material=material_by_id.get(layer.material_id)
                    if material is None:continue
                    layers.append(LayerDefinition(material_id=material.id,material=material,layer_number=layer.layer_number,layer_type=_enum_or_none(MaterialType,layer.layer_type) or MaterialType.OTHER,dft_min=layer.dft_min,dft_max=layer.dft_max,target_dft=layer.target_dft if layer.target_dft is not None else dft_fallback(material),thinner_percent=layer.thinner_percent or 0,thinner_material_id=layer.thinner_material_id,thinner_basis=layer.thinner_basis,losses_percent=None,notes=layer.notes or ""))
                if layers:systems.append(CoatingSystem(id=orm.id,system_name=orm.system_name,manufacturer=orm.manufacturer or "",description=orm.description or "",durability=_enum_or_none(DurabilityLevel,orm.durability),substrate=orm.substrate or "",total_dft_min=orm.total_dft_min,total_dft_target=orm.total_dft_target,total_dft_max=orm.total_dft_max,number_of_layers=len(layers),temperature_min=orm.temperature_min,temperature_max=orm.temperature_max,standards=orm.standards or "",certificate=orm.certificate or "",technical_document=orm.technical_document or "",notes=orm.notes or "",layers=layers))
        return systems or fallback
    except Exception:return fallback
def dft_fallback(material):
    value=getattr(material,"recommended_dft_min",None);return value if value is not None and value>0 else 100
def _demo_systems():
    mats={m.id:m for m in _demo_materials()};return [CoatingSystem(id=1,system_name="Blank Universal + Finish (C3–C4 Medium)",manufacturer="Blank",layers=[LayerDefinition(material_id=1,material=mats[1],layer_number=1,target_dft=150),LayerDefinition(material_id=2,material=mats[2],layer_number=2,target_dft=80)],number_of_layers=2)]
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle(f"{__app_name__} v{__version__}");self.setMinimumSize(1100,700);self.resize(1280,800);self.setStyleSheet(APP_STYLE);self.settings=AppSettings.load();self.calc_service=CalculationService();self.rec_service=RecommendationService();self._materials=_load_materials_from_db(_demo_materials());self._systems=_load_systems_from_db(self._materials,_demo_systems());self._engineering_context=EngineeringContext();self._build_ui();self._load_demo_data();self.statusBar().showMessage("Готово. Материалы и системы загружены из базы данных.")
    def _build_ui(self):
        self.tabs=QTabWidget();self.setCentralWidget(self.tabs);self.calc_view=CalculationView(self.calc_service);self.calc_view.set_settings(self.settings);self.calc_view.set_engineering_context(self._engineering_context);self.rec_view=RecommendationView(self.rec_service);self.cmp_view=ComparisonView(self.calc_service);self.two_component_view=TwoComponentView();self.materials_view=MaterialsView(self._materials);self.history_view=HistoryView();self.systems_view=SystemsView(self._materials);self.settings_view=SettingsView(self.settings)
        self.tabs.addTab(self.calc_view,"Расчёт");self.tabs.addTab(self.rec_view,"Рекомендации");self.tabs.addTab(self.cmp_view,"Сравнение");self.tabs.addTab(self.two_component_view,"2К-информация");self.tabs.addTab(self.materials_view,"База материалов");self.tabs.addTab(self.systems_view,"Системы");self.tabs.addTab(self.history_view,"История");self.tabs.addTab(self.settings_view,"Настройки")
        self.calc_view.calculation_done.connect(self._on_calc_done);self.calc_view.add_to_comparison.connect(self._on_add_to_comparison);self.calc_view.material_added.connect(self._on_material_added_from_calculation);self.materials_view.materials_changed.connect(self._on_materials_changed);self.history_view.load_requested.connect(self._on_history_load);self.systems_view.systems_changed.connect(self._on_systems_changed);self.settings_view.settings_changed.connect(self._on_settings_changed)
        menubar=self.menuBar();file_menu=menubar.addMenu("Файл");act_exit=QAction("Выход",self);act_exit.triggered.connect(self.close);file_menu.addAction(act_exit);engineering_menu=menubar.addMenu("Инженерное");act_context=QAction("Контекст НД и поверхности…",self);act_context.triggered.connect(self._edit_engineering_context);engineering_menu.addAction(act_context);help_menu=menubar.addMenu("Справка");act_about=QAction("О программе",self);act_about.triggered.connect(self._on_about);help_menu.addAction(act_about);self.setStatusBar(QStatusBar())
    def _edit_engineering_context(self):
        dialog=EngineeringContextDialog(self._engineering_context,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:context=dialog.context()
        except ValueError as exc:QMessageBox.warning(self,"Инженерный контекст",str(exc));return
        self._engineering_context=context;self.calc_view.set_engineering_context(context)
        model=context.normative_model
        if model is None:self.statusBar().showMessage("Инженерный контекст обновлён: нормативная модель не выбрана; отсутствующие правила остаются UNKNOWN.",10000)
        else:self.statusBar().showMessage(f"Инженерный контекст обновлён: модель {model.model_id} v{model.version}; правила без источника остаются UNKNOWN.",10000)
    def _load_demo_data(self):self.calc_view.set_materials(self._materials);self.calc_view.set_systems(self._systems);self.rec_view.set_systems(self._systems)
    def _refresh_system_catalog(self):self._systems=_load_systems_from_db(self._materials,_demo_systems());self.calc_view.set_systems(self._systems);self.rec_view.set_systems(self._systems)
    def _on_systems_changed(self):self._refresh_system_catalog();self.statusBar().showMessage(f"Каталог систем обновлён: {len(self._systems)}",5000)
    def _on_settings_changed(self,settings):
        self.settings=settings;self.calc_view.set_settings(settings);self.statusBar().showMessage("Настройки применены к расчёту и экспорту",7000)
    @staticmethod
    def _money(value,decimals=2):return "—" if value is None else f"{value:,.{decimals}f}".replace(","," ")
    def _on_calc_done(self,result):
        self._last_calculation_result=result
        self.systems_view.set_calculation_result(result)
        self.statusBar().showMessage(f"Расчёт выполнен: {result.total_dft:.0f} мкм, {self._money(result.total_cost_per_m2)} руб/м², объект {self._money(result.total_cost,0)} руб",10000)
        try:self.history_view.save_result(result)
        except Exception as exc:self.statusBar().showMessage(f"Не удалось сохранить расчёт в историю: {exc}",10000)
    def _on_add_to_comparison(self,result):self.cmp_view.add_from_calculation(result);self.tabs.setCurrentWidget(self.cmp_view);self.statusBar().showMessage("Система добавлена в сравнение. Добавьте другие варианты и нажмите «Сравнить».",10000)
    def _on_history_load(self,snapshot):
        try:self.calc_view.restore_snapshot(snapshot);self.tabs.setCurrentWidget(self.calc_view);self.statusBar().showMessage("Снимок истории восстановлен и доступен для редактирования.",10000)
        except (TypeError,ValueError,KeyError) as exc:QMessageBox.warning(self,"История",f"Не удалось восстановить снимок: {exc}")
    def _on_material_added_from_calculation(self,material):
        materials=_load_materials_from_db(self._materials);self._on_materials_changed(materials);self.statusBar().showMessage(f"Материал «{material.display_name()}» добавлен в базу и доступен во всех разделах",7000)
    def _on_materials_changed(self,materials):self._materials=materials;self.calc_view.set_materials(materials);self.systems_view.set_materials(materials);self._refresh_system_catalog();self.statusBar().showMessage(f"База материалов обновлена: {len(materials)} записей",5000)
    def _on_about(self):QMessageBox.about(self,"О программе",f"<b>{__app_name__}</b> v{__version__}<br><br>Профессиональный калькулятор расхода ЛКМ<br>и предварительного подбора систем АКЗ.")
