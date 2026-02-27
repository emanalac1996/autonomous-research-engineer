"""Stage 2: Innovation-type classification with artifact-backed heuristics."""

from research_engineer.classifier.confidence import (
    check_escalation,
    compute_confidence,
)
from research_engineer.classifier.heuristics import classify
from research_engineer.classifier.seed_artifact import register_seed_artifact
from research_engineer.classifier.types import ClassificationResult, InnovationType

__all__ = [
    "ClassificationResult",
    "InnovationType",
    "check_escalation",
    "classify",
    "compute_confidence",
    "register_seed_artifact",
]
