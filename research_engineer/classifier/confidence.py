"""Confidence scoring for innovation-type classification.

Computes a weighted confidence score from heuristic match strength,
topology agreement, and manifest evidence. Triggers escalation when
confidence falls below the threshold.
"""

from __future__ import annotations

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.types import InnovationType
from research_engineer.comprehension.topology import TopologyChange, TopologyChangeType

# Confidence component weights
HEURISTIC_WEIGHT = 0.5
TOPOLOGY_WEIGHT = 0.3
MANIFEST_WEIGHT = 0.2

# Escalation threshold
CONFIDENCE_THRESHOLD = 0.6

# Topology agreement lookup: {innovation_type: {agreeing_topology_types}}
_TOPOLOGY_AGREEMENT: dict[InnovationType, set[TopologyChangeType]] = {
    InnovationType.parameter_tuning: {TopologyChangeType.none},
    InnovationType.modular_swap: {TopologyChangeType.component_swap},
    InnovationType.pipeline_restructuring: {
        TopologyChangeType.stage_addition,
        TopologyChangeType.stage_removal,
        TopologyChangeType.flow_restructuring,
    },
    InnovationType.architectural_innovation: {
        TopologyChangeType.stage_addition,
        TopologyChangeType.flow_restructuring,
    },
}

# Contradictions: parameter_tuning + any topology change is a contradiction
_TOPOLOGY_CONTRADICTIONS: dict[InnovationType, set[TopologyChangeType]] = {
    InnovationType.parameter_tuning: {
        TopologyChangeType.stage_addition,
        TopologyChangeType.stage_removal,
        TopologyChangeType.flow_restructuring,
    },
}


def _topology_agreement_score(
    topology: TopologyChange,
    innovation_type: InnovationType,
) -> float:
    """Score how well the topology signal agrees with the classification.

    Returns:
        1.0 for agreement, 0.3 for neutral mismatch, 0.0 for contradiction.
    """
    agreeing = _TOPOLOGY_AGREEMENT.get(innovation_type, set())
    contradictions = _TOPOLOGY_CONTRADICTIONS.get(innovation_type, set())

    if topology.change_type in contradictions:
        return 0.0
    if topology.change_type in agreeing:
        return 1.0
    return 0.3


def compute_confidence(
    heuristic_match_strength: float,
    topology: TopologyChange,
    innovation_type: InnovationType,
    manifest_evidence_count: int,
) -> float:
    """Compute weighted confidence score for a classification.

    Args:
        heuristic_match_strength: Raw match strength from rule engine (0-1).
        topology: Topology change analysis result.
        innovation_type: The classified innovation type.
        manifest_evidence_count: Number of manifest matches found.

    Returns:
        Confidence score clamped to [0.0, 1.0].
    """
    topology_score = _topology_agreement_score(topology, innovation_type)
    manifest_score = min(manifest_evidence_count / 2.0, 1.0)

    confidence = (
        HEURISTIC_WEIGHT * heuristic_match_strength
        + TOPOLOGY_WEIGHT * topology_score * topology.confidence
        + MANIFEST_WEIGHT * manifest_score
    )

    return max(0.0, min(confidence, 1.0))


def check_escalation(
    confidence: float,
    innovation_type: InnovationType,
) -> EscalationTrigger | None:
    """Check if escalation is needed based on confidence.

    Args:
        confidence: The computed confidence score.
        innovation_type: The classified innovation type (for future use).

    Returns:
        EscalationTrigger if confidence is below threshold, None otherwise.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return EscalationTrigger.confidence_below_threshold
    return None
