"""Feasibility gate orchestrator: assess implementability of classified papers.

Takes a ComprehensionSummary + ClassificationResult and runs per-innovation-type
gating logic against live codebase manifests. Produces a FeasibilityResult with
one of 4 statuses: FEASIBLE, FEASIBLE_WITH_ADAPTATION, ESCALATE, NOT_FEASIBLE.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary
from research_engineer.feasibility.blast_radius import (
    BlastRadiusReport,
    RiskLevel,
    compute_blast_radius,
)
from research_engineer.feasibility.dependency_graph import (
    DependencyGraph,
    build_dependency_graph,
)
from research_engineer.feasibility.manifest_checker import (
    ManifestCheckResult,
    check_operations,
    load_all_manifests,
)
from research_engineer.feasibility.test_coverage import (
    CoverageAssessment,
    assess_test_coverage,
)


class FeasibilityStatus(str, Enum):
    """Outcome of the feasibility gate."""

    FEASIBLE = "FEASIBLE"
    FEASIBLE_WITH_ADAPTATION = "FEASIBLE_WITH_ADAPTATION"
    ESCALATE = "ESCALATE"
    NOT_FEASIBLE = "NOT_FEASIBLE"


class FeasibilityResult(BaseModel):
    """Full result of feasibility assessment."""

    model_config = ConfigDict()

    status: FeasibilityStatus
    innovation_type: InnovationType
    manifest_check: ManifestCheckResult
    blast_radius: BlastRadiusReport | None = None
    coverage: CoverageAssessment | None = None
    rationale: str
    escalation_trigger: EscalationTrigger | None = None
    adaptation_notes: list[str] = Field(default_factory=list)

    @field_validator("rationale")
    @classmethod
    def rationale_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rationale must not be empty")
        return v


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_operations_list(summary: ComprehensionSummary) -> list[str]:
    """Extract operations to check from a ComprehensionSummary."""
    ops: list[str] = []
    ops.extend(summary.inputs_required)
    ops.extend(summary.outputs_produced)
    ops.extend(summary.paper_terms)
    return ops


def _gate_parameter_tuning(
    manifest_check: ManifestCheckResult,
    classification: ClassificationResult,
) -> tuple[FeasibilityStatus, str, EscalationTrigger | None, list[str]]:
    """Gate logic for parameter_tuning: manifest check only."""
    coverage = manifest_check.coverage_ratio

    if classification.confidence < 0.6:
        return (
            FeasibilityStatus.ESCALATE,
            f"Classification confidence {classification.confidence:.2f} below threshold",
            EscalationTrigger.confidence_below_threshold,
            [],
        )

    if coverage == 0.0:
        return (
            FeasibilityStatus.NOT_FEASIBLE,
            "No operations matched in manifests",
            None,
            [],
        )

    if coverage >= 0.5:
        return (
            FeasibilityStatus.FEASIBLE,
            f"Manifest coverage {coverage:.2f} sufficient for parameter tuning",
            None,
            [],
        )

    return (
        FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
        f"Manifest coverage {coverage:.2f} partial; adaptation may be needed",
        None,
        [f"Only {coverage:.0%} of operations found in manifests"],
    )


def _gate_modular_swap(
    manifest_check: ManifestCheckResult,
    blast_radius: BlastRadiusReport,
    classification: ClassificationResult,
) -> tuple[FeasibilityStatus, str, EscalationTrigger | None, list[str]]:
    """Gate logic for modular_swap: manifest + blast radius."""
    coverage = manifest_check.coverage_ratio
    risk = blast_radius.risk_level

    if classification.confidence < 0.6 or risk == RiskLevel.critical:
        trigger = (
            EscalationTrigger.confidence_below_threshold
            if classification.confidence < 0.6
            else EscalationTrigger.novel_primitive
        )
        return (
            FeasibilityStatus.ESCALATE,
            f"Modular swap escalated: confidence={classification.confidence:.2f}, risk={risk.value}",
            trigger,
            [],
        )

    if coverage == 0.0:
        return (
            FeasibilityStatus.NOT_FEASIBLE,
            "No operations matched in manifests for modular swap",
            None,
            [],
        )

    if coverage >= 0.5 and risk in (RiskLevel.low, RiskLevel.medium):
        return (
            FeasibilityStatus.FEASIBLE,
            f"Modular swap feasible: coverage={coverage:.2f}, risk={risk.value}",
            None,
            [],
        )

    notes = []
    if coverage < 0.5:
        notes.append(f"Manifest coverage {coverage:.0%} below 50%")
    if risk not in (RiskLevel.low, RiskLevel.medium):
        notes.append(f"Blast radius risk is {risk.value}")
    return (
        FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
        f"Modular swap feasible with adaptation: coverage={coverage:.2f}, risk={risk.value}",
        None,
        notes,
    )


def _gate_pipeline_restructuring(
    manifest_check: ManifestCheckResult,
    blast_radius: BlastRadiusReport,
    test_coverage: CoverageAssessment,
    classification: ClassificationResult,
) -> tuple[FeasibilityStatus, str, EscalationTrigger | None, list[str]]:
    """Gate logic for pipeline_restructuring: full analysis."""
    coverage = manifest_check.coverage_ratio
    risk = blast_radius.risk_level
    test_cov = test_coverage.coverage_ratio

    if classification.confidence < 0.6 or risk == RiskLevel.critical:
        trigger = (
            EscalationTrigger.confidence_below_threshold
            if classification.confidence < 0.6
            else EscalationTrigger.novel_primitive
        )
        return (
            FeasibilityStatus.ESCALATE,
            f"Pipeline restructuring escalated: confidence={classification.confidence:.2f}, risk={risk.value}",
            trigger,
            [],
        )

    if coverage == 0.0:
        return (
            FeasibilityStatus.NOT_FEASIBLE,
            "No operations matched for pipeline restructuring",
            None,
            [],
        )

    if coverage >= 0.5 and risk in (RiskLevel.low, RiskLevel.medium) and test_cov >= 0.5:
        return (
            FeasibilityStatus.FEASIBLE,
            f"Pipeline restructuring feasible: coverage={coverage:.2f}, risk={risk.value}, test_cov={test_cov:.2f}",
            None,
            [],
        )

    notes = []
    if coverage < 0.5:
        notes.append(f"Manifest coverage {coverage:.0%} below 50%")
    if risk not in (RiskLevel.low, RiskLevel.medium):
        notes.append(f"Blast radius risk is {risk.value}")
    if test_cov < 0.5:
        notes.append(f"Test coverage {test_cov:.0%} below 50%")
    return (
        FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
        f"Pipeline restructuring feasible with adaptation: coverage={coverage:.2f}, risk={risk.value}, test_cov={test_cov:.2f}",
        None,
        notes,
    )


def _gate_architectural_innovation(
    manifest_check: ManifestCheckResult,
    blast_radius: BlastRadiusReport,
    test_coverage: CoverageAssessment,
    classification: ClassificationResult,
) -> tuple[FeasibilityStatus, str, EscalationTrigger | None, list[str]]:
    """Gate logic for architectural_innovation: strictest requirements."""
    coverage = manifest_check.coverage_ratio
    risk = blast_radius.risk_level
    test_cov = test_coverage.coverage_ratio
    total_ops = len(manifest_check.matched_operations) + len(manifest_check.unmatched_operations)
    unmatched_ratio = len(manifest_check.unmatched_operations) / max(total_ops, 1)

    # NOT_FEASIBLE: coverage == 0 or >80% unmatched
    if coverage == 0.0 or unmatched_ratio > 0.8:
        return (
            FeasibilityStatus.NOT_FEASIBLE,
            f"Architectural innovation not feasible: coverage={coverage:.2f}, unmatched={unmatched_ratio:.0%}",
            None,
            [],
        )

    # ESCALATE: >50% unmatched or low confidence
    if unmatched_ratio > 0.5 or classification.confidence < 0.6:
        trigger = (
            EscalationTrigger.novel_primitive
            if unmatched_ratio > 0.5
            else EscalationTrigger.confidence_below_threshold
        )
        return (
            FeasibilityStatus.ESCALATE,
            f"Architectural innovation escalated: unmatched={unmatched_ratio:.0%}, confidence={classification.confidence:.2f}",
            trigger,
            [],
        )

    # FEASIBLE: strict requirements
    if coverage >= 0.5 and risk in (RiskLevel.low, RiskLevel.medium) and test_cov >= 0.7:
        return (
            FeasibilityStatus.FEASIBLE,
            f"Architectural innovation feasible: coverage={coverage:.2f}, risk={risk.value}, test_cov={test_cov:.2f}",
            None,
            [],
        )

    # FEASIBLE_WITH_ADAPTATION
    notes = []
    if coverage < 0.5:
        notes.append(f"Manifest coverage {coverage:.0%} below 50%")
    if risk not in (RiskLevel.low, RiskLevel.medium):
        notes.append(f"Blast radius risk is {risk.value}")
    if test_cov < 0.7:
        notes.append(f"Test coverage {test_cov:.0%} below 70%")
    return (
        FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
        f"Architectural innovation feasible with adaptation: coverage={coverage:.2f}, risk={risk.value}, test_cov={test_cov:.2f}",
        None,
        notes,
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def assess_feasibility(
    summary: ComprehensionSummary,
    classification: ClassificationResult,
    manifests_dir: Path,
) -> FeasibilityResult:
    """Assess feasibility of a classified paper against codebase state.

    Runs per-innovation-type gating logic:
    - parameter_tuning: manifest check only
    - modular_swap: manifest + blast radius
    - pipeline_restructuring: full (manifest + blast radius + test coverage)
    - architectural_innovation: full with strictest thresholds

    Args:
        summary: Paper comprehension summary.
        classification: Innovation-type classification result.
        manifests_dir: Path to directory containing manifest YAML files.

    Returns:
        FeasibilityResult with status, rationale, and sub-analyses.
    """
    # 1. Load manifests and check operations
    manifests = load_all_manifests(manifests_dir)
    operations = _build_operations_list(summary)
    manifest_check = check_operations(operations, manifests)

    innovation_type = classification.innovation_type

    # 2. Parameter tuning: manifest only
    if innovation_type == InnovationType.parameter_tuning:
        status, rationale, trigger, notes = _gate_parameter_tuning(
            manifest_check, classification
        )
        return FeasibilityResult(
            status=status,
            innovation_type=innovation_type,
            manifest_check=manifest_check,
            rationale=rationale,
            escalation_trigger=trigger,
            adaptation_notes=notes,
        )

    # 3. Build dependency graph for blast radius
    dep_graph = build_dependency_graph(manifests_dir)

    # Identify target nodes from matched operations
    target_nodes = []
    for match in manifest_check.matched_operations:
        if match.function_name:
            node_id = f"{match.repo_name}::{match.module_path}.{match.function_name}"
        elif match.class_name:
            node_id = f"{match.repo_name}::{match.module_path}.{match.class_name}"
        else:
            continue
        if node_id in dep_graph.graph:
            target_nodes.append(node_id)

    blast_radius = compute_blast_radius(target_nodes, dep_graph)

    # 4. Modular swap: manifest + blast radius
    if innovation_type == InnovationType.modular_swap:
        status, rationale, trigger, notes = _gate_modular_swap(
            manifest_check, blast_radius, classification
        )
        return FeasibilityResult(
            status=status,
            innovation_type=innovation_type,
            manifest_check=manifest_check,
            blast_radius=blast_radius,
            rationale=rationale,
            escalation_trigger=trigger,
            adaptation_notes=notes,
        )

    # 5. Full analysis: test coverage needed
    affected_funcs = blast_radius.affected_functions
    test_coverage = assess_test_coverage(affected_funcs, dep_graph)

    # 6. Pipeline restructuring
    if innovation_type == InnovationType.pipeline_restructuring:
        status, rationale, trigger, notes = _gate_pipeline_restructuring(
            manifest_check, blast_radius, test_coverage, classification
        )
        return FeasibilityResult(
            status=status,
            innovation_type=innovation_type,
            manifest_check=manifest_check,
            blast_radius=blast_radius,
            coverage=test_coverage,
            rationale=rationale,
            escalation_trigger=trigger,
            adaptation_notes=notes,
        )

    # 7. Architectural innovation (strictest)
    status, rationale, trigger, notes = _gate_architectural_innovation(
        manifest_check, blast_radius, test_coverage, classification
    )
    return FeasibilityResult(
        status=status,
        innovation_type=innovation_type,
        manifest_check=manifest_check,
        blast_radius=blast_radius,
        coverage=test_coverage,
        rationale=rationale,
        escalation_trigger=trigger,
        adaptation_notes=notes,
    )
