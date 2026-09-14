from pathlib import Path

import openpyxl

from app.services.system_book_importer import SystemBookImporter


def test_system_book_importer_keeps_sheet_row_cells_and_sha256(tmp_path: Path):
    path = tmp_path / "Системы 2.XLSX"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "АКЗ"
    sheet.append(["Система", "Материал", "DFT"])
    sheet.append(["Система A", "Материал X", 120])
    sheet.append([None, None, None])
    workbook.save(path)

    rows = SystemBookImporter().read(path)

    assert len(rows) == 2
    assert rows[0].sheet == "АКЗ"
    assert rows[0].row_number == 1
    assert rows[1].row_number == 2
    assert rows[1].cells == ("Система A", "Материал X", 120)
    assert len(rows[0].source.sha256) == 64


def test_system_book_importer_rejects_unknown_book_name(tmp_path: Path):
    path = tmp_path / "other.xlsx"
    workbook = openpyxl.Workbook()
    workbook.save(path)

    try:
        SystemBookImporter().read(path)
    except ValueError as exc:
        assert "Неизвестный файл каталога систем" in str(exc)
    else:
        raise AssertionError("unknown workbook name must be rejected")
