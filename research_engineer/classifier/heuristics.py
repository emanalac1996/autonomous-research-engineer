"""Heuristic engine for innovation-type classification.

Loads classification rules from the ArtifactRegistry and applies a
best-score-wins algorithm to classify papers. Rules are YAML-defined
evaluation rubrics that can be hot-swapped via the artifact system.
"""

from __future__ import annotations

import yaml

from agent_factors.artifacts import ArtifactRegistry, ArtifactType

from research_engineer.classifier.confidence import (
    check_escalation,
    compute_confidence,
)
from research_engineer.classifier.seed_artifact import (
    CLASSIFIER_DOMAIN,
    register_seed_artifact,
)
from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary, SectionType
from research_engineer.comprehension.topology import TopologyChange


def load_heuristic_rules(registry: ArtifactRegistry) -> list[dict]:
    """Load classification heuristic rules from the artifact registry.

    Auto-registers the seed artifact if no evaluation_rubric exists
    in the classifier domain.

    Args:
        registry: The artifact registry to query.

    Returns:
        List of rule dicts sorted by priority (ascending).
    """
    entries = registry.query(
        artifact_type=ArtifactType.evaluation_rubric,
        domain=CLASSIFIER_DOMAIN,
    )

    if not entries:
        register_seed_artifact(registry)
        entries = registry.query(
            artifact_type=ArtifactType.evaluation_rubric,
            domain=CLASSIFIER_DOMAIN,
        )

    if not entries:
        return []

    # Use the first (most recently registered) artifact
    content = registry.get_content(entries[0].artifact_id)
    if not content:
        return []

    data = yaml.safe_load(content)
    rules = data.get("rules", [])
    return sorted(rules, key=lambda r: r.get("priority", 999))


def _build_analysis_text(summary: ComprehensionSummary) -> str:
    """Build combined text for keyword matching from summary fields."""
    parts = [summary.transformation_proposed]
    for section in summary.sections:
        if section.section_type in {SectionType.abstract, SectionType.method}:
            parts.append(section.content)
    return " ".join(parts)


def _compute_rule_score(
    rule: dict,
    topology: TopologyChange,
    analysis_text: str,
) -> float:
    """Compute match strength for a single rule against the input signals.

    Returns:
        match_strength in [0.0, 1.0].
    """
    signals = rule.get("signals", {})

    # Topology match score
    rule_topology = signals.get("topology_change_type", "")
    if isinstance(rule_topology, str):
        rule_topology_set = {rule_topology}
    else:
        rule_topology_set = set(rule_topology)

    topology_match_score = 1.0 if topology.change_type.value in rule_topology_set else 0.0

    # Keyword match score
    keywords = signals.get("transformation_keywords", [])
    text_lower = analysis_text.lower()
    matched_count = sum(1 for kw in keywords if kw.lower() in text_lower)
    keyword_match_score = min(matched_count / 2.0, 1.0) if keywords else 0.0

    # Combined match strength
    if keywords:
        match_strength = (topology_match_score + keyword_match_score) / 2.0
    else:
        # Fallback rules with no keywords rely solely on topology
        match_strength = topology_match_score * 0.5

    return match_strength


def classify(
    summary: ComprehensionSummary,
    topology: TopologyChange,
    manifest_evidence: list[str],
    registry: ArtifactRegistry,
) -> ClassificationResult:
    """Classify a paper's innovation type using artifact-backed heuristics.

    Args:
        summary: The comprehension summary from paper parsing.
        topology: Topology change analysis result.
        manifest_evidence: List of manifest match descriptions.
        registry: Artifact registry containing classification heuristics.

    Returns:
        ClassificationResult with type, confidence, rationale, and evidence.
    """
    rules = load_heuristic_rules(registry)
    analysis_text = _build_analysis_text(summary)

    best_rule = None
    best_weighted_score = -1.0
    best_match_strength = 0.0

    for rule in rules:
        match_strength = _compute_rule_score(rule, topology, analysis_text)
        weight = rule.get("weight", 0.5)
        weighted_score = match_strength * weight

        if weighted_score > best_weighted_score or (
            weighted_score == best_weighted_score
            and (best_rule is None or rule.get("priority", 999) < best_rule.get("priority", 999))
        ):
            best_weighted_score = weighted_score
            best_match_strength = match_strength
            best_rule = rule

    if best_rule is None:
        # Fallback: no rules matched at all
        innovation_type = InnovationType.parameter_tuning
        rationale = "No heuristic rules matched; defaulting to parameter_tuning"
        best_match_strength = 0.0
    else:
        innovation_type = InnovationType(best_rule["classification"])
        rationale = (
            f"Rule '{best_rule['rule_id']}' matched with strength "
            f"{best_match_strength:.2f}: {best_rule.get('description', '')}"
        )

    topology_signal = (
        f"{topology.change_type.value} with confidence {topology.confidence:.2f}"
    )

    confidence = compute_confidence(
        heuristic_match_strength=best_match_strength,
        topology=topology,
        innovation_type=innovation_type,
        manifest_evidence_count=len(manifest_evidence),
    )

    escalation = check_escalation(confidence, innovation_type)

    return ClassificationResult(
        innovation_type=innovation_type,
        confidence=confidence,
        rationale=rationale,
        topology_signal=topology_signal,
        manifest_evidence=manifest_evidence,
        escalation_trigger=escalation,
    )
