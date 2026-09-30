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
        {"source": {"file": "x.xlsx", "sheet": "S", "row": 1}, "source_row_id": "1", "ral": "7035", "color": "серый", "price_per_kg": 700.0, "density": 1.4, "solids_by_volume_percent": 73.0, "material_name_raw": "Blank Finish"},
        {"source": {"file": "x.xlsx", "sheet": "S", "row": 2}, "source_row_id": "2", "ral": "7040", "color": "серый", "price_per_kg": 750.0, "density": 1.4, "solids_by_volume_percent": 73.0, "material_name_raw": "Blank Finish"},
    ]
    output = builder.finalize({
        "blank finish": {
            "material_name": "Blank Finish",
            "base_material_name": "Blank Finish",
            "ral": "",
            "aliases": ["Blank Finish Ral 7035", "Blank Finish Ral 7040"],
            "observations": observations,
            "source_records": [x["source"] for x in observations],
        }
    })
    assert len(output["materials"]) == 1
    variants = {v["ral"]: v for v in output["materials"][0]["variants"]}
    assert variants["7035"]["price_per_kg"] == 700.0
    assert variants["7040"]["price_per_kg"] == 750.0
    assert variants["7035"]["density"] == variants["7040"]["density"] == 1.4
    assert variants["7035"]["solids_by_volume_percent"] == variants["7040"]["solids_by_volume_percent"] == 73.0
