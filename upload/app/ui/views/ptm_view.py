"""PTM / fire-protection steel geometry calculator view."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.ptm import (
    HeatingMode,
    PTMCalculationInput,
    PTMProfile,
    PTMProfileType,
)
from app.services.ptm_service import PTMService


class PTMView(QWidget):
    calculation_done = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = PTMService()
        self._dimension_widgets: dict[str, QDoubleSpinBox] = {}
        self._updating = False
        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("ПТМ — приведённая толщина металла")
        title.setProperty("heading", True)
        root.addWidget(title)

        note = QLabel(
            "Сначала выбирается сортамент и профиль. Для табличного профиля "
            "значения площади и массы подставляются автоматически. "
            "Для вариантов «по размерам» размеры вводятся вручную. "
            "Огнезащитный состав на этом этапе не выбирается."
        )
        note.setWordWrap(True)
        note.setProperty("subheading", True)
        root.addWidget(note)

        selector = QGroupBox("Сортамент")
        form = QFormLayout(selector)

        self.cmb_type = QComboBox()
        for profile_type in PTMProfileType:
            self.cmb_type.addItem(profile_type.value, profile_type)
        self.cmb_type.currentIndexChanged.connect(self._refresh_standards)

        self.cmb_standard = QComboBox()
        self.cmb_standard.currentIndexChanged.connect(self._refresh_profiles)

        self.cmb_profile = QComboBox()
        self.cmb_profile.currentIndexChanged.connect(self._profile_changed)

        form.addRow("Тип проката:", self.cmb_type)
        form.addRow("Стандарт:", self.cmb_standard)
        form.addRow("Профиль:", self.cmb_profile)
        root.addWidget(selector)

        geometry = QGroupBox("Геометрия / табличные параметры")
        self.geometry_form = QFormLayout(geometry)
        self.lbl_f = QLabel("—")
        self.lbl_mass = QLabel("—")
        self.lbl_auto_dimensions = QLabel("—")
        self.lbl_auto_dimensions.setWordWrap(True)
        self.geometry_form.addRow("Площадь сечения F:", self.lbl_f)
        self.geometry_form.addRow("Масса:", self.lbl_mass)
        self.geometry_form.addRow("Размеры:", self.lbl_auto_dimensions)

        root.addWidget(geometry)
        self.geometry_box = geometry

        heating = QGroupBox("Обогреваемый периметр")
        hf = QFormLayout(heating)
        self.cmb_heating = QComboBox()
        for mode in (
            HeatingMode.FOUR_SIDES,
            HeatingMode.THREE_SIDES,
            HeatingMode.TWO_SIDES,
            HeatingMode.CUSTOM,
        ):
            self.cmb_heating.addItem(mode.value, mode)
        self.cmb_heating.currentIndexChanged.connect(self._mode_changed)
        self.spin_custom_perimeter = QDoubleSpinBox()
        self.spin_custom_perimeter.setRange(0.01, 100000.0)
        self.spin_custom_perimeter.setDecimals(2)
        self.spin_custom_perimeter.setSuffix(" мм")
        self.spin_custom_perimeter.setEnabled(False)
        self.spin_custom_perimeter.valueChanged.connect(self._auto_calculate)

        hf.addRow("Режим:", self.cmb_heating)
        hf.addRow("P вручную:", self.spin_custom_perimeter)
        root.addWidget(heating)

        manual = QGroupBox("Размеры для ручного ввода")
        self.manual_form = QFormLayout(manual)
        root.addWidget(manual)
        self.manual_box = manual

        dimensions = QGroupBox("Расчётный результат")
        df = QFormLayout(dimensions)
        self.lbl_ptm = QLabel("—")
        self.lbl_area = QLabel("—")
        self.lbl_perimeter = QLabel("—")
        self.lbl_surface_m = QLabel("—")
        self.lbl_surface_t = QLabel("—")
        self.lbl_total_surface = QLabel("—")
        self.lbl_total_mass = QLabel("—")
        df.addRow("Приведённая толщина металла:", self.lbl_ptm)
        df.addRow("Площадь сечения:", self.lbl_area)
        df.addRow("Обогреваемый периметр:", self.lbl_perimeter)
        df.addRow("Площадь поверхности / 1 м:", self.lbl_surface_m)
        df.addRow("Площадь поверхности / 1 т:", self.lbl_surface_t)
        df.addRow("Площадь на весь объём:", self.lbl_total_surface)
        df.addRow("Масса на весь объём:", self.lbl_total_mass)
        root.addWidget(dimensions)

        controls = QHBoxLayout()
        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(0.01, 1_000_000.0)
        self.spin_length.setDecimals(3)
        self.spin_length.setValue(1.0)
        self.spin_length.setSuffix(" м")
        self.spin_length.valueChanged.connect(self._auto_calculate)

        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 1_000_000)
        self.spin_quantity.setValue(1)
        self.spin_quantity.valueChanged.connect(self._auto_calculate)

        controls.addWidget(QLabel("Длина:"))
        controls.addWidget(self.spin_length)
        controls.addWidget(QLabel("Количество:"))
        controls.addWidget(self.spin_quantity)
        self.btn_calc = QPushButton("Рассчитать")
        self.btn_calc.clicked.connect(self._calculate)
        controls.addWidget(self.btn_calc)
        controls.addStretch()
        root.addLayout(controls)

        self.txt_source = QTextEdit()
        self.txt_source.setReadOnly(True)
        self.txt_source.setMaximumHeight(120)
        root.addWidget(self.txt_source)

    def _populate(self):
        self._refresh_standards()

    def _refresh_standards(self):
        profile_type = self.cmb_type.currentData()
        self._updating = True
        self.cmb_standard.blockSignals(True)
        self.cmb_standard.clear()
        for standard in self.service.list_standards(profile_type):
            self.cmb_standard.addItem(standard, standard)
        self.cmb_standard.blockSignals(False)
        self._updating = False
        self._refresh_profiles()

    def _refresh_profiles(self):
        profile_type = self.cmb_type.currentData()
        standard = self.cmb_standard.currentData()
        rows = self.service.list_profiles(standard=standard, profile_type=profile_type)
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for row in rows:
            self.cmb_profile.addItem(row.name, row)
        self.cmb_profile.blockSignals(False)
        if not rows and standard:
            self.cmb_profile.addItem("Ручной ввод размеров", None)
        self._profile_changed()

    def _clear_manual(self):
        while self.manual_form.rowCount():
            self.manual_form.removeRow(0)
        self._dimension_widgets.clear()

    def _add_dimension(self, key: str, label: str, value: float = 0.0):
        w = QDoubleSpinBox()
        w.setRange(0.01, 10000.0)
        w.setDecimals(3)
        w.setValue(value if value > 0 else 1.0)
        w.setSuffix(" мм")
        w.valueChanged.connect(self._auto_calculate)
        self.manual_form.addRow(label, w)
        self._dimension_widgets[key] = w

    def _configure_manual(self):
        self._clear_manual()
        profile_type = self.cmb_type.currentData()
        standard = self.cmb_standard.currentData() or ""

        # Fixed catalog profiles use read-only catalog data.
        if self.cmb_profile.currentData() is not None:
            self.manual_box.setEnabled(False)
            self.manual_box.setTitle("Ручные размеры — не требуются для табличного профиля")
            return

        self.manual_box.setEnabled(True)
        self.manual_box.setTitle("Размеры для ручного ввода")

        if profile_type == PTMProfileType.I_BEAM:
            self._add_dimension("h", "Высота h")
            self._add_dimension("b", "Ширина полки b")
            self._add_dimension("s", "Толщина стенки s")
            self._add_dimension("t", "Толщина полки t")
        elif profile_type == PTMProfileType.CHANNEL:
            self._add_dimension("h", "Высота h")
            self._add_dimension("b", "Ширина полки b")
            self._add_dimension("s", "Толщина стенки s")
            self._add_dimension("t", "Толщина полки t")
        elif profile_type == PTMProfileType.ANGLE:
            self._add_dimension("a", "Полка A")
            self._add_dimension("b", "Полка B")
            self._add_dimension("t", "Толщина t")
        elif profile_type == PTMProfileType.BOX:
            self._add_dimension("h", "Высота h")
            self._add_dimension("b", "Ширина b")
            self._add_dimension("t", "Толщина стенки t")
        elif profile_type == PTMProfileType.PIPE:
            self._add_dimension("d", "Наружный диаметр D")
            self._add_dimension("t", "Толщина стенки t")
        elif profile_type == PTMProfileType.ROUND_BAR:
            self._add_dimension("d", "Диаметр d")
        elif profile_type == PTMProfileType.SHEET:
            self._add_dimension("t", "Толщина листа t")
        self._auto_calculate()

    def _profile_changed(self):
        profile = self.cmb_profile.currentData()
        self._configure_manual()
        if profile is None:
            self.lbl_f.setText("автоматически после ввода размеров")
            self.lbl_mass.setText("автоматически из площади для стали")
            self.lbl_auto_dimensions.setText("Ручной ввод")
            self.txt_source.setPlainText(
                f"Источник сортамента: {self.cmb_standard.currentData() or 'UNKNOWN'}"
            )
            return

        parts = []
        for label, value in (
            ("h", profile.height_mm),
            ("b", profile.width_mm),
            ("s", profile.web_thickness_mm),
            ("t", profile.flange_thickness_mm),
            ("A", profile.leg_a_mm),
            ("B", profile.leg_b_mm),
            ("D", profile.outside_diameter_mm),
            ("d", profile.diameter_mm),
        ):
            if value is not None:
                parts.append(f"{label}={value:g} мм")
        self.lbl_f.setText("UNKNOWN" if profile.area_cm2 is None else f"{profile.area_cm2:g} см²")
        self.lbl_mass.setText(
            "UNKNOWN" if profile.mass_kg_per_m is None else f"{profile.mass_kg_per_m:g} кг/м"
        )
        self.lbl_auto_dimensions.setText(" | ".join(parts) if parts else "Размеры не заданы")
        source = profile.source or "UNKNOWN"
        if profile.source_url:
            source += f"\n{profile.source_url}"
        if profile.notes:
            source += f"\n{profile.notes}"
        self.txt_source.setPlainText(source)
        self._auto_calculate()

    def _mode_changed(self):
        self.spin_custom_perimeter.setEnabled(
            self.cmb_heating.currentData() == HeatingMode.CUSTOM
        )
        self._auto_calculate()

    def _manual_profile(self) -> PTMProfile | None:
        profile_type = self.cmb_type.currentData()
        standard = self.cmb_standard.currentData()
        if profile_type is None or not standard:
            return None

        v = {key: widget.value() for key, widget in self._dimension_widgets.items()}
        return PTMProfile(
            standard=standard,
            profile_type=profile_type,
            name="Ручной профиль",
            area_cm2=None,
            mass_kg_per_m=None,
            height_mm=v.get("h"),
            width_mm=v.get("b"),
            web_thickness_mm=v.get("s"),
            flange_thickness_mm=v.get("t"),
            leg_a_mm=v.get("a"),
            leg_b_mm=v.get("b") if profile_type == PTMProfileType.ANGLE else None,
            wall_thickness_mm=v.get("t"),
            outside_diameter_mm=v.get("d") if profile_type == PTMProfileType.PIPE else None,
            diameter_mm=v.get("d") if profile_type == PTMProfileType.ROUND_BAR else None,
            sheet_thickness_mm=v.get("t") if profile_type == PTMProfileType.SHEET else None,
            source=f"Ручной ввод / {standard}",
            notes="Размеры заданы пользователем. Для ПТМ используется геометрическая модель сечения.",
        )

    def _current_profile(self) -> PTMProfile | None:
        return self.cmb_profile.currentData() or self._manual_profile()

    def _auto_calculate(self):
        if self._updating:
            return
        self._calculate(auto=True)

    def _calculate(self, auto: bool = False):
        profile = self._current_profile()
        mode = self.cmb_heating.currentData()
        if profile is None or mode is None:
            return
        try:
            result = self.service.calculate(
                profile,
                heating_mode=mode,
                heated_perimeter_mm=(
                    self.spin_custom_perimeter.value()
                    if mode == HeatingMode.CUSTOM
                    else None
                ),
                length_m=self.spin_length.value(),
                quantity=self.spin_quantity.value(),
            )
        except ValueError as exc:
            self.lbl_ptm.setText("UNKNOWN")
            self.lbl_area.setText("UNKNOWN")
            self.lbl_perimeter.setText("UNKNOWN")
            self.lbl_surface_m.setText("UNKNOWN")
            self.lbl_surface_t.setText("UNKNOWN")
            if not auto:
                self.txt_source.append(f"Ошибка: {exc}")
            return

        self.lbl_ptm.setText(f"{result.ptm_mm:.3f} мм")
        self.lbl_area.setText(f"{result.section_area_cm2:.3f} см²")
        self.lbl_perimeter.setText(f"{result.heated_perimeter_mm:.2f} мм")
        self.lbl_surface_m.setText(f"{result.surface_m2_per_m:.4f} м²")
        self.lbl_surface_t.setText(
            "UNKNOWN" if result.surface_m2_per_t is None
            else f"{result.surface_m2_per_t:.3f} м²"
        )
        self.lbl_total_surface.setText(f"{result.total_surface_m2:.3f} м²")
        self.lbl_total_mass.setText(f"{result.total_mass_kg:.3f} кг")
        self.calculation_done.emit(result)
