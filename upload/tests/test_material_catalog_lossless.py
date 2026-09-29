"""Regression coverage for the lossless Excel material catalog."""
from upload.scripts import build_material_catalog as builder


def test_excel_dry_residue_is_volumetric_solids():
    assert builder.num("95±3") == 95.0
    assert builder.range_text("95±3") == "95±3"


def test_source_row_id_is_stable():
    a = builder.row_id("Системы 3.xlsx", "АКЗ", 12)
    b = builder.row_id("Системы 3.xlsx", "АКЗ", 12)
    assert a == b


def test_source_row_keeps_every_nonempty_cell():
    row = builder.make_source_row(
        "Системы 4.xlsx",
        "Лист1",
        10,
        ["Blank Universal 110", 1.4, 73, None, "серый"],
        {"material": [0], "density": [1], "solids": [2], "color": [4]},
    )
    assert [x["value"] for x in row["cells"]] == ["Blank Universal 110", "1.4", "73", "серый"]
    assert row["source"]["row"] == 10


def test_material_column_accepts_product_name_without_keyword_filter():
    headers = {"material": [2], "density": [5]}
    vals = ["x", "x", "Some Vendor Product", "x", "x", "1.42"]
    assert builder.likely_material(vals[2], vals, 2, headers)
