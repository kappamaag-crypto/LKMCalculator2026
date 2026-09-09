"""Полноценная вкладка настроек приложения."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from app.config import AppSettings, DB_PATH, SETTINGS_PATH


class SettingsView(QWidget):
    """Настройки, сохраняемые в data/settings.json."""

    settings_changed = Signal(object)

    def __init__(self, settings: AppSettings | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings or AppSettings.load()
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Настройки")
        title.setProperty("heading", True)
        root.addWidget(title)

        subtitle = QLabel("Общие параметры программы, расчёта и экспорта")
        subtitle.setProperty("subheading", True)
        root.addWidget(subtitle)

        org = QGroupBox("Организация")
        form = QFormLayout(org)
        self.ed_org = QLineEdit()
        self.ed_address = QLineEdit()
        self.ed_phone = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_logo = QLineEdit()
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.ed_logo)
        btn_logo = QPushButton("Выбрать…")
        btn_logo.clicked.connect(self._choose_logo)
        logo_row.addWidget(btn_logo)
        form.addRow("Название:", self.ed_org)
        form.addRow("Адрес:", self.ed_address)
        form.addRow("Телефон:", self.ed_phone)
        form.addRow("E-mail:", self.ed_email)
        form.addRow("Логотип:", logo_row)
        root.addWidget(org)

        calc = QGroupBox("Расчёт и цены")
        form = QFormLayout(calc)
        self.spin_vat = QDoubleSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setDecimals(2)
        self.spin_vat.setSuffix(" %")
        self.chk_vat = QCheckBox("Цены материалов указаны с НДС")
        self.spin_losses = QDoubleSpinBox()
        self.spin_losses.setRange(0, 100)
        self.spin_losses.setDecimals(2)
        self.spin_losses.setSuffix(" %")
        form.addRow("НДС:", self.spin_vat)
        form.addRow("", self.chk_vat)
        form.addRow("Потери по умолчанию:", self.spin_losses)
        root.addWidget(calc)

        export = QGroupBox("Экспорт")
        form = QFormLayout(export)
        self.ed_export_dir = QLineEdit()
        export_row = QHBoxLayout()
        export_row.addWidget(self.ed_export_dir)
        btn_export = QPushButton("Выбрать…")
        btn_export.clicked.connect(self._choose_export_dir)
        export_row.addWidget(btn_export)
        self.ed_excel = QLineEdit()
        excel_row = QHBoxLayout()
        excel_row.addWidget(self.ed_excel)
        btn_excel = QPushButton("Выбрать…")
        btn_excel.clicked.connect(self._choose_excel)
        excel_row.addWidget(btn_excel)
        form.addRow("Папка отчётов:", export_row)
        form.addRow("Шаблон Excel:", excel_row)
        root.addWidget(export)

        db = QGroupBox("База данных")
        form = QFormLayout(db)
        self.lbl_db = QLabel(str(DB_PATH))
        self.lbl_settings = QLabel(str(SETTINGS_PATH))
        self.lbl_db.setWordWrap(True)
        self.lbl_settings.setWordWrap(True)
        form.addRow("База материалов:", self.lbl_db)
        form.addRow("Файл настроек:", self.lbl_settings)
        btn_backup = QPushButton("Создать резервную копию базы")
        btn_backup.clicked.connect(self._backup_database)
        form.addRow("", btn_backup)
        root.addWidget(db)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_reset = QPushButton("По умолчанию")
        btn_reset.setProperty("secondary", True)
        btn_reset.clicked.connect(self._reset_defaults)
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_settings)
        buttons.addWidget(btn_reset)
        buttons.addWidget(btn_save)
        root.addLayout(buttons)
        root.addStretch()

    def _load_values(self) -> None:
        s = self.settings
        self.ed_org.setText(s.organization_name)
        self.ed_address.setText(s.organization_address)
        self.ed_phone.setText(s.organization_phone)
        self.ed_email.setText(s.organization_email)
        self.ed_logo.setText(s.logo_path)
        self.spin_vat.setValue(s.vat_rate)
        self.chk_vat.setChecked(s.prices_include_vat)
        self.spin_losses.setValue(s.default_losses_percent)
        self.ed_export_dir.setText(s.export_dir)
        self.ed_excel.setText(s.excel_template_path)

    def _collect(self) -> AppSettings:
        return AppSettings(
            organization_name=self.ed_org.text().strip() or "Организация",
            organization_address=self.ed_address.text().strip(),
            organization_phone=self.ed_phone.text().strip(),
            organization_email=self.ed_email.text().strip(),
            logo_path=self.ed_logo.text().strip(),
            currency=self.settings.currency,
            vat_rate=self.spin_vat.value(),
            prices_include_vat=self.chk_vat.isChecked(),
            default_losses_percent=self.spin_losses.value(),
            default_area_unit=self.settings.default_area_unit,
            export_dir=self.ed_export_dir.text().strip(),
            excel_template_path=self.ed_excel.text().strip(),
            language=self.settings.language,
            weight_conditions=self.settings.weight_conditions,
            weight_corrosion=self.settings.weight_corrosion,
            weight_durability=self.settings.weight_durability,
            weight_temperature=self.settings.weight_temperature,
            weight_compatibility=self.settings.weight_compatibility,
            weight_technology=self.settings.weight_technology,
            weight_cost=self.settings.weight_cost,
        )

    def save_settings(self) -> None:
        try:
            self.settings = self._collect()
            self.settings.save()
            self.settings_changed.emit(self.settings)
            QMessageBox.information(self, "Настройки", "Настройки сохранены.")
        except Exception as exc:
            QMessageBox.critical(self, "Настройки", f"Не удалось сохранить настройки:\n{exc}")

    def _reset_defaults(self) -> None:
        if QMessageBox.question(
            self, "Настройки", "Вернуть настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.settings = AppSettings()
        self._load_values()

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите логотип", "", "Изображения (*.png *.jpg *.jpeg *.svg)"
        )
        if path:
            self.ed_logo.setText(path)

    def _choose_export_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для отчётов", self.ed_export_dir.text())
        if path:
            self.ed_export_dir.setText(path)

    def _choose_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите шаблон Excel", self.ed_excel.text(), "Excel (*.xlsx *.xlsm)"
        )
        if path:
            self.ed_excel.setText(path)

    def _backup_database(self) -> None:
        if not DB_PATH.exists():
            QMessageBox.warning(self, "База данных", "Файл базы данных ещё не создан.")
            return
        default_name = f"database_backup_{__import__('datetime').datetime.now():%Y%m%d_%H%M%S}.sqlite"
        target, _ = QFileDialog.getSaveFileName(
            self, "Сохранить резервную копию", str(Path.home() / default_name), "SQLite (*.sqlite)"
        )
        if not target:
            return
        try:
            shutil.copy2(DB_PATH, target)
            QMessageBox.information(self, "База данных", f"Резервная копия создана:\n{target}")
        except Exception as exc:
            QMessageBox.critical(self, "База данных", f"Не удалось создать копию:\n{exc}")
