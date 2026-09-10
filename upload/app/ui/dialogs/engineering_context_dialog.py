"""Dialog for explicit source-backed engineering context entry.

The dialog stores source identity and measured/declared surface data only. It
never creates normative values or infers an approval from a missing source.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.engineering_context import EngineeringContext
from app.domain.normative import NormativeModel, NormativeSource, UNKNOWN
from app.domain.surface_profile import SurfaceCondition, SurfacePreparation, SurfaceProfile
from app.services.engineering_source_registry import EngineeringSourceRegistry, EngineeringSource


class EngineeringContextDialog(QDialog):
    """Edit normative source identity and structured surface condition."""

    def __init__(self, context: EngineeringContext | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Инженерный контекст")
        self.setMinimumWidth(620)
        self._context = context or EngineeringContext()
        self._source_registry = EngineeringSourceRegistry()
        self._build_ui()
        self._load_context(self._context)

    @staticmethod
    def _source_fields(group: QGroupBox) -> tuple[QLineEdit, QLineEdit, QLineEdit, QLineEdit, QLineEdit]:
        form = QFormLayout(group)
        document_id = QLineEdit()
        title = QLineEdit()
        revision = QLineEdit()
        issuer = QLineEdit()
        uri = QLineEdit()
        form.addRow("Документ / ID:", document_id)
        form.addRow("Наименование:", title)
        form.addRow("Редакция:", revision)
        form.addRow("Организация:", issuer)
        form.addRow("Источник / URI:", uri)
        return document_id, title, revision, issuer, uri

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()

        normative_page = QWidget()
        normative_layout = QVBoxLayout(normative_page)
        normative_source = QGroupBox("Источник нормативной базы")
        (
            self.norm_document_id,
            self.norm_title,
            self.norm_revision,
            self.norm_issuer,
            self.norm_uri,
        ) = self._source_fields(normative_source)
        self.norm_source_combo = QComboBox()
        self.norm_source_combo.addItem("— выбрать документ из реестра —", None)
        for item in self._source_registry.by_category("Нормативный документ"):
            self.norm_source_combo.addItem(item.source.title or item.source.document_id, item)
        self.norm_source_combo.currentIndexChanged.connect(self._on_norm_source_selected)
        normative_source.layout().insertRow(0, "Реестр источников:", self.norm_source_combo)
        normative_layout.addWidget(normative_source)

        normative_form = QFormLayout()
        self.norm_model_id = QLineEdit()
        self.norm_version = QLineEdit()
        self.norm_description = QLineEdit()
        self.norm_status = QComboBox()
        self.norm_status.addItem("Источник выбран, правила пока UNKNOWN", UNKNOWN)
        normative_form.addRow("ID модели:", self.norm_model_id)
        normative_form.addRow("Версия модели:", self.norm_version)
        normative_form.addRow("Описание:", self.norm_description)
        normative_form.addRow("Состояние правил:", self.norm_status)
        normative_layout.addLayout(normative_form)
        tabs.addTab(normative_page, "Нормативная база")

        surface_page = QWidget()
        surface_layout = QVBoxLayout(surface_page)
        preparation_group = QGroupBox("Подготовка поверхности")
        preparation_form = QFormLayout(preparation_group)
        self.prep_method = QComboBox()
        for value, title in (("UNKNOWN", "Не задано"), ("Sa", "Sa"), ("St", "St"), ("OTHER", "Другое")):
            self.prep_method.addItem(title, value)
        self.prep_grade = QLineEdit()
        self.prep_status = QComboBox()
        self.prep_status.addItem("UNKNOWN", UNKNOWN)
        self.prep_status.addItem("KNOWN", "KNOWN")
        self.prep_notes = QLineEdit()
        preparation_form.addRow("Метод:", self.prep_method)
        preparation_form.addRow("Степень / обозначение:", self.prep_grade)
        preparation_form.addRow("Оценка:", self.prep_status)
        preparation_form.addRow("Примечание:", self.prep_notes)
        prep_source = QGroupBox("Источник степени подготовки")
        (
            self.prep_document_id,
            self.prep_title,
            self.prep_revision,
            self.prep_issuer,
            self.prep_uri,
        ) = self._source_fields(prep_source)

        profile_group = QGroupBox("Профиль шероховатости")
        profile_form = QFormLayout(profile_group)
        self.profile_measurement = QComboBox()
        for value, title in (("UNKNOWN", "Не задано"), ("Rz", "Rz"), ("Ry5", "Ry5"), ("Rmax", "Rmax")):
            self.profile_measurement.addItem(title, value)
        self.profile_min = self._spin()
        self.profile_nominal = self._spin()
        self.profile_max = self._spin()
        self.profile_status = QComboBox()
        self.profile_status.addItem("UNKNOWN", UNKNOWN)
        self.profile_status.addItem("KNOWN", "KNOWN")
        self.profile_notes = QLineEdit()
        profile_form.addRow("Параметр:", self.profile_measurement)
        profile_form.addRow("Минимум, мкм:", self.profile_min)
        profile_form.addRow("Номинал, мкм:", self.profile_nominal)
        profile_form.addRow("Максимум, мкм:", self.profile_max)
        profile_form.addRow("Оценка:", self.profile_status)
        profile_form.addRow("Примечание:", self.profile_notes)
        profile_source = QGroupBox("Источник профиля")
        (
            self.profile_document_id,
            self.profile_title,
            self.profile_revision,
            self.profile_issuer,
            self.profile_uri,
        ) = self._source_fields(profile_source)

        surface_form = QFormLayout()
        self.surface_substrate = QLineEdit()
        self.contamination_status = self._status_combo()
        self.moisture_status = self._status_combo()
        surface_form.addRow("Основание:", self.surface_substrate)
        surface_form.addRow("Загрязнение:", self.contamination_status)
        surface_form.addRow("Влага:", self.moisture_status)
        surface_layout.addLayout(surface_form)
        surface_layout.addWidget(preparation_group)
        surface_layout.addWidget(prep_source)
        surface_layout.addWidget(profile_group)
        surface_layout.addWidget(profile_source)
        tabs.addTab(surface_page, "Поверхность")

        root.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 10000.0)
        spin.setDecimals(1)
        spin.setSpecialValueText("не задано")
        spin.setValue(0.0)
        return spin

    @staticmethod
    def _status_combo() -> QComboBox:
        combo = QComboBox()
        for value in (UNKNOWN, "ACCEPTABLE", "UNACCEPTABLE"):
            combo.addItem(value, value)
        return combo

    @staticmethod
    def _source_from_widgets(document_id: QLineEdit, title: QLineEdit, revision: QLineEdit, issuer: QLineEdit, uri: QLineEdit) -> NormativeSource | None:
        value = document_id.text().strip()
        if not value:
            return None
        return NormativeSource(
            document_id=value,
            title=title.text().strip(),
            revision=revision.text().strip(),
            issuer=issuer.text().strip(),
            source_uri=uri.text().strip(),
        )

    def _on_norm_source_selected(self, index: int) -> None:
        item = self.norm_source_combo.itemData(index)
        if not isinstance(item, EngineeringSource):
            return
        source = item.source
        self.norm_document_id.setText(source.document_id)
        self.norm_title.setText(source.title)
        self.norm_revision.setText(source.revision)
        self.norm_issuer.setText(source.issuer)
        self.norm_uri.setText(source.source_uri)
        if not self.norm_model_id.text().strip():
            self.norm_model_id.setText(source.document_id)
        if not self.norm_version.text().strip():
            self.norm_version.setText(source.revision or "source")

    def _load_source(self, source: NormativeSource | None, fields: tuple[QLineEdit, QLineEdit, QLineEdit, QLineEdit, QLineEdit]) -> None:
        if source is None:
            return
        for widget, value in zip(fields, (source.document_id, source.title, source.revision, source.issuer, source.source_uri)):
            widget.setText(value)
        if fields == (self.norm_document_id, self.norm_title, self.norm_revision, self.norm_issuer, self.norm_uri):
            idx = self.norm_source_combo.findText(source.title or source.document_id)
            if idx >= 0:
                self.norm_source_combo.setCurrentIndex(idx)

    def _load_context(self, context: EngineeringContext) -> None:
        model = context.normative_model
        if model is not None:
            self.norm_model_id.setText(model.model_id)
            self.norm_version.setText(model.version)
            self.norm_description.setText(model.description)
            first_source = next((rule.source for rule in model.rules.values() if rule.source is not None), None)
            self._load_source(first_source, (self.norm_document_id, self.norm_title, self.norm_revision, self.norm_issuer, self.norm_uri))

        condition = context.surface_condition
        preparation = condition.preparation
        profile = condition.profile
        self.prep_method.setCurrentIndex(max(0, self.prep_method.findData(preparation.method)))
        self.prep_grade.setText(preparation.grade)
        self.prep_status.setCurrentIndex(1 if preparation.is_known else 0)
        self.prep_notes.setText(preparation.notes)
        self._load_source(preparation.standard, (self.prep_document_id, self.prep_title, self.prep_revision, self.prep_issuer, self.prep_uri))
        self.profile_measurement.setCurrentIndex(max(0, self.profile_measurement.findData(profile.measurement)))
        for widget, value in ((self.profile_min, profile.minimum_um), (self.profile_nominal, profile.nominal_um), (self.profile_max, profile.maximum_um)):
            widget.setValue(float(value) if value is not None else 0.0)
        self.profile_status.setCurrentIndex(1 if profile.is_known else 0)
        self.profile_notes.setText(profile.notes)
        self._load_source(profile.standard, (self.profile_document_id, self.profile_title, self.profile_revision, self.profile_issuer, self.profile_uri))
        self.surface_substrate.setText(condition.substrate)
        self.contamination_status.setCurrentIndex(max(0, self.contamination_status.findData(condition.contamination_status)))
        self.moisture_status.setCurrentIndex(max(0, self.moisture_status.findData(condition.moisture_status)))

    def context(self) -> EngineeringContext:
        norm_source = self._source_from_widgets(self.norm_document_id, self.norm_title, self.norm_revision, self.norm_issuer, self.norm_uri)
        model_id = self.norm_model_id.text().strip()
        version = self.norm_version.text().strip()
        model = None
        if model_id or version or norm_source:
            if not model_id or not version:
                raise ValueError("Для нормативной модели укажите ID модели и версию.")
            model = NormativeModel(
                model_id=model_id,
                version=version,
                description=self.norm_description.text().strip(),
                rules={},
            )

        prep_source = self._source_from_widgets(self.prep_document_id, self.prep_title, self.prep_revision, self.prep_issuer, self.prep_uri)
        prep_status = str(self.prep_status.currentData())
        if prep_status == "KNOWN" and prep_source is None:
            raise ValueError("KNOWN для подготовки поверхности требует источника.")
        preparation = SurfacePreparation(
            method=self.prep_method.currentData(),
            grade=self.prep_grade.text().strip(),
            standard=prep_source,
            assessment=prep_status,
            notes=self.prep_notes.text().strip(),
        )

        profile_source = self._source_from_widgets(self.profile_document_id, self.profile_title, self.profile_revision, self.profile_issuer, self.profile_uri)
        profile_status = str(self.profile_status.currentData())
        if profile_status == "KNOWN" and profile_source is None:
            raise ValueError("KNOWN для профиля требует источника.")
        profile = SurfaceProfile(
            measurement=self.profile_measurement.currentData(),
            minimum_um=self.profile_min.value() or None,
            nominal_um=self.profile_nominal.value() or None,
            maximum_um=self.profile_max.value() or None,
            standard=profile_source,
            assessment=profile_status,
            notes=self.profile_notes.text().strip(),
        )
        return EngineeringContext(
            normative_model=model,
            surface_condition=SurfaceCondition(
                preparation=preparation,
                profile=profile,
                substrate=self.surface_substrate.text().strip(),
                contamination_status=str(self.contamination_status.currentData()),
                moisture_status=str(self.moisture_status.currentData()),
            ),
        )

    def accept(self) -> None:
        try:
            self._context = self.context()
        except ValueError as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Инженерный контекст", str(exc))
            return
        super().accept()
