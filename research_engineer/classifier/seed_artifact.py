"""Seed heuristic artifact for innovation-type classification.

Stores the 5-rule classification heuristic as a YAML artifact in the
ArtifactRegistry (type: evaluation_rubric). Rules are loaded at runtime
by the heuristic engine, enabling hot-swap and version evolution.
"""

from __future__ import annotations

import yaml
from agent_factors.artifacts import ArtifactRegistry, ArtifactType

from research_engineer.classifier.types import InnovationType

CLASSIFIER_DOMAIN = "research_engineer_classification"
SEED_ARTIFACT_NAME = "innovation_type_classification_heuristic"
SEED_ARTIFACT_PROVENANCE = "comm-018"

_SEED_YAML = """\
rules:
  - rule_id: rule_parameter_tuning
    description: >-
      Detects parameter tuning papers: no topology change, keywords related
      to tuning, adjusting, or grid search over existing parameters.
    classification: parameter_tuning
    priority: 1
    signals:
      topology_change_type: none
      transformation_keywords:
        - parameter
        - tune
        - tuning
        - adjust
        - grid search
        - hyperparameter
        - weight selection
        - varying
        - optimize parameter
      manifest_only: true
    weight: 0.9

  - rule_id: rule_modular_swap
    description: >-
      Detects modular swap papers: component_swap topology, keywords related
      to replacing, swapping, or substituting a single component.
    classification: modular_swap
    priority: 2
    signals:
      topology_change_type: component_swap
      transformation_keywords:
        - replace
        - replacing
        - swap
        - swapping
        - substitute
        - substituting
        - instead of
        - alternative to
        - drop-in replacement
    weight: 0.9

  - rule_id: rule_architectural_innovation
    description: >-
      Detects architectural innovation papers: stage_addition or
      flow_restructuring topology with new evaluation methodology,
      novel primitives, or knowledge graph infrastructure.
    classification: architectural_innovation
    priority: 3
    signals:
      topology_change_type:
        - stage_addition
        - flow_restructuring
      transformation_keywords:
        - new evaluation methodology
        - novel
        - knowledge graph
        - new primitive
        - new abstraction
        - graph construction
        - intermediate representation
      has_new_evaluation: true
    weight: 0.85

  - rule_id: rule_pipeline_restructuring
    description: >-
      Detects pipeline restructuring papers: topology change with
      restructuring, new stage, or reordering keywords.
    classification: pipeline_restructuring
    priority: 4
    signals:
      topology_change_type:
        - stage_addition
        - stage_removal
        - flow_restructuring
      transformation_keywords:
        - restructure
        - restructuring
        - new stage
        - new pipeline stage
        - reorder
        - rearrange
        - intermediate representation
        - additional step
    weight: 0.85

  - rule_id: rule_pipeline_restructuring_fallback
    description: >-
      Fallback for any topology-changing paper not caught by more
      specific rules above.
    classification: pipeline_restructuring
    priority: 5
    signals:
      topology_change_type:
        - stage_addition
        - stage_removal
        - flow_restructuring
      transformation_keywords: []
    weight: 0.6
"""


def get_seed_heuristic_content() -> str:
    """Return the seed heuristic YAML content."""
    return _SEED_YAML


def validate_heuristic_yaml(content: str) -> dict:
    """Parse and validate heuristic YAML content.

    Args:
        content: YAML string to validate.

    Returns:
        Parsed dict with validated structure.

    Raises:
        ValueError: If content is invalid or missing required fields.
    """
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("Heuristic YAML must be a mapping")
    if "rules" not in data:
        raise ValueError("Heuristic YAML must have a 'rules' key")

    required_keys = {"rule_id", "classification", "priority", "signals"}
    valid_types = {t.value for t in InnovationType}

    for i, rule in enumerate(data["rules"]):
        missing = required_keys - set(rule.keys())
        if missing:
            raise ValueError(
                f"Rule {i} missing required keys: {missing}"
            )
        if rule["classification"] not in valid_types:
            raise ValueError(
                f"Rule {i} has invalid classification: {rule['classification']}"
            )

    return data


def register_seed_artifact(registry: ArtifactRegistry) -> str:
    """Register the seed heuristic artifact if not already present.

    Args:
        registry: ArtifactRegistry instance to register into.

    Returns:
        The artifact_id of the (existing or newly registered) artifact.
    """
    # Check if already registered
    existing = registry.query(
        artifact_type=ArtifactType.evaluation_rubric,
        domain=CLASSIFIER_DOMAIN,
    )
    if existing:
        return existing[0].artifact_id

    entry = registry.register(
        artifact_type=ArtifactType.evaluation_rubric,
        name=SEED_ARTIFACT_NAME,
        description=(
            "5-rule heuristic for classifying research papers into "
            "parameter_tuning, modular_swap, pipeline_restructuring, "
            "or architectural_innovation innovation types."
        ),
        content=get_seed_heuristic_content(),
        domain=CLASSIFIER_DOMAIN,
        author="autonomous-research-engineer",
        provenance=SEED_ARTIFACT_PROVENANCE,
        source_description="Seed artifact from blueprint comm-018",
        tags=["classifier", "heuristic", "seed"],
    )
    return entry.artifact_id
