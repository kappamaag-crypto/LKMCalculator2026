from app.services.spk_effa_tds_catalog import spk_effa_tds_by_id, spk_effa_tds_documents
from app.services.tds_known_rules import known_dft_rule_for_material_name, known_rules_for_document, known_tds_rules, resolve_document_id_for_material_name
from app.services.tds_rule_promotion import parse_dft_range_um
from app.services.tds_technology_bridge import check_target_dft_with_known_tds
from app.domain.enums import MaterialType
from app.domain.models import Material

def test_all_catalog_docs_have_known_rules():
    docs = {d.document_id for d in spk_effa_tds_documents()}
    rule_docs = {r.document_id for r in known_tds_rules()}
    assert not (docs - rule_docs)

def test_tank_lp_promoted_and_specific():
    assert resolve_document_id_for_material_name("Blank Tank LP") == "BLANK_TANK_LP_TDS"
    assert resolve_document_id_for_material_name("Blank Tank") == "BLANK_TANK_TDS"
    dft = known_dft_rule_for_material_name("Blank Tank LP")
    assert parse_dft_range_um(str(dft.value)) == (150.0, 250.0)
    mat = Material(material_name="Blank Tank LP", material_type=MaterialType.PRIMER)
    assert any(i.code == "TECH_TDS_DFT_OK" for i in check_target_dft_with_known_tds(mat, 200).issues)

def test_effa_solids_no_um_dft():
    rules = {r.rule_id: r for r in known_rules_for_document("EFFA_01B_TDS")}
    assert "EFFA_01B_SOLIDS_BY_VOLUME" in rules
    assert known_dft_rule_for_material_name("EFFA 01B") is None
    assert spk_effa_tds_by_id("EFFA_01B_TDS").sha256.startswith("f74b8548")
