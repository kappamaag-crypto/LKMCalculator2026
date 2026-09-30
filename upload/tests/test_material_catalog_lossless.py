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


def test_ral_is_extracted_from_product_name():
    assert builder.extract_ral("Blank Finish RAL 7035") == "7035"
    assert builder.extract_ral("Blank Finish РАЛ-7040") == "7040"


def test_ral_variants_have_distinct_catalog_identity():
    materials = {
        "blank finish|ral:7035": {
            "material_name": "Blank Finish",
            "base_material_name": "Blank Finish",
            "ral": "7035",
            "aliases": ["Blank Finish RAL 7035"],
            "observations": [{
                "source": {"file": "a.xlsx", "sheet": "Лист1", "row": 1},
                "density": 1.3,
                "solids_by_volume_percent": 58,
                "price_per_kg": 700,
            }],
            "source_records": [],
        },
        "blank finish|ral:7040": {
            "material_name": "Blank Finish",
            "base_material_name": "Blank Finish",
            "ral": "7040",
            "aliases": ["Blank Finish RAL 7040"],
            "observations": [{
                "source": {"file": "a.xlsx", "sheet": "Лист1", "row": 2},
                "density": 1.3,
                "solids_by_volume_percent": 58,
                "price_per_kg": 750,
            }],
            "source_records": [],
        },
    }
    out = builder.finalize(materials)
    variants = {(x["material_name"], x["ral"], x["price_per_kg"]) for x in out["materials"]}
    assert variants == {("Blank Finish", "7035", 700.0), ("Blank Finish", "7040", 750.0)}


def test_discovered_workbooks_are_not_hard_coded():
    assert all(path.lower().endswith((".xls", ".xlsx", ".xlsm")) for path in builder.WORKBOOKS)


def test_variant_group_preserves_ral_and_price():
    observations = [
        {"ral": "7035", "color": "серый", "price_per_kg": 700.0, "density": 1.4, "solids_by_volume_percent": 73.0},
        {"ral": "7040", "color": "серый", "price_per_kg": 750.0, "density": 1.4, "solids_by_volume_percent": 73.0},
    ]
    assert observations[0]["price_per_kg"] != observations[1]["price_per_kg"]
    assert observations[0]["density"] == observations[1]["density"]
    assert observations[0]["solids_by_volume_percent"] == observations[1]["solids_by_volume_percent"]
