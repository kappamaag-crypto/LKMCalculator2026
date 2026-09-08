"""Главное окно приложения."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from app import __version__, __app_name__
from app.domain.models import Material, CoatingSystem, LayerDefinition, ObjectData
from app.domain.enums import (
    MaterialType, BinderType, CorrosionCategory, DurabilityLevel,
    SurfaceType, EnvironmentType,
)
from app.services.calculation_service import CalculationService
from app.services.recommendation_service import RecommendationService
from app.ui.styles import APP_STYLE
from app.ui.views.calculation_view import CalculationView
from app.ui.views.recommendation_view import RecommendationView
from app.ui.views.comparison_view import ComparisonView
from app.ui.views.history_view import HistoryView
from app.ui.views.materials_view import MaterialsView


def _demo_materials() -> list[Material]:
    return [
        Material(
            id=1, manufacturer="Blank", brand="Blank",
            material_name="\u0413\u0440\u0443\u043d\u0442-\u042d\u043c\u0430\u043b\u044c Blank Universal",
            material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY,
            density=1.4, solids_percent=73.0, price_per_kg=552.0,
            recommended_dft_min=100, recommended_dft_max=200, packaging_kg=20.0,
        ),
        Material(
            id=2, manufacturer="Blank", brand="Blank",
            material_name="\u042d\u043c\u0430\u043b\u044c Blank Finish",
            material_type=MaterialType.FINISH, binder_type=BinderType.POLYURETHANE,
            density=1.3, solids_percent=58.0, price_per_kg=892.0,
            recommended_dft_min=60, recommended_dft_max=100, packaging_kg=20.0,
        ),
        Material(
            id=3, manufacturer="Blank", brand="Blank",
            material_name="\u0426\u0438\u043d\u043a\u043e\u043d\u0430\u043f\u043e\u043b\u043d\u0435\u043d\u043d\u044b\u0439 \u0433\u0440\u0443\u043d\u0442",
            material_type=MaterialType.ZINC_RICH, binder_type=BinderType.EPOXY,
            density=2.5, solids_percent=65.0, price_per_kg=1200.0,
            recommended_dft_min=40, recommended_dft_max=80, packaging_kg=25.0,
        ),
        Material(
            id=4, manufacturer="Blank",
            material_name="\u0420\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c \u0443\u043d\u0438\u0432\u0435\u0440\u0441\u0430\u043b\u044c\u043d\u044b\u0439",
            material_type=MaterialType.THINNER, binder_type=BinderType.OTHER,
            density=0.9, solids_percent=0.0, price_per_kg=150.0,
        ),
    ]


def _demo_systems() -> list[CoatingSystem]:
    mats = {m.id: m for m in _demo_materials()}
    return [
        CoatingSystem(
            id=1, system_name="Blank Universal + Finish (C3\u2013C4 Medium)",
            manufacturer="Blank",
            corrosion_categories=[CorrosionCategory.C3, CorrosionCategory.C4],
            durability=DurabilityLevel.MEDIUM,
            surface_types=[SurfaceType.NEW_STEEL],
            environments=[EnvironmentType.OUTDOOR, EnvironmentType.INDUSTRIAL],
            temperature_min=-40, temperature_max=80,
            layers=[
                LayerDefinition(material_id=1, material=mats[1], layer_number=1, target_dft=150),
                LayerDefinition(material_id=2, material=mats[2], layer_number=2, target_dft=80),
            ],
            number_of_layers=2,
        ),
        CoatingSystem(
            id=2, system_name="\u0426\u0438\u043d\u043a + Universal + Finish (C4\u2013C5 High)",
            manufacturer="Blank",
            corrosion_categories=[CorrosionCategory.C4, CorrosionCategory.C5],
            durability=DurabilityLevel.HIGH,
            surface_types=[SurfaceType.NEW_STEEL],
            environments=[EnvironmentType.OUTDOOR, EnvironmentType.INDUSTRIAL, EnvironmentType.MARINE],
            temperature_min=-50, temperature_max=120,
            layers=[
                LayerDefinition(material_id=3, material=mats[3], layer_number=1, target_dft=60),
                LayerDefinition(material_id=1, material=mats[1], layer_number=2, target_dft=150),
                LayerDefinition(material_id=2, material=mats[2], layer_number=3, target_dft=80),
            ],
            number_of_layers=3,
        ),
        CoatingSystem(
            id=3, system_name="\u041e\u0434\u043d\u043e\u0441\u043b\u043e\u0439\u043d\u0430\u044f \u0433\u0440\u0443\u043d\u0442-\u044d\u043c\u0430\u043b\u044c (C2 Low)",
            manufacturer="Blank",
            corrosion_categories=[CorrosionCategory.C2],
            durability=DurabilityLevel.LOW,
            surface_types=[SurfaceType.NEW_STEEL],
            environments=[EnvironmentType.INDOOR],
            temperature_min=-20, temperature_max=40,
            layers=[
                LayerDefinition(material_id=1, material=mats[1], layer_number=1, target_dft=120),
            ],
            number_of_layers=1,
        ),
    ]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(APP_STYLE)

        self.calc_service = CalculationService()
        self.rec_service = RecommendationService()

        self._materials = _demo_materials()
        self._systems = _demo_systems()

        self._build_ui()
        self._load_demo_data()
        self.statusBar().showMessage("\u0413\u043e\u0442\u043e\u0432\u043e. \u0414\u0435\u043c\u043e-\u0434\u0430\u043d\u043d\u044b\u0435 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b.")

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.calc_view = CalculationView(self.calc_service)
        self.rec_view = RecommendationView(self.rec_service)
        self.cmp_view = ComparisonView(self.calc_service)

        self.tabs.addTab(self.calc_view, "\u0420\u0430\u0441\u0447\u0451\u0442")
        self.tabs.addTab(self.rec_view, "\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438")
        self.tabs.addTab(self.cmp_view, "\u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435")

        self.materials_view = MaterialsView(self._materials)
        self.history_view = HistoryView()
        self.tabs.addTab(self.materials_view, "\u0411\u0430\u0437\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432")

        stub_sys = QLabel("\u0420\u0430\u0437\u0434\u0435\u043b \u00ab\u0421\u0438\u0441\u0442\u0435\u043c\u044b\u00bb \u2014 \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440 \u0448\u0430\u0431\u043b\u043e\u043d\u043e\u0432 (\u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435)")
        stub_sys.setAlignment(Qt.AlignCenter)
        stub_sys.setProperty("subheading", True)
        self.tabs.addTab(stub_sys, "\u0421\u0438\u0441\u0442\u0435\u043c\u044b")

        self.tabs.addTab(self.history_view, "\u0418\u0441\u0442\u043e\u0440\u0438\u044f")

        stub_set = QLabel("\u0420\u0430\u0437\u0434\u0435\u043b \u00ab\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438\u00bb \u2014 \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435")
        stub_set.setAlignment(Qt.AlignCenter)
        stub_set.setProperty("subheading", True)
        self.tabs.addTab(stub_set, "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")

        self.calc_view.calculation_done.connect(self._on_calc_done)
        self.materials_view.materials_changed.connect(self._on_materials_changed)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("\u0424\u0430\u0439\u043b")
        act_exit = QAction("\u0412\u044b\u0445\u043e\u0434", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        help_menu = menubar.addMenu("\u0421\u043f\u0440\u0430\u0432\u043a\u0430")
        act_about = QAction("\u041e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

        self.setStatusBar(QStatusBar())

    def _load_demo_data(self) -> None:
        self.calc_view.set_materials(self._materials)
        self.rec_view.set_systems(self._systems)

    def _on_calc_done(self, result) -> None:
        self.statusBar().showMessage(
            f"\u0420\u0430\u0441\u0447\u0451\u0442 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d: {result.total_dft:.0f} \u043c\u043a\u043c, "
            f"{result.total_cost_per_m2:.2f} \u0440\u0443\u0431/\u043c\u00b2, "
            f"\u043e\u0431\u044a\u0435\u043a\u0442 {result.total_cost:,.0f} \u0440\u0443\u0431".replace(",", " "),
            10000,
        )
        self.cmp_view.add_from_calculation(result)
        try:
            self.history_view.save_result(result)
        except Exception:
            pass

    def _on_materials_changed(self, materials: list) -> None:
        self._materials = materials
        self.calc_view.set_materials(materials)
        self.statusBar().showMessage(f"\u0411\u0430\u0437\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0430: {len(materials)} \u0437\u0430\u043f\u0438\u0441\u0435\u0439", 5000)

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "\u041e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435",
            f"<b>{__app_name__}</b> v{__version__}<br><br>"
            "\u041f\u0440\u043e\u0444\u0435\u0441\u0441\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439 \u043a\u0430\u043b\u044c\u043a\u0443\u043b\u044f\u0442\u043e\u0440 \u0440\u0430\u0441\u0445\u043e\u0434\u0430 \u041b\u041a\u041c<br>"
            "\u0438 \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u043e\u0434\u0431\u043e\u0440\u0430 \u0441\u0438\u0441\u0442\u0435\u043c \u0410\u041a\u0417.<br><br>"
            "\u0424\u043e\u0440\u043c\u0443\u043b\u044b \u0440\u0430\u0441\u0447\u0451\u0442\u0430 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u044e\u0442 \u0438\u0441\u0445\u043e\u0434\u043d\u043e\u043c\u0443 \u043a\u0430\u043b\u044c\u043a\u0443\u043b\u044f\u0442\u043e\u0440\u0443.<br>"
            "\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043d\u043e\u0441\u044f\u0442 \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440.",
        )
