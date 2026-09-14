"""Smoke-проверка открытия customer Excel и headless PDF-конвертации через LibreOffice."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.config import AppSettings
from app.infrastructure.export.customer_excel_exporter import CustomerExcelExporter
from tests.test_customer_excel_export import _result, _template


def test_customer_excel_roundtrips_through_libreoffice_to_pdf(tmp_path: Path):
    template = tmp_path / "template.xlsx"
    output = tmp_path / "customer.xlsx"
    pdf_dir = tmp_path / "pdf"
    profile_dir = tmp_path / "lo-profile"
    pdf_dir.mkdir()

    _template(template)
    settings = AppSettings(report_mode="full", excel_template_path=str(template))
    CustomerExcelExporter(settings).export_calculation(_result(4), output)

    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    subprocess.run(
        [
            "soffice",
            "--headless",
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(pdf_dir),
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )

    pdf = pdf_dir / "customer.pdf"
    assert pdf.exists()
    assert pdf.stat().st_size > 0
    assert pdf.read_bytes().startswith(b"%PDF-")
