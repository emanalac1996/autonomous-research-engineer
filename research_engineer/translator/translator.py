"""Blueprint translator orchestrator: paper + classification → ADR-005 blueprint.

Combines manifest targeting, historical change patterns, WU decomposition,
and DAG validation into a complete translation pipeline.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from agent_factors.dag.schema import (
    Blueprint,
    BlueprintMetadata,
    BlueprintStatus,
    DeferredItem,
    Phase,
)
from agent_factors.dag.validator import DAGValidationReport, validate_dag

from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary
from research_engineer.translator.change_patterns import (
    ChangePatternReport,
    mine_ledger,
)
from research_engineer.translator.manifest_targeter import (
    FileTargeting,
    identify_targets,
)
from research_engineer.translator.wu_decomposer import decompose


class TranslationInput(BaseModel):
    """Bundled input for the translation pipeline."""

    summary: ComprehensionSummary
    classification: ClassificationResult
    manifests_dir: Path | None = None
    ledger_path: Path | None = None
    blueprint_name: str | None = None
    meta_category: str | None = None
    date: str | None = None


class TranslationResult(BaseModel):
    """Complete output of the translation pipeline."""

    blueprint: Blueprint
    validation_report: DAGValidationReport
    file_targeting: FileTargeting
    change_patterns: ChangePatternReport
    test_estimate_low: int
    test_estimate_high: int


def _build_deferred_items(
    classification: ClassificationResult,
    summary: ComprehensionSummary,
    file_targeting: FileTargeting,
) -> list[DeferredItem]:
    """Build deferred items based on limitations and targeting scope.

    Rules:
    - pipeline_restructuring/architectural_innovation with multi-repo → RE-D{N}
    - Limitations containing "model", "requires", "not currently" → deferred
    """
    items: list[DeferredItem] = []
    counter = 1

    itype = classification.innovation_type
    multi_repo = len(file_targeting.target_repos) > 1

    # Multi-repo deferred item for complex types
    if multi_repo and itype in (
        InnovationType.pipeline_restructuring,
        InnovationType.architectural_innovation,
    ):
        items.append(DeferredItem(
            id=f"RE-D{counter}",
            item="Cross-repo coordination required for multi-repo changes",
            extension_point="blueprint execution",
            trigger="When implementation spans multiple repositories",
        ))
        counter += 1

    # Limitation-derived deferred items
    deferred_keywords = ["model", "requires", "not currently"]
    for limitation in summary.limitations:
        limitation_lower = limitation.lower()
        if any(kw in limitation_lower for kw in deferred_keywords):
            items.append(DeferredItem(
                id=f"RE-D{counter}",
                item=limitation[:100],
                extension_point="infrastructure dependency",
                trigger=f"When: {limitation[:60]}",
            ))
            counter += 1

    return items


def _generate_blueprint_name(
    summary: ComprehensionSummary,
    classification: ClassificationResult,
    custom_name: str | None = None,
) -> str:
    """Generate a blueprint name containing the innovation type."""
    if custom_name:
        return custom_name

    itype_label = classification.innovation_type.value.replace("_", " ").title()
    title_part = summary.title[:50] if summary.title else "Paper Translation"
    return f"{title_part} ({itype_label})"


def translate(input: TranslationInput) -> TranslationResult:
    """Orchestrate the full translation pipeline.

    Steps:
    1. identify_targets() → FileTargeting
    2. mine_ledger() → ChangePatternReport
    3. decompose() → list[WorkingUnit]
    4. Build Phase, BlueprintMetadata, DeferredItems
    5. Assemble Blueprint
    6. validate_dag() → DAGValidationReport
    7. Compute test estimates
    8. Return TranslationResult
    """
    # Step 1: File targeting
    file_targeting = identify_targets(
        input.summary,
        input.classification.innovation_type,
        input.manifests_dir,
    )

    # Step 2: Change patterns
    if input.ledger_path and input.ledger_path.exists():
        change_patterns = mine_ledger(input.ledger_path)
    else:
        change_patterns = ChangePatternReport()

    # Step 3: Decompose into WUs
    wus = decompose(
        input.summary,
        input.classification,
        file_targeting,
        change_patterns,
        phase_id="1",
    )

    # Step 4: Build Phase
    itype = input.classification.innovation_type
    phase_goal = (
        f"Implement {itype.value.replace('_', ' ')}: "
        f"{input.summary.transformation_proposed[:80]}"
    )
    phase = Phase(
        id="1",
        goal=phase_goal,
        working_units=wus,
        output=f"Validated {itype.value.replace('_', ' ')} implementation",
    )

    # Step 5: Build metadata
    bp_date = input.date or date.today().isoformat()
    metadata = BlueprintMetadata(
        date=bp_date,
        status=BlueprintStatus.planned,
        meta_category=input.meta_category,
    )

    # Step 6: Build deferred items
    deferred_items = _build_deferred_items(
        input.classification, input.summary, file_targeting
    )

    # Step 7: Assemble Blueprint
    bp_name = _generate_blueprint_name(
        input.summary, input.classification, input.blueprint_name
    )
    blueprint = Blueprint(
        name=bp_name,
        phases=[phase],
        deferred_items=deferred_items,
        metadata=metadata,
    )

    # Step 8: Validate DAG
    validation_report = validate_dag(blueprint)

    # Step 9: Compute test estimates
    wu_count = len(wus)
    # Use change pattern test ratio if available
    itype_str = itype.value
    if itype_str in change_patterns.by_innovation_type:
        ratio = change_patterns.by_innovation_type[itype_str].avg_test_ratio
        if ratio > 0:
            test_low = max(1, int(wu_count * ratio * 0.8))
            test_high = max(test_low, int(wu_count * ratio * 1.2))
        else:
            test_low = max(1, wu_count * 2)
            test_high = wu_count * 4
    else:
        test_low = max(1, wu_count * 2)
        test_high = wu_count * 4

    return TranslationResult(
        blueprint=blueprint,
        validation_report=validation_report,
        file_targeting=file_targeting,
        change_patterns=change_patterns,
        test_estimate_low=test_low,
        test_estimate_high=test_high,
    )
