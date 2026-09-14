"""Bridge KNOWN TDS rules into NormativeModel / EngineeringContext."""
from __future__ import annotations
from typing import Sequence
from app.domain.engineering_context import EngineeringContext
from app.domain.normative import NormativeModel, NormativeRule, NormativeSource
from app.domain.surface_profile import SurfaceCondition
from app.services.spk_effa_tds_catalog import spk_effa_tds_by_id
from app.services.tds_known_rules import (
    known_dft_rule_for_material_name, known_rules_for_document, known_tds_rules,
    resolve_document_id_for_material_name,
)
from app.services.tds_manifest import TDSRule

def _source_from_tds_document(document_id: str) -> NormativeSource | None:
    doc = spk_effa_tds_by_id(document_id)
    if doc is None or getattr(doc, "status", "UNKNOWN") != "KNOWN":
        return None
    sha = getattr(doc, "sha256", "") or ""
    return NormativeSource(
        document_id=document_id, title=getattr(doc, "title", "") or document_id,
        revision=getattr(doc, "revision", "") or "measured-binary-sha256", issuer="SPKEFFA",
        source_uri=f"sha256:{sha}" if sha else (getattr(doc, "source_path", "") or ""),
    )

def tds_rule_to_normative(rule: TDSRule) -> NormativeRule | None:
    if rule.status != "KNOWN":
        return None
    source = _source_from_tds_document(rule.document_id)
    if source is None:
        return None
    return NormativeRule(rule_id=rule.rule_id, value=rule.value, status="KNOWN", source=source,
                         applicability=rule.applicability or "", notes=f"locator={rule.locator}")

def normative_model_from_known_tds(material_names: Sequence[str] | None = None, *, model_id="spk-effa-tds", version="1") -> NormativeModel:
    rules: dict[str, NormativeRule] = {}
    if material_names:
        doc_ids = set()
        for name in material_names:
            doc_id = resolve_document_id_for_material_name(name or "")
            if doc_id: doc_ids.add(doc_id)
        tds_rules = []
        for doc_id in sorted(doc_ids):
            tds_rules.extend(known_rules_for_document(doc_id))
    else:
        tds_rules = list(known_tds_rules())
    for rule in tds_rules:
        nr = tds_rule_to_normative(rule)
        if nr is not None: rules[nr.rule_id] = nr
    return NormativeModel(model_id=model_id, version=version, rules=rules,
                          description="Explicitly promoted SPKEFFA TDS rules (binary SHA-256 identity)")

def engineering_context_from_known_tds(material_names=None, *, surface_condition=None, base=None) -> EngineeringContext:
    model = normative_model_from_known_tds(material_names)
    surface = surface_condition
    if surface is None and base is not None: surface = base.surface_condition
    if surface is None: surface = SurfaceCondition()
    return EngineeringContext(normative_model=model, surface_condition=surface)

def tds_trace_for_material(material_name: str) -> dict:
    doc_id = resolve_document_id_for_material_name(material_name or "")
    dft = known_dft_rule_for_material_name(material_name or "")
    doc = spk_effa_tds_by_id(doc_id) if doc_id else None
    return {
        "material_name": material_name, "document_id": doc_id,
        "document_sha256": getattr(doc, "sha256", None) if doc else None,
        "document_status": getattr(doc, "status", None) if doc else None,
        "dft_rule_id": dft.rule_id if dft else None, "dft_value": dft.value if dft else None,
        "dft_status": dft.status if dft else "UNKNOWN",
        "tds_verified": "KNOWN" if dft is not None and dft.status == "KNOWN" else "UNKNOWN",
    }
