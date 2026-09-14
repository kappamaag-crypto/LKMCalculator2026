from app.services.tds_normative_bridge import engineering_context_from_known_tds, normative_model_from_known_tds, tds_trace_for_material
def test_model():
    known = normative_model_from_known_tds().known_rules()
    assert len(known) >= 25
    assert all(r.source.source_uri.startswith("sha256:") for r in known)
def test_trace_tank_lp():
    t = tds_trace_for_material("Blank Tank LP")
    assert t["tds_verified"] == "KNOWN" and t["document_id"] == "BLANK_TANK_LP_TDS"
def test_ctx():
    assert engineering_context_from_known_tds(["Blank Zinc primer"]).normative_status == "KNOWN"
