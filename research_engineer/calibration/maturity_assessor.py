"""Maturity assessor: evaluate maturity gate eligibility for classification pipeline.

Bridges AccuracyTracker metrics with agent-factors maturity gate infrastructure
to determine when the agent can advance from foundational to empirical maturity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agent_factors.artifacts import ArtifactRegistry
from agent_factors.g_layer.escalation import EscalationTrigger
from agent_factors.g_layer.maturity import DEFAULT_GATES, check_maturity_eligibility

from research_engineer.calibration.tracker import AccuracyTracker


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CalibrationEvidence(BaseModel):
    """Evidence gathered from the calibration pipeline for maturity assessment."""

    model_config = ConfigDict()

    total_papers_evaluated: int
    overall_accuracy: float = Field(ge=0.0, le=1.0)
    per_type_f1_scores: dict[str, float]
    has_calibration_set: bool
    artifact_count: int
    worst_type_f1: float
    confidence_accuracy_correlation: float


class MaturityAssessment(BaseModel):
    """Result of maturity assessment for the classification pipeline."""

    model_config = ConfigDict()

    repo: str
    current_level: str
    target_level: str
    recommendation: str  # "ready", "not_ready", "insufficient_data"
    evidence: CalibrationEvidence
    unmet_requirements: list[str] = Field(default_factory=list)
    escalation_trigger: EscalationTrigger | None = None


# ---------------------------------------------------------------------------
# Assessment function
# ---------------------------------------------------------------------------

MIN_RECORDS_FOR_ASSESSMENT = 5
MIN_TYPE_F1_THRESHOLD = 0.6


def assess_maturity(
    tracker: AccuracyTracker,
    registry: ArtifactRegistry,
    repo_name: str = "autonomous-research-engineer",
    current_level: str = "foundational",
) -> MaturityAssessment:
    """Assess maturity gate eligibility for the classification pipeline.

    Composes AccuracyTracker metrics with agent-factors maturity gate
    infrastructure to evaluate readiness for level advancement.

    Args:
        tracker: The accuracy tracker with classification records.
        registry: The artifact registry for counting artifacts.
        repo_name: Repository name for the assessment.
        current_level: Current maturity level.

    Returns:
        MaturityAssessment with recommendation and evidence.
    """
    report = tracker.report()

    # Build per-type F1 scores dict
    per_type_f1: dict[str, float] = {}
    for pta in report.per_type:
        per_type_f1[pta.innovation_type.value] = pta.f1_score

    worst_f1 = min(per_type_f1.values()) if per_type_f1 else 0.0

    # Count artifacts
    counts = registry.count_by_type()
    artifact_count = sum(counts.values())

    # Build evidence
    has_calibration = report.total_records >= MIN_RECORDS_FOR_ASSESSMENT
    evidence = CalibrationEvidence(
        total_papers_evaluated=report.total_records,
        overall_accuracy=report.overall_accuracy,
        per_type_f1_scores=per_type_f1,
        has_calibration_set=has_calibration,
        artifact_count=artifact_count,
        worst_type_f1=worst_f1,
        confidence_accuracy_correlation=report.confidence_accuracy_correlation,
    )

    # Determine target level
    target_level = "empirical" if current_level == "foundational" else "validated"

    # Insufficient data check
    if report.total_records < MIN_RECORDS_FOR_ASSESSMENT:
        return MaturityAssessment(
            repo=repo_name,
            current_level=current_level,
            target_level=target_level,
            recommendation="insufficient_data",
            evidence=evidence,
            unmet_requirements=[
                f"Need {MIN_RECORDS_FOR_ASSESSMENT} evaluations, "
                f"have {report.total_records}"
            ],
        )

    # Get the appropriate gate
    gate_key = f"{current_level}_to_{target_level}"
    gate = DEFAULT_GATES.get(gate_key, DEFAULT_GATES["foundational_to_empirical"])

    # Check agent-factors maturity eligibility
    eligible, unmet = check_maturity_eligibility(
        session_count=report.total_records,
        approval_rate=report.overall_accuracy,
        error_rate=1.0 - report.overall_accuracy,
        gate=gate,
        artifact_count=artifact_count,
        has_calibration=has_calibration,
        has_human_review=False,
    )

    # Domain-specific check: no blind spots
    escalation = None
    if worst_f1 < MIN_TYPE_F1_THRESHOLD:
        # Find worst type for message
        worst_type = min(per_type_f1, key=per_type_f1.get)
        unmet.append(
            f"Worst per-type F1 is {worst_f1:.2f} ({worst_type}), "
            f"need >= {MIN_TYPE_F1_THRESHOLD}"
        )
        eligible = False
        escalation = EscalationTrigger.maturity_insufficient

    if not eligible:
        return MaturityAssessment(
            repo=repo_name,
            current_level=current_level,
            target_level=target_level,
            recommendation="not_ready",
            evidence=evidence,
            unmet_requirements=unmet,
            escalation_trigger=escalation,
        )

    return MaturityAssessment(
        repo=repo_name,
        current_level=current_level,
        target_level=target_level,
        recommendation="ready",
        evidence=evidence,
        unmet_requirements=[],
    )
