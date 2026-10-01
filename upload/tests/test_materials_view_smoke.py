"""Headless regression tests for the material editor UI."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.models import Material
from app.ui.views.materials_view import MaterialEditDialog


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_material_editor_accepts_unknown_thinner_required():
    _app()
    material = Material(material_name="Без данных", thinner_required=None)
    dialog = MaterialEditDialog(material)
    assert dialog.chk_thinner_required.isChecked() is False
    dialog.close()
