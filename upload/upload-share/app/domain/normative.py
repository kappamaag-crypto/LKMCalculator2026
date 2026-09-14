"""Versioned normative references for engineering decisions.

This module stores *source metadata and explicit rules*, not invented normative
values. A rule can be absent/UNKNOWN until a verified source is loaded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Mapping

UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NormativeSource:
    """Identity of a normative/technical source used by an engineering rule."""

    document_id: str
    title: str = ""
    revision: str = ""
    effective_from: date | None = None
    effective_to: date | None = None
    issuer: str = ""
    source_uri: str = ""

    def key(self) -> str:
        return f"{self.document_id}:{self.revision}" if self.revision else self.document_id


@dataclass(frozen=True)
class NormativeRule:
    """One source-backed rule with an explicit UNKNOWN state."""

    rule_id: str
    value: object | None = None
    status: str = UNKNOWN
    source: NormativeSource | None = None
    applicability: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        status = self.status.strip().upper()
        if not self.rule_id.strip():
            raise ValueError("rule_id is required")
        if status not in {"KNOWN", UNKNOWN}:
            raise ValueError("rule status must be KNOWN or UNKNOWN")
        if status == "KNOWN" and self.source is None:
            raise ValueError("KNOWN normative rules require a source")
        object.__setattr__(self, "status", status)

    @property
    def is_known(self) -> bool:
        return self.status == "KNOWN"


@dataclass(frozen=True)
class NormativeModel:
    """Immutable version of the normative rule set used for a calculation."""

    model_id: str
    version: str
    rules: Mapping[str, NormativeRule] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if not self.version.strip():
            raise ValueError("version is required")
        normalized = dict(self.rules)
        for rule_id, rule in normalized.items():
            if rule_id != rule.rule_id:
                raise ValueError("rule mapping key must match rule_id")
        object.__setattr__(self, "rules", MappingProxyType(normalized))

    def rule(self, rule_id: str) -> NormativeRule:
        """Return a rule, or an explicit UNKNOWN rule when source data is absent."""
        return self.rules.get(rule_id, NormativeRule(rule_id=rule_id))

    def known_rules(self) -> tuple[NormativeRule, ...]:
        return tuple(rule for rule in self.rules.values() if rule.is_known)


class NormativeRegistry:
    """Deterministic registry for versioned normative models."""

    def __init__(self, models: tuple[NormativeModel, ...] = ()) -> None:
        self._models = {f"{model.model_id}:{model.version}": model for model in models}

    def register(self, model: NormativeModel) -> None:
        key = f"{model.model_id}:{model.version}"
        if key in self._models:
            raise ValueError(f"normative model already registered: {key}")
        self._models[key] = model

    def get(self, model_id: str, version: str) -> NormativeModel | None:
        return self._models.get(f"{model_id}:{version}")

    def require(self, model_id: str, version: str) -> NormativeModel:
        model = self.get(model_id, version)
        if model is None:
            raise KeyError(f"normative model not found: {model_id}:{version}")
        return model

    def versions(self, model_id: str) -> tuple[str, ...]:
        prefix = f"{model_id}:"
        return tuple(key[len(prefix):] for key in self._models if key.startswith(prefix))
