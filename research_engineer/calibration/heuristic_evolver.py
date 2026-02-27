"""Heuristic evolver: analyze misclassifications and propose rule mutations.

After each calibration batch, identifies systematic weaknesses in the
current heuristic rules and proposes concrete mutations (keyword additions,
weight adjustments) that can be applied to the artifact registry.
"""

from __future__ import annotations

from collections import defaultdict

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_factors.artifacts import ArtifactRegistry, ArtifactType

from research_engineer.calibration.tracker import AccuracyTracker
from research_engineer.classifier.seed_artifact import (
    CLASSIFIER_DOMAIN,
    validate_heuristic_yaml,
)
from research_engineer.classifier.types import InnovationType


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

VALID_MUTATION_TYPES = {"add_keyword", "adjust_weight", "add_rule", "adjust_priority"}


class MisclassificationPattern(BaseModel):
    """A detected pattern of misclassification."""

    model_config = ConfigDict()

    predicted_type: InnovationType
    actual_type: InnovationType
    count: int
    fraction_of_total_errors: float = Field(ge=0.0, le=1.0)
    example_paper_ids: list[str] = Field(default_factory=list)
    avg_confidence: float = Field(ge=0.0, le=1.0)


class RuleMutation(BaseModel):
    """A proposed mutation to a heuristic rule."""

    model_config = ConfigDict()

    mutation_type: str
    target_rule_id: str | None = None
    description: str
    parameter: str
    old_value: str | None = None
    new_value: str

    @field_validator("mutation_type")
    @classmethod
    def valid_mutation_type(cls, v: str) -> str:
        if v not in VALID_MUTATION_TYPES:
            raise ValueError(f"mutation_type must be one of {VALID_MUTATION_TYPES}")
        return v


class EvolutionProposal(BaseModel):
    """Complete proposal for evolving heuristic rules."""

    model_config = ConfigDict()

    patterns: list[MisclassificationPattern]
    mutations: list[RuleMutation]
    expected_accuracy_improvement: float
    requires_human_review: bool = True
    rationale: str


class EvolutionResult(BaseModel):
    """Result of applying an evolution proposal."""

    model_config = ConfigDict()

    proposal: EvolutionProposal
    applied: bool
    new_artifact_version: int | None = None
    artifact_id: str | None = None


# ---------------------------------------------------------------------------
# Rule ID mapping for innovation types
# ---------------------------------------------------------------------------

_TYPE_TO_RULE_ID: dict[str, str] = {
    "parameter_tuning": "rule_parameter_tuning",
    "modular_swap": "rule_modular_swap",
    "pipeline_restructuring": "rule_pipeline_restructuring",
    "architectural_innovation": "rule_architectural_innovation",
}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyze_misclassifications(
    tracker: AccuracyTracker,
) -> list[MisclassificationPattern]:
    """Identify systematic misclassification patterns.

    Groups misclassifications by (predicted_type, actual_type) pair,
    computes frequency and average confidence for each pattern.

    Args:
        tracker: The accuracy tracker with classification records.

    Returns:
        List of MisclassificationPattern sorted by count descending.
    """
    misses = tracker.misclassifications()
    if not misses:
        return []

    total_errors = len(misses)

    # Group by (predicted, actual)
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for rec in misses:
        key = (rec.predicted_type.value, rec.ground_truth_type.value)
        groups[key].append(rec)

    patterns = []
    for (pred, actual), recs in groups.items():
        avg_conf = sum(r.confidence for r in recs) / len(recs)
        patterns.append(
            MisclassificationPattern(
                predicted_type=InnovationType(pred),
                actual_type=InnovationType(actual),
                count=len(recs),
                fraction_of_total_errors=len(recs) / total_errors,
                example_paper_ids=[r.paper_id for r in recs[:3]],
                avg_confidence=avg_conf,
            )
        )

    return sorted(patterns, key=lambda p: p.count, reverse=True)


# ---------------------------------------------------------------------------
# Mutation proposal
# ---------------------------------------------------------------------------


def propose_mutations(
    patterns: list[MisclassificationPattern],
    registry: ArtifactRegistry,
) -> EvolutionProposal:
    """Propose heuristic rule mutations based on misclassification patterns.

    Strategy:
    - For each pattern, propose adding keywords to the actual_type's rule
      to improve its detection.
    - If average confidence on misclassification is low (< 0.6),
      propose lowering the predicted_type's rule weight.

    Args:
        patterns: Detected misclassification patterns.
        registry: Artifact registry containing current heuristic rules.

    Returns:
        EvolutionProposal with suggested mutations.
    """
    mutations: list[RuleMutation] = []

    for pattern in patterns:
        actual_rule_id = _TYPE_TO_RULE_ID.get(pattern.actual_type.value)
        pred_rule_id = _TYPE_TO_RULE_ID.get(pattern.predicted_type.value)

        # Suggest adding a keyword to the actual type's rule
        if actual_rule_id:
            keyword_hint = f"{pattern.actual_type.value}_distinguisher"
            mutations.append(
                RuleMutation(
                    mutation_type="add_keyword",
                    target_rule_id=actual_rule_id,
                    description=(
                        f"Add keyword to {actual_rule_id} to reduce "
                        f"misclassification from {pattern.predicted_type.value}"
                    ),
                    parameter="signals.transformation_keywords",
                    new_value=keyword_hint,
                )
            )

        # If low confidence, suggest weight adjustment
        if pattern.avg_confidence < 0.6 and pred_rule_id:
            mutations.append(
                RuleMutation(
                    mutation_type="adjust_weight",
                    target_rule_id=pred_rule_id,
                    description=(
                        f"Lower weight of {pred_rule_id} due to low-confidence "
                        f"misclassifications (avg={pattern.avg_confidence:.2f})"
                    ),
                    parameter="weight",
                    old_value="current",
                    new_value="0.7",
                )
            )

    # Estimate improvement
    total_patterns = sum(p.count for p in patterns)
    expected_improvement = 0.05 * len(mutations) if mutations else 0.0

    rationale_parts = [
        f"Detected {len(patterns)} misclassification pattern(s) "
        f"covering {total_patterns} error(s)."
    ]
    if mutations:
        rationale_parts.append(
            f"Proposing {len(mutations)} mutation(s) to improve accuracy."
        )

    return EvolutionProposal(
        patterns=patterns,
        mutations=mutations,
        expected_accuracy_improvement=min(expected_improvement, 1.0),
        requires_human_review=True,
        rationale=" ".join(rationale_parts),
    )


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def apply_evolution(
    proposal: EvolutionProposal,
    registry: ArtifactRegistry,
    auto_apply: bool = False,
) -> EvolutionResult:
    """Apply proposed mutations to the artifact registry.

    If auto_apply=False (default), returns the proposal without applying.
    If auto_apply=True, loads current heuristic YAML, applies mutations,
    validates, and writes as new version.

    Args:
        proposal: The evolution proposal to apply.
        registry: The artifact registry to update.
        auto_apply: Whether to automatically apply mutations.

    Returns:
        EvolutionResult with applied status and new version info.
    """
    if not auto_apply:
        return EvolutionResult(
            proposal=proposal,
            applied=False,
        )

    # Load current heuristic YAML
    entries = registry.query(
        artifact_type=ArtifactType.evaluation_rubric,
        domain=CLASSIFIER_DOMAIN,
    )

    if not entries:
        return EvolutionResult(
            proposal=proposal,
            applied=False,
        )

    entry = entries[0]
    content = registry.get_content(entry.artifact_id)
    if not content:
        return EvolutionResult(
            proposal=proposal,
            applied=False,
        )

    data = yaml.safe_load(content)
    rules = data.get("rules", [])

    # Apply mutations
    for mutation in proposal.mutations:
        if mutation.mutation_type == "add_keyword" and mutation.target_rule_id:
            for rule in rules:
                if rule.get("rule_id") == mutation.target_rule_id:
                    keywords = rule.get("signals", {}).get("transformation_keywords", [])
                    if mutation.new_value not in keywords:
                        keywords.append(mutation.new_value)
                    rule.setdefault("signals", {})["transformation_keywords"] = keywords
                    break

        elif mutation.mutation_type == "adjust_weight" and mutation.target_rule_id:
            for rule in rules:
                if rule.get("rule_id") == mutation.target_rule_id:
                    try:
                        rule["weight"] = float(mutation.new_value)
                    except ValueError:
                        pass
                    break

        elif mutation.mutation_type == "adjust_priority" and mutation.target_rule_id:
            for rule in rules:
                if rule.get("rule_id") == mutation.target_rule_id:
                    try:
                        rule["priority"] = int(mutation.new_value)
                    except ValueError:
                        pass
                    break

        elif mutation.mutation_type == "add_rule":
            new_rule = yaml.safe_load(mutation.new_value)
            if isinstance(new_rule, dict):
                rules.append(new_rule)

    data["rules"] = rules
    new_content = yaml.dump(data, default_flow_style=False, sort_keys=False)

    # Validate
    validate_heuristic_yaml(new_content)

    # Write new version
    registry.update(
        artifact_id=entry.artifact_id,
        content=new_content,
        author="calibration-evolver",
        source_description="Heuristic evolution from misclassification analysis",
    )

    return EvolutionResult(
        proposal=proposal,
        applied=True,
        artifact_id=entry.artifact_id,
    )
