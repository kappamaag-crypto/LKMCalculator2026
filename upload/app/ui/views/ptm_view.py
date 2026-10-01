"""PTM / fire-protection engineering calculator view."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.ptm import (
    HeatingMode,
    PTMCalculationInput,
    PTMProfileType,
    calculate,
    list_profiles,
    list_standards,
)


class PTMView(QWidget):
    calculation_done = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("ПТМ / Огнезащита металлоконструкций")
        title.setProperty("heading", True)
        root.addWidget(title)

        note = QLabel(
            "Расчёт приведённой толщины металла: F / P. "
            "Профиль, стандарт и режим обогрева выбираются отдельно."
        )
        note.setWordWrap(True)
        note.setProperty("subheading", True)
        root.addWidget(note)

        form_box = QGroupBox("Параметры профиля")
        form = QFormLayout(form_box)

        self.cmb_type = QComboBox()
        for value in PTMProfileType:
            self.cmb_type.addItem(value.value, value)
        self.cmb_type.currentIndexChanged.connect(self._refresh_profiles)

        self.cmb_standard = QComboBox()
        self.cmb_standard.currentIndexChanged.connect(self._refresh_profiles)

        self.cmb_profile = QComboBox()
        self.cmb_profile.currentIndexChanged.connect(self._profile_changed)

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

        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(0.01, 1000000.0)
        self.spin_length.setDecimals(3)
        self.spin_length.setValue(1.0)
        self.spin_length.setSuffix(" м")

        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 1000000)
        self.spin_quantity.setValue(1)

        form.addRow("Тип:", self.cmb_type)
        form.addRow("Стандарт:", self.cmb_standard)
        form.addRow("Профиль:", self.cmb_profile)
        form.addRow("Обогрев:", self.cmb_heating)
        form.addRow("Пользовательский P:", self.spin_custom_perimeter)
        form.addRow("Длина:", self.spin_length)
        form.addRow("Количество:", self.spin_quantity)

        root.addWidget(form_box)

        profile_box = QGroupBox("Справочные данные")
        profile_layout = QVBoxLayout(profile_box)
        self.lbl_geometry = QLabel("—")
        self.lbl_geometry.setWordWrap(True)
        profile_layout.addWidget(self.lbl_geometry)

        root.addWidget(profile_box)

        result_box = QGroupBox("Результат")
        result_layout = QFormLayout(result_box)
        self.lbl_ptm = QLabel("—")
        self.lbl_area = QLabel("—")
        self.lbl_perimeter = QLabel("—")
        self.lbl_surface_m = QLabel("—")
        self.lbl_surface_t = QLabel("—")
        self.lbl_total_surface = QLabel("—")
        self.lbl_total_mass = QLabel("—")
        result_layout.addRow("ПТМ:", self.lbl_ptm)
        result_layout.addRow("Площадь сечения:", self.lbl_area)
        result_layout.addRow("Обогреваемый периметр:", self.lbl_perimeter)
        result_layout.addRow("Площадь поверхности / 1 м:", self.lbl_surface_m)
        result_layout.addRow("Площадь поверхности / 1 т:", self.lbl_surface_t)
        result_layout.addRow("Площадь на весь объём:", self.lbl_total_surface)
        result_layout.addRow("Масса на весь объём:", self.lbl_total_mass)
        root.addWidget(result_box)

        buttons = QHBoxLayout()
        self.btn_calc = QPushButton("Рассчитать")
        self.btn_calc.clicked.connect(self._calculate)
        buttons.addWidget(self.btn_calc)
        buttons.addStretch()
        root.addLayout(buttons)

        self.txt_source = QTextEdit()
        self.txt_source.setReadOnly(True)
        self.txt_source.setMaximumHeight(100)
        root.addWidget(self.txt_source)

    def _populate(self):
        self.cmb_standard.blockSignals(True)
        self.cmb_standard.clear()
        for standard in list_standards():
            self.cmb_standard.addItem(standard, standard)
        self.cmb_standard.blockSignals(False)
        self._refresh_profiles()

    def _refresh_profiles(self):
        profile_type = self.cmb_type.currentData()
        standard = self.cmb_standard.currentData()
        rows = list_profiles(standard=standard, profile_type=profile_type)
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for row in rows:
            self.cmb_profile.addItem(row.name, row)
        self.cmb_profile.blockSignals(False)
        self._profile_changed()

    def _profile_changed(self):
        profile = self.cmb_profile.currentData()
        if profile is None:
            self.lbl_geometry.setText("Для выбранного типа/стандарта пока нет загруженных профилей.")
            self.txt_source.clear()
            return
        parts = [
            f"F = {profile.area_cm2:g} см²",
            f"масса = {profile.mass_kg_per_m:g} кг/м" if profile.mass_kg_per_m else "масса = UNKNOWN",
        ]
        if profile.height_mm is not None:
            parts.append(f"h = {profile.height_mm:g} мм")
        if profile.width_mm is not None:
            parts.append(f"b = {profile.width_mm:g} мм")
        if profile.web_thickness_mm is not None:
            parts.append(f"tw = {profile.web_thickness_mm:g} мм")
        if profile.flange_thickness_mm is not None:
            parts.append(f"tf = {profile.flange_thickness_mm:g} мм")
        self.lbl_geometry.setText(" | ".join(parts))
        self.txt_source.setPlainText(
            f"Источник: {profile.source or 'UNKNOWN'}\n{profile.notes}".strip()
        )

    def _mode_changed(self):
        self.spin_custom_perimeter.setEnabled(
            self.cmb_heating.currentData() == HeatingMode.CUSTOM
        )

    def _calculate(self):
        profile = self.cmb_profile.currentData()
        mode = self.cmb_heating.currentData()
        if profile is None or mode is None:
            return
        try:
            result = calculate(
                PTMCalculationInput(
                    profile=profile,
                    heating_mode=mode,
                    heated_perimeter_mm=(
                        self.spin_custom_perimeter.value()
                        if mode == HeatingMode.CUSTOM
                        else None
                    ),
                    length_m=self.spin_length.value(),
                    quantity=self.spin_quantity.value(),
                )
            )
        except ValueError as exc:
            self.lbl_ptm.setText("UNKNOWN")
            self.txt_source.append(f"Ошибка: {exc}")
            return

        self.lbl_ptm.setText(f"{result.ptm_mm:.3f} мм")
        self.lbl_area.setText(f"{result.section_area_cm2:.3f} см²")
        self.lbl_perimeter.setText(f"{result.heated_perimeter_mm:.2f} мм")
        self.lbl_surface_m.setText(f"{result.surface_m2_per_m:.4f} м²/м")
        self.lbl_surface_t.setText(
            "UNKNOWN" if result.surface_m2_per_t is None
            else f"{result.surface_m2_per_t:.3f} м²/т"
        )
        self.lbl_total_surface.setText(f"{result.total_surface_m2:.3f} м²")
        self.lbl_total_mass.setText(
            "UNKNOWN" if result.total_mass_kg is None
            else f"{result.total_mass_kg:.3f} кг"
        )
        self.calculation_done.emit(result)
