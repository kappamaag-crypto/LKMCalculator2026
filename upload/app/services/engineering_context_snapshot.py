"""Persistence helpers for normative and surface engineering context.

The serializers are deliberately source-preserving: they never manufacture
normative values or convert missing source information into a permission.
"""

from __future__ import annotations
from datetime import date
from typing import Any
from app.domain.engineering_context import EngineeringContext
from app.domain.normative import NormativeModel, NormativeRule, NormativeSource, UNKNOWN
from app.domain.surface_profile import SurfaceCondition, SurfacePreparation, SurfaceProfile


def _source_to_dict(source: NormativeSource | None) -> dict[str, Any] | None:
    if source is None:return None
    return {"document_id":source.document_id,"title":source.title,"revision":source.revision,"effective_from":source.effective_from.isoformat() if source.effective_from else None,"effective_to":source.effective_to.isoformat() if source.effective_to else None,"issuer":source.issuer,"source_uri":source.source_uri}

def _source_from_dict(data: dict[str, Any] | None) -> NormativeSource | None:
    if not data:return None
    return NormativeSource(document_id=str(data.get("document_id","")),title=str(data.get("title","")),revision=str(data.get("revision","")),effective_from=date.fromisoformat(data["effective_from"]) if data.get("effective_from") else None,effective_to=date.fromisoformat(data["effective_to"]) if data.get("effective_to") else None,issuer=str(data.get("issuer","")),source_uri=str(data.get("source_uri","")))

def normative_model_to_dict(model: NormativeModel | None) -> dict[str, Any] | None:
    if model is None:return None
    return {"model_id":model.model_id,"version":model.version,"description":model.description,"rules":{rule_id:{"rule_id":rule.rule_id,"value":rule.value,"status":rule.status,"source":_source_to_dict(rule.source),"applicability":rule.applicability,"notes":rule.notes} for rule_id,rule in model.rules.items()}}

def normative_model_from_dict(data: dict[str, Any] | None) -> NormativeModel | None:
    if not data:return None
    rules={rule_id:NormativeRule(rule_id=str(rule_data.get("rule_id",rule_id)),value=rule_data.get("value"),status=str(rule_data.get("status",UNKNOWN)),source=_source_from_dict(rule_data.get("source")),applicability=str(rule_data.get("applicability","")),notes=str(rule_data.get("notes",""))) for rule_id,rule_data in dict(data.get("rules",{})).items()}
    return NormativeModel(model_id=str(data.get("model_id","")),version=str(data.get("version","")),rules=rules,description=str(data.get("description","")))

def surface_condition_to_dict(condition: SurfaceCondition | None) -> dict[str, Any] | None:
    if condition is None:return None
    return {"preparation":{"method":condition.preparation.method,"grade":condition.preparation.grade,"standard":_source_to_dict(condition.preparation.standard),"assessment":condition.preparation.assessment,"notes":condition.preparation.notes},"profile":{"measurement":condition.profile.measurement,"minimum_um":condition.profile.minimum_um,"nominal_um":condition.profile.nominal_um,"maximum_um":condition.profile.maximum_um,"standard":_source_to_dict(condition.profile.standard),"assessment":condition.profile.assessment,"notes":condition.profile.notes},"substrate":condition.substrate,"contamination_status":condition.contamination_status,"moisture_status":condition.moisture_status}

def surface_condition_from_dict(data: dict[str, Any] | None) -> SurfaceCondition | None:
    if not data:return None
    preparation=dict(data.get("preparation",{})); profile=dict(data.get("profile",{}))
    return SurfaceCondition(preparation=SurfacePreparation(method=preparation.get("method","UNKNOWN"),grade=str(preparation.get("grade","")),standard=_source_from_dict(preparation.get("standard")),assessment=str(preparation.get("assessment",UNKNOWN)),notes=str(preparation.get("notes",""))),profile=SurfaceProfile(measurement=profile.get("measurement","UNKNOWN"),minimum_um=profile.get("minimum_um"),nominal_um=profile.get("nominal_um"),maximum_um=profile.get("maximum_um"),standard=_source_from_dict(profile.get("standard")),assessment=str(profile.get("assessment",UNKNOWN)),notes=str(profile.get("notes",""))),substrate=str(data.get("substrate","")),contamination_status=str(data.get("contamination_status",UNKNOWN)),moisture_status=str(data.get("moisture_status",UNKNOWN)))

def engineering_context_to_dict(context: EngineeringContext | None) -> dict[str, Any] | None:
    if context is None:return None
    return {"normative_model":normative_model_to_dict(context.normative_model),"surface_condition":surface_condition_to_dict(context.surface_condition)}

def engineering_context_from_dict(data: dict[str, Any] | None) -> EngineeringContext | None:
    if data is None:return None
    surface=surface_condition_from_dict(data.get("surface_condition"))
    return EngineeringContext(normative_model=normative_model_from_dict(data.get("normative_model")),surface_condition=surface or SurfaceCondition())
