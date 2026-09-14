"""Domain engine for checking compatibility across adjacent coating layers.

The engine is intentionally conservative: it consumes the source-backed
binder matrix from :mod:`app.domain.compatibility`, checks every adjacent
transition, and never turns a missing source entry into a prohibition.

Material-specific TDS conditions (cure state, recoat window, surface
preparation, etc.) are represented as optional context but are not invented
here. They become applicable only when an explicit source-backed rule exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .compatibility import CompatibilityRule, check_materials
from .enums import CompatibilityStatus
from .models import LayerDefinition, Material, SystemCalculationResult


_STATUS_PRIORITY = {
    CompatibilityStatus.ALLOWED: 0,
    CompatibilityStatus.WARNING: 1,
    CompatibilityStatus.UNKNOWN: 2,
    CompatibilityStatus.FORBIDDEN: 3,
}


@dataclass(frozen=True)
class LayerCompatibilityContext:
    """Optional application context for future TDS-backed rules.

    These values are deliberately informational for the current source
    matrix. No generic assumptions are made from them.
    """

    previous_is_cured: Optional[bool] = None
    recoat_elapsed_h: Optional[float] = None
    surface_prepared: Optional[bool] = None


@dataclass(frozen=True)
class LayerTransitionResult:
    """Compatibility result for one adjacent layer transition."""

    previous_layer_index: int
    applied_layer_index: int
    previous_material: Optional[Material]
    applied_material: Optional[Material]
    rule: CompatibilityRule
    context: LayerCompatibilityContext = LayerCompatibilityContext()

    @property
    def status(self) -> CompatibilityStatus:
        return self.rule.status

    @property
    def message(self) -> str:
        previous = (
            self.previous_material.display_name()
            if self.previous_material is not None
            else f"слой {self.previous_layer_index}"
        )
        applied = (
            self.applied_material.display_name()
            if self.applied_material is not None
            else f"слой {self.applied_layer_index}"
        )
        return f"Слой {self.applied_layer_index}: «{applied}» по «{previous}» — {self.rule.note}"


@dataclass(frozen=True)
class LayerCompatibilityReport:
    """Whole-system compatibility report with traceable transitions."""

    transitions: tuple[LayerTransitionResult, ...]

    @property
    def status(self) -> CompatibilityStatus:
        if not self.transitions:
            return CompatibilityStatus.UNKNOWN
        return max(
            (transition.status for transition in self.transitions),
            key=lambda status: _STATUS_PRIORITY[status],
        )

    @property
    def is_allowed(self) -> bool:
        return self.status is CompatibilityStatus.ALLOWED

    @property
    def warning_transitions(self) -> tuple[LayerTransitionResult, ...]:
        """Transitions with a source-backed special condition/warning."""
        return tuple(
            transition
            for transition in self.transitions
            if transition.status is CompatibilityStatus.WARNING
        )

    @property
    def unknown_transitions(self) -> tuple[LayerTransitionResult, ...]:
        """Transitions for which the source matrix has no confirmed rule."""
        return tuple(
            transition
            for transition in self.transitions
            if transition.status is CompatibilityStatus.UNKNOWN
        )

    @property
    def forbidden_transitions(self) -> tuple[LayerTransitionResult, ...]:
        """Transitions explicitly marked forbidden by the source matrix."""
        return tuple(
            transition
            for transition in self.transitions
            if transition.status is CompatibilityStatus.FORBIDDEN
        )

    @property
    def blocking_transitions(self) -> tuple[LayerTransitionResult, ...]:
        """Transitions that prevent an unconditional compatibility pass.

        UNKNOWN is included because a missing source entry cannot be promoted
        to compatibility. It is a review blocker, not an invented prohibition:
        the caller must resolve the evidence before declaring the system
        compatible. WARNING remains non-blocking and preserves its source note.
        """
        return tuple(
            transition
            for transition in self.transitions
            if transition.status in {
                CompatibilityStatus.UNKNOWN,
                CompatibilityStatus.FORBIDDEN,
            }
        )


class LayerCompatibilityEngine:
    """Check every adjacent pair in a coating system.

    ``layers`` may contain any reasonable number of layers. The engine does
    not recalculate consumption and has no UI/database dependencies.
    """

    def check_transition(
        self,
        previous: Material | None,
        applied: Material | None,
        *,
        previous_layer_index: int = 1,
        applied_layer_index: int = 2,
        context: LayerCompatibilityContext | None = None,
    ) -> LayerTransitionResult:
        rule = check_materials(previous, applied)
        return LayerTransitionResult(
            previous_layer_index=previous_layer_index,
            applied_layer_index=applied_layer_index,
            previous_material=previous,
            applied_material=applied,
            rule=rule,
            context=context or LayerCompatibilityContext(),
        )

    def check_layers(
        self,
        layers: Sequence[LayerDefinition],
        contexts: Sequence[LayerCompatibilityContext] | None = None,
    ) -> LayerCompatibilityReport:
        if len(layers) < 2:
            return LayerCompatibilityReport(transitions=())
        if contexts is not None and len(contexts) != len(layers) - 1:
            raise ValueError(
                "contexts must contain exactly one item for each adjacent layer transition"
            )

        transitions: list[LayerTransitionResult] = []
        for index in range(1, len(layers)):
            context = contexts[index - 1] if contexts is not None else None
            transitions.append(
                self.check_transition(
                    layers[index - 1].material,
                    layers[index].material,
                    previous_layer_index=index,
                    applied_layer_index=index + 1,
                    context=context,
                )
            )
        return LayerCompatibilityReport(transitions=tuple(transitions))

    def check_result(
        self,
        result: SystemCalculationResult,
        contexts: Sequence[LayerCompatibilityContext] | None = None,
    ) -> LayerCompatibilityReport:
        """Check an already calculated system without recalculating it."""
        layers = [LayerDefinition(material=layer.material) for layer in result.layers]
        return self.check_layers(layers, contexts=contexts)

    def report(
        self,
        result: SystemCalculationResult,
        contexts: Sequence[LayerCompatibilityContext] | None = None,
    ) -> LayerCompatibilityReport:
        """CompatibilityService-facing alias for an already calculated result."""
        return self.check_result(result, contexts=contexts)

    def check_material_sequence(
        self,
        materials: Sequence[Material | None],
        contexts: Sequence[LayerCompatibilityContext] | None = None,
    ) -> LayerCompatibilityReport:
        """Convenience API for an already resolved material sequence."""
        layers = [LayerDefinition(material=material) for material in materials]
        return self.check_layers(layers, contexts=contexts)
