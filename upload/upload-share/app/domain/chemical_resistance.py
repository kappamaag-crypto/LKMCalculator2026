"""Chemical resistance — only via source-backed rules.

Без явного KNOWN-правила с NormativeSource результат всегда UNKNOWN.
Модуль не выводит стойкость из типа связующего, категории коррозии или «опыта».
Не импортирует services/ORM/UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from app.domain.normative import NormativeSource, UNKNOWN


RESISTANT = "RESISTANT"
NOT_RESISTANT = "NOT_RESISTANT"


@dataclass(frozen=True)
class ChemicalAgent:
    """Identifier of the chemical medium / agent under evaluation."""

    agent_id: str
    name: str = ""
    concentration_percent: float | None = None
    temperature_c: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id is required")
        if self.concentration_percent is not None and self.concentration_percent < 0:
            raise ValueError("concentration_percent must be non-negative")


@dataclass(frozen=True)
class ChemicalResistanceRule:
    """One source-backed chemical resistance statement.

    status KNOWN requires a NormativeSource. outcome is RESISTANT or NOT_RESISTANT
    only when status is KNOWN; otherwise outcome is UNKNOWN.
    """

    rule_id: str
    material_hint: str
    agent_id: str
    status: str = UNKNOWN
    outcome: str = UNKNOWN
    source: NormativeSource | None = None
    concentration_max_percent: float | None = None
    temperature_max_c: float | None = None
    applicability: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id is required")
        if not self.material_hint.strip():
            raise ValueError("material_hint is required")
        if not self.agent_id.strip():
            raise ValueError("agent_id is required")
        status = self.status.strip().upper()
        if status not in {"KNOWN", UNKNOWN}:
            raise ValueError("status must be KNOWN or UNKNOWN")
        if status == "KNOWN" and self.source is None:
            raise ValueError("KNOWN chemical resistance rules require a NormativeSource")
        outcome = self.outcome.strip().upper()
        if status == "KNOWN" and outcome not in {RESISTANT, NOT_RESISTANT}:
            raise ValueError("KNOWN rules must have outcome RESISTANT or NOT_RESISTANT")
        if status != "KNOWN":
            outcome = UNKNOWN
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "outcome", outcome)

    @property
    def is_known(self) -> bool:
        return self.status == "KNOWN"


@dataclass(frozen=True)
class ChemicalResistanceIssue:
    level: str
    code: str
    message: str
    agent_id: str = ""
    material_name: str = ""


@dataclass
class ChemicalResistanceCheckResult:
    """Aggregate result for material(s) vs chemical agent(s)."""

    items: list[ChemicalResistanceIssue] = field(default_factory=list)
    outcomes: dict[str, dict[str, str]] = field(default_factory=dict)

    def add(self, level: str, code: str, message: str, *, agent_id: str = "", material_name: str = "") -> None:
        self.items.append(
            ChemicalResistanceIssue(
                level=level,
                code=code,
                message=message,
                agent_id=agent_id,
                material_name=material_name,
            )
        )

    def set_outcome(self, material_name: str, agent_id: str, outcome: str) -> None:
        self.outcomes.setdefault(material_name, {})[agent_id] = outcome

    @property
    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.items)

    @property
    def has_unknown(self) -> bool:
        if any(i.code == "CHEM_RESISTANCE_UNKNOWN" for i in self.items):
            return True
        for by_agent in self.outcomes.values():
            if any(v == UNKNOWN for v in by_agent.values()):
                return True
        return False

    @property
    def all_resistant(self) -> bool:
        if not self.outcomes:
            return False
        for by_agent in self.outcomes.values():
            for outcome in by_agent.values():
                if outcome != RESISTANT:
                    return False
        return not self.has_errors

    def summary_lines(self) -> list[str]:
        lines = ["Chemical resistance check:"]
        for mat, by_agent in sorted(self.outcomes.items()):
            for agent, outcome in sorted(by_agent.items()):
                lines.append(f"  {mat} × {agent} → {outcome}")
        for item in self.items:
            lines.append(f"  {item.level.upper()} {item.code}: {item.message}")
        return lines


def _normalize_hint(text: str) -> str:
    return " ".join(text.casefold().split())


def resolve_rule(
    material_name: str,
    agent_id: str,
    rules: Sequence[ChemicalResistanceRule],
) -> ChemicalResistanceRule | None:
    needle = _normalize_hint(material_name)
    agent = agent_id.strip().casefold()
    candidates: list[ChemicalResistanceRule] = []
    for rule in rules:
        if not rule.is_known:
            continue
        if rule.agent_id.strip().casefold() != agent:
            continue
        hint = _normalize_hint(rule.material_hint)
        if hint and hint in needle:
            candidates.append(rule)
    if not candidates:
        return None
    return max(candidates, key=lambda r: len(_normalize_hint(r.material_hint)))


def check_chemical_resistance(
    material_names: Sequence[str],
    agents: Sequence[ChemicalAgent],
    rules: Sequence[ChemicalResistanceRule],
    *,
    require_known: bool = False,
) -> ChemicalResistanceCheckResult:
    result = ChemicalResistanceCheckResult()
    if not material_names:
        result.add("info", "CHEM_NO_MATERIALS", "Материалы для проверки химстойкости не переданы.")
        return result
    if not agents:
        result.add("info", "CHEM_NO_AGENTS", "Химические агенты не заданы — проверка не выполняется.")
        return result

    known_rules = [r for r in rules if r.is_known]
    if not known_rules:
        for name in material_names:
            for agent in agents:
                result.set_outcome(name, agent.agent_id, UNKNOWN)
                result.add(
                    "error" if require_known else "info",
                    "CHEM_RESISTANCE_UNKNOWN",
                    f"Нет source-backed правил химстойкости; «{name}» × «{agent.agent_id}» = UNKNOWN.",
                    agent_id=agent.agent_id,
                    material_name=name,
                )
        return result

    for name in material_names:
        for agent in agents:
            rule = resolve_rule(name, agent.agent_id, known_rules)
            if rule is None:
                result.set_outcome(name, agent.agent_id, UNKNOWN)
                result.add(
                    "error" if require_known else "info",
                    "CHEM_RESISTANCE_UNKNOWN",
                    f"Нет KNOWN-правила для «{name}» × «{agent.agent_id}» — UNKNOWN (не выводится из типа ЛКМ).",
                    agent_id=agent.agent_id,
                    material_name=name,
                )
                continue

            outcome = rule.outcome
            if (
                rule.concentration_max_percent is not None
                and agent.concentration_percent is not None
                and agent.concentration_percent > rule.concentration_max_percent
            ):
                outcome = NOT_RESISTANT
                result.add(
                    "error",
                    "CHEM_CONCENTRATION_EXCEEDED",
                    (
                        f"Концентрация {agent.concentration_percent:g}% выше предела правила "
                        f"{rule.concentration_max_percent:g}% ({rule.rule_id})."
                    ),
                    agent_id=agent.agent_id,
                    material_name=name,
                )
            if (
                rule.temperature_max_c is not None
                and agent.temperature_c is not None
                and agent.temperature_c > rule.temperature_max_c
            ):
                outcome = NOT_RESISTANT
                result.add(
                    "error",
                    "CHEM_TEMPERATURE_EXCEEDED",
                    (
                        f"Температура {agent.temperature_c:g} °C выше предела правила "
                        f"{rule.temperature_max_c:g} °C ({rule.rule_id})."
                    ),
                    agent_id=agent.agent_id,
                    material_name=name,
                )

            result.set_outcome(name, agent.agent_id, outcome)
            if outcome == RESISTANT:
                result.add(
                    "info",
                    "CHEM_RESISTANT",
                    f"KNOWN: «{name}» устойчив к «{agent.agent_id}» ({rule.rule_id}; {rule.source.document_id if rule.source else '—'}).",
                    agent_id=agent.agent_id,
                    material_name=name,
                )
            elif outcome == NOT_RESISTANT:
                result.add(
                    "error",
                    "CHEM_NOT_RESISTANT",
                    f"KNOWN: «{name}» не устойчив к «{agent.agent_id}» ({rule.rule_id}).",
                    agent_id=agent.agent_id,
                    material_name=name,
                )

    return result


def rules_by_id(rules: Sequence[ChemicalResistanceRule]) -> Mapping[str, ChemicalResistanceRule]:
    return {r.rule_id: r for r in rules}
