"""WU decomposer: break down innovation into Working Units by type.

Decomposes a classified paper innovation into a DAG of Working Units using
type-specific templates. WU counts are bounded by innovation type ranges
and optionally adjusted by historical change pattern data.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent_factors.dag.schema import WorkingUnit, WUStatus
from agent_factors.dag.validator import validate_dag

from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary
from research_engineer.translator.change_patterns import ChangePatternReport
from research_engineer.translator.manifest_targeter import FileTargeting


# Default WU count ranges per innovation type
DEFAULT_WU_RANGES: dict[str, tuple[int, int]] = {
    "parameter_tuning": (1, 3),
    "modular_swap": (3, 5),
    "pipeline_restructuring": (5, 12),
    "architectural_innovation": (8, 20),
}


class DecompositionConfig(BaseModel):
    """Configurable parameters for WU decomposition."""

    wu_count_ranges: dict[str, tuple[int, int]] = Field(
        default_factory=lambda: dict(DEFAULT_WU_RANGES)
    )
    default_effort: str = "1-2 days"
    test_ratio: float = 3.0


def _adjust_wu_count(
    base_count: int,
    innovation_type: str,
    change_patterns: ChangePatternReport | None,
    config: DecompositionConfig,
) -> int:
    """Adjust WU count based on historical change pattern data.

    Nudges the count toward historical average if data is available,
    while staying within the configured range.
    """
    lo, hi = config.wu_count_ranges.get(
        innovation_type, DEFAULT_WU_RANGES.get(innovation_type, (1, 20))
    )

    if change_patterns and innovation_type in change_patterns.by_innovation_type:
        stats = change_patterns.by_innovation_type[innovation_type]
        if stats.sample_count > 0 and stats.avg_wu_count > 0:
            historical = stats.avg_wu_count
            # Nudge toward historical average (30% weight)
            adjusted = base_count * 0.7 + historical * 0.3
            return max(lo, min(hi, round(adjusted)))

    return max(lo, min(hi, base_count))


def _parameter_tuning_wus(
    phase_id: str,
    summary: ComprehensionSummary,
    file_targeting: FileTargeting,
    config: DecompositionConfig,
) -> list[WorkingUnit]:
    """Generate 1-3 WUs for parameter tuning."""
    wus: list[WorkingUnit] = []

    # WU 1: Identify config parameter
    wus.append(WorkingUnit(
        id=f"{phase_id}.1",
        description=f"Identify configuration parameter: {summary.transformation_proposed[:80]}",
        depends_on=[],
        acceptance_criteria="Config parameter identified and documented",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_modified=[ft.source_file for ft in file_targeting.files_modified[:3]],
    ))

    # WU 2: Apply change and validate
    wus.append(WorkingUnit(
        id=f"{phase_id}.2",
        description="Apply parameter change and validate against baseline",
        depends_on=[f"{phase_id}.1"],
        acceptance_criteria="Parameter applied; regression test passes",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # WU 3 (optional): Regression boundary test
    if len(summary.claims) > 0:
        wus.append(WorkingUnit(
            id=f"{phase_id}.3",
            description="Regression test for parameter boundary conditions",
            depends_on=[f"{phase_id}.2"],
            acceptance_criteria="Boundary conditions tested; no regressions",
            effort_estimate=config.default_effort,
            status=WUStatus.planned,
        ))

    return wus


def _modular_swap_wus(
    phase_id: str,
    summary: ComprehensionSummary,
    file_targeting: FileTargeting,
    config: DecompositionConfig,
) -> list[WorkingUnit]:
    """Generate 3-5 WUs for modular swap."""
    wus: list[WorkingUnit] = []

    # WU 1: Study interface contract
    wus.append(WorkingUnit(
        id=f"{phase_id}.1",
        description="Study interface contract of component to be replaced",
        depends_on=[],
        acceptance_criteria="Interface contract documented; inputs/outputs mapped",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_modified=[ft.source_file for ft in file_targeting.files_modified[:2]],
    ))

    # WU 2: Implement replacement component
    wus.append(WorkingUnit(
        id=f"{phase_id}.2",
        description=f"Implement replacement component: {summary.transformation_proposed[:60]}",
        depends_on=[f"{phase_id}.1"],
        acceptance_criteria="Replacement component passes unit tests",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_created=[ft.source_file for ft in file_targeting.files_created[:1]],
    ))

    # WU 3 (optional): Create adapter if interface mismatch
    has_mismatch = len(summary.inputs_required) > 2
    if has_mismatch:
        wus.append(WorkingUnit(
            id=f"{phase_id}.3",
            description="Create adapter layer for interface mismatch",
            depends_on=[f"{phase_id}.2"],
            acceptance_criteria="Adapter bridges old and new interfaces",
            effort_estimate=config.default_effort,
            status=WUStatus.planned,
        ))

    # WU N-1: Integration test
    prev_id = wus[-1].id
    integration_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{integration_n}",
        description="Integration test: verify replacement in full pipeline",
        depends_on=[prev_id],
        acceptance_criteria="End-to-end pipeline passes with replacement component",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # WU N: Regression test
    prev_id = wus[-1].id
    regression_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{regression_n}",
        description="Regression test: verify no unintended side effects",
        depends_on=[prev_id],
        acceptance_criteria="All existing tests pass; no regressions",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    return wus


def _pipeline_restructuring_wus(
    phase_id: str,
    summary: ComprehensionSummary,
    file_targeting: FileTargeting,
    config: DecompositionConfig,
) -> list[WorkingUnit]:
    """Generate 5-12 WUs for pipeline restructuring."""
    wus: list[WorkingUnit] = []

    # WU 1: Analyze current topology
    wus.append(WorkingUnit(
        id=f"{phase_id}.1",
        description="Analyze current pipeline topology and data flow",
        depends_on=[],
        acceptance_criteria="Current topology documented with stage dependencies",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_modified=[ft.source_file for ft in file_targeting.files_modified[:2]],
    ))

    # WU 2: Design new topology
    wus.append(WorkingUnit(
        id=f"{phase_id}.2",
        description="Design new pipeline topology based on paper proposal",
        depends_on=[f"{phase_id}.1"],
        acceptance_criteria="New topology design documented with contract changes",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # WUs 3-N: One WU per new/modified stage (capped at 6)
    stages = summary.inputs_required[:6]
    for i, stage in enumerate(stages, start=3):
        if i > 8:  # Cap at 6 stage WUs
            break
        wus.append(WorkingUnit(
            id=f"{phase_id}.{i}",
            description=f"Implement stage modification: {stage[:50]}",
            depends_on=[f"{phase_id}.2"],
            acceptance_criteria=f"Stage '{stage[:30]}' implemented and unit tested",
            effort_estimate=config.default_effort,
            status=WUStatus.planned,
            files_created=[ft.source_file for ft in file_targeting.files_created[:1]]
            if i == 3 else [],
        ))

    # Update contracts
    contract_n = len(wus) + 1
    prev_ids = [wus[-1].id]
    wus.append(WorkingUnit(
        id=f"{phase_id}.{contract_n}",
        description="Update inter-stage contracts for new topology",
        depends_on=prev_ids,
        acceptance_criteria="All contracts updated; type checks pass",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # Integration test
    integration_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{integration_n}",
        description="Integration test: verify restructured pipeline end-to-end",
        depends_on=[f"{phase_id}.{contract_n}"],
        acceptance_criteria="Full pipeline passes with new topology",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # Regression test
    regression_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{regression_n}",
        description="Regression test: verify no unintended side effects",
        depends_on=[f"{phase_id}.{integration_n}"],
        acceptance_criteria="All existing tests pass; no regressions",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    return wus


def _architectural_innovation_wus(
    phase_id: str,
    summary: ComprehensionSummary,
    file_targeting: FileTargeting,
    config: DecompositionConfig,
) -> list[WorkingUnit]:
    """Generate 8-20 WUs for architectural innovation."""
    wus: list[WorkingUnit] = []

    # WU 1: Define new primitive interfaces
    wus.append(WorkingUnit(
        id=f"{phase_id}.1",
        description="Define new primitive interfaces and type contracts",
        depends_on=[],
        acceptance_criteria="Interface definitions documented; type stubs created",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_modified=[ft.source_file for ft in file_targeting.files_modified[:2]],
    ))

    # WU 2: Scaffold new module structure
    wus.append(WorkingUnit(
        id=f"{phase_id}.2",
        description="Scaffold new module structure for architectural primitives",
        depends_on=[f"{phase_id}.1"],
        acceptance_criteria="Module skeleton created; imports verified",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
        files_created=[ft.source_file for ft in file_targeting.files_created[:2]],
    ))

    # WUs 3-M: One WU per new primitive (capped at 8)
    primitives = (
        summary.inputs_required + summary.outputs_produced
    )[:8]
    for i, primitive in enumerate(primitives, start=3):
        if i > 10:  # Cap at 8 primitive WUs
            break
        wus.append(WorkingUnit(
            id=f"{phase_id}.{i}",
            description=f"Implement primitive: {primitive[:50]}",
            depends_on=[f"{phase_id}.2"],
            acceptance_criteria=f"Primitive '{primitive[:30]}' implemented with unit tests",
            effort_estimate=config.default_effort,
            status=WUStatus.planned,
        ))

    # Build integration layer
    integration_n = len(wus) + 1
    prev_id = wus[-1].id
    wus.append(WorkingUnit(
        id=f"{phase_id}.{integration_n}",
        description="Build integration layer connecting new primitives",
        depends_on=[prev_id],
        acceptance_criteria="Integration layer connects all primitives",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # Pipeline integration
    pipeline_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{pipeline_n}",
        description="Integrate new architecture into existing pipeline",
        depends_on=[f"{phase_id}.{integration_n}"],
        acceptance_criteria="Pipeline accepts new architectural components",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # Test framework
    test_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{test_n}",
        description="Build test framework for new architectural components",
        depends_on=[f"{phase_id}.{pipeline_n}"],
        acceptance_criteria="Test framework covers all new primitives",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # End-to-end validation
    e2e_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{e2e_n}",
        description="End-to-end validation of architectural innovation",
        depends_on=[f"{phase_id}.{test_n}"],
        acceptance_criteria="Full system passes with new architecture; benchmarks met",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    # Documentation and acceptance
    doc_n = len(wus) + 1
    wus.append(WorkingUnit(
        id=f"{phase_id}.{doc_n}",
        description="Documentation and acceptance criteria verification",
        depends_on=[f"{phase_id}.{e2e_n}"],
        acceptance_criteria="Architecture documented; all acceptance criteria met",
        effort_estimate=config.default_effort,
        status=WUStatus.planned,
    ))

    return wus


_TEMPLATE_DISPATCH = {
    InnovationType.parameter_tuning: _parameter_tuning_wus,
    InnovationType.modular_swap: _modular_swap_wus,
    InnovationType.pipeline_restructuring: _pipeline_restructuring_wus,
    InnovationType.architectural_innovation: _architectural_innovation_wus,
}


def decompose(
    summary: ComprehensionSummary,
    classification: ClassificationResult,
    file_targeting: FileTargeting,
    change_patterns: ChangePatternReport | None = None,
    phase_id: str = "1",
    config: DecompositionConfig | None = None,
) -> list[WorkingUnit]:
    """Decompose paper innovation into Working Units.

    Args:
        summary: Paper comprehension output.
        classification: Innovation type classification.
        file_targeting: Manifest-derived file targets.
        change_patterns: Historical pattern data (optional).
        phase_id: Phase ID for WU numbering.
        config: Decomposition configuration (optional).

    Returns:
        List of WorkingUnit models forming a valid DAG.
    """
    if config is None:
        config = DecompositionConfig()

    template_fn = _TEMPLATE_DISPATCH[classification.innovation_type]
    wus = template_fn(phase_id, summary, file_targeting, config)

    # Adjust count based on historical data
    itype = classification.innovation_type.value
    target_count = _adjust_wu_count(len(wus), itype, change_patterns, config)

    # Trim or pad to target count while maintaining DAG validity
    lo, hi = config.wu_count_ranges.get(itype, (1, 20))
    if len(wus) > hi:
        # Trim from the middle (keep first and last WUs)
        keep_first = 2
        keep_last = 2
        mid_count = hi - keep_first - keep_last
        if mid_count > 0:
            mid_wus = wus[keep_first:-keep_last][:mid_count]
            wus = wus[:keep_first] + mid_wus + wus[-keep_last:]
        else:
            wus = wus[:hi]
        # Fix dependencies after trimming
        valid_ids = {wu.id for wu in wus}
        for wu in wus:
            wu.depends_on = [d for d in wu.depends_on if d in valid_ids]
    elif len(wus) < lo:
        # Pad with additional WUs
        while len(wus) < lo:
            n = len(wus) + 1
            prev_id = wus[-1].id if wus else f"{phase_id}.1"
            wus.append(WorkingUnit(
                id=f"{phase_id}.{n}",
                description=f"Additional validation step {n}",
                depends_on=[prev_id],
                acceptance_criteria="Validation complete",
                effort_estimate=config.default_effort,
                status=WUStatus.planned,
            ))

    return wus


def validate_decomposition(
    wus: list[WorkingUnit],
    innovation_type: str,
    config: DecompositionConfig | None = None,
) -> bool:
    """Validate that a decomposition meets WU count constraints and DAG validity.

    Args:
        wus: List of Working Units to validate.
        innovation_type: Innovation type string.
        config: Decomposition configuration (optional).

    Returns:
        True if WU count is in range and DAG is valid.
    """
    if config is None:
        config = DecompositionConfig()

    lo, hi = config.wu_count_ranges.get(
        innovation_type, DEFAULT_WU_RANGES.get(innovation_type, (1, 20))
    )

    if not (lo <= len(wus) <= hi):
        return False

    # Build a minimal Blueprint for DAG validation
    from agent_factors.dag.schema import Blueprint, Phase

    phase_id = wus[0].phase_number if wus else "1"
    blueprint = Blueprint(
        name="validation_check",
        phases=[Phase(id=phase_id, working_units=wus)],
    )

    report = validate_dag(blueprint)
    return report.overall_passed
