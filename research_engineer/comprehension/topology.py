"""Topology analyzer: detect pipeline topology changes from comprehension summaries.

Classifies whether a paper proposes changes to pipeline *topology* (adding/removing
stages, changing data flow) vs. changes within existing topology (parameter/component
changes). This is a key input to the innovation-type classifier (Stage 2).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    SectionType,
)


class TopologyChangeType(str, Enum):
    """Types of pipeline topology change."""

    none = "none"
    component_swap = "component_swap"
    stage_addition = "stage_addition"
    stage_removal = "stage_removal"
    flow_restructuring = "flow_restructuring"


class TopologyChange(BaseModel):
    """Result of topology change analysis."""

    model_config = ConfigDict()

    change_type: TopologyChangeType
    affected_stages: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Keyword sets for detection (lowercased)
# ---------------------------------------------------------------------------

_STAGE_ADDITION_KEYWORDS: list[str] = [
    "new stage",
    "new pipeline stage",
    "introduces a new",
    "introduce a new",
    "additional step",
    "intermediate representation",
    "new module",
    "novel pipeline",
    "adds a new",
    "new evaluation methodology",
]

_STAGE_REMOVAL_KEYWORDS: list[str] = [
    "remove stage",
    "remove the stage",
    "remove the",
    "eliminate stage",
    "eliminate the stage",
    "eliminate the",
    "bypass",
    "skip stage",
    "removes the",
    "eliminates the",
    "drop the stage",
]

_COMPONENT_SWAP_KEYWORDS: list[str] = [
    "replace",
    "replacing",
    "swap",
    "swapping",
    "substitute",
    "substituting",
    "instead of",
    "alternative to",
    "drop-in replacement",
]

_FLOW_RESTRUCTURING_KEYWORDS: list[str] = [
    "restructure",
    "reorder",
    "rearrange",
    "change flow",
    "new data flow",
    "different routing",
    "pipeline restructuring",
    "rewrite the pipeline",
    "reorganize",
]

_NO_TOPOLOGY_KEYWORDS: list[str] = [
    "no architectural changes",
    "no structural change",
    "parameter",
    "weight selection",
    "tune",
    "tuning",
    "adjust",
    "optimize parameter",
    "hyperparameter",
    "grid search",
    "varying",
]

# Known pipeline stage names for affected_stages extraction
_KNOWN_STAGES: list[str] = [
    "retrieval",
    "generation",
    "reranking",
    "indexing",
    "embedding",
    "routing",
    "parsing",
    "extraction",
    "graph construction",
    "answer generation",
    "entity linking",
    "relation extraction",
]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _count_keyword_matches(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Count how many keywords appear in text. Return count and matched keywords."""
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return len(matched), matched


def _extract_affected_stages(summary: ComprehensionSummary) -> list[str]:
    """Identify which pipeline stages are affected by the proposed change."""
    # Build analysis text from all available fields
    parts = [summary.transformation_proposed]
    parts.extend(summary.inputs_required)
    parts.extend(summary.outputs_produced)
    for section in summary.sections:
        if section.section_type in {SectionType.abstract, SectionType.method}:
            parts.append(section.content)
    combined = " ".join(parts).lower()

    return [stage for stage in _KNOWN_STAGES if stage in combined]


def analyze_topology(summary: ComprehensionSummary) -> TopologyChange:
    """Analyze a ComprehensionSummary for pipeline topology changes.

    Args:
        summary: The structured comprehension output from paper parsing.

    Returns:
        TopologyChange with detected change type, affected stages,
        confidence, and evidence strings.
    """
    # Build analysis text from transformation + abstract + method
    parts = [summary.transformation_proposed]
    for section in summary.sections:
        if section.section_type in {SectionType.abstract, SectionType.method}:
            parts.append(section.content)
    analysis_text = " ".join(parts)

    # Count matches in each category
    add_count, add_evidence = _count_keyword_matches(analysis_text, _STAGE_ADDITION_KEYWORDS)
    remove_count, remove_evidence = _count_keyword_matches(analysis_text, _STAGE_REMOVAL_KEYWORDS)
    swap_count, swap_evidence = _count_keyword_matches(analysis_text, _COMPONENT_SWAP_KEYWORDS)
    flow_count, flow_evidence = _count_keyword_matches(analysis_text, _FLOW_RESTRUCTURING_KEYWORDS)
    none_count, none_evidence = _count_keyword_matches(analysis_text, _NO_TOPOLOGY_KEYWORDS)

    affected_stages = _extract_affected_stages(summary)

    # Priority-ordered classification
    # stage_addition > flow_restructuring > stage_removal > component_swap > none
    if add_count > 0 and add_count >= swap_count:
        return TopologyChange(
            change_type=TopologyChangeType.stage_addition,
            affected_stages=affected_stages,
            confidence=min(add_count / 3.0, 1.0),
            evidence=[f"stage_addition keyword: '{kw}'" for kw in add_evidence],
        )

    if flow_count > 0:
        return TopologyChange(
            change_type=TopologyChangeType.flow_restructuring,
            affected_stages=affected_stages,
            confidence=min(flow_count / 3.0, 1.0),
            evidence=[f"flow_restructuring keyword: '{kw}'" for kw in flow_evidence],
        )

    if remove_count > 0:
        return TopologyChange(
            change_type=TopologyChangeType.stage_removal,
            affected_stages=affected_stages,
            confidence=min(remove_count / 3.0, 1.0),
            evidence=[f"stage_removal keyword: '{kw}'" for kw in remove_evidence],
        )

    if swap_count > 0 and none_count == 0:
        return TopologyChange(
            change_type=TopologyChangeType.component_swap,
            affected_stages=affected_stages,
            confidence=min(swap_count / 3.0, 1.0),
            evidence=[f"component_swap keyword: '{kw}'" for kw in swap_evidence],
        )

    # Default: no topology change
    evidence = [f"no_topology keyword: '{kw}'" for kw in none_evidence] if none_evidence else ["no topology-change keywords detected"]
    return TopologyChange(
        change_type=TopologyChangeType.none,
        affected_stages=affected_stages,
        confidence=min(max(none_count, 1) / 3.0, 1.0),
        evidence=evidence,
    )
