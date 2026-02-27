"""Calibration report generator: orchestrate accuracy, maturity, and evolution.

Composes tracker, maturity assessor, and heuristic evolver into a single
structured report with optional markdown rendering.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict

from agent_factors.artifacts import ArtifactRegistry

from research_engineer.calibration.heuristic_evolver import (
    EvolutionProposal,
    analyze_misclassifications,
    propose_mutations,
)
from research_engineer.calibration.maturity_assessor import (
    MaturityAssessment,
    assess_maturity,
)
from research_engineer.calibration.tracker import AccuracyReport, AccuracyTracker


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CalibrationInput(BaseModel):
    """Bundled input for calibration report generation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tracker: AccuracyTracker
    registry: ArtifactRegistry
    repo_name: str = "autonomous-research-engineer"
    current_maturity_level: str = "foundational"


class CalibrationReport(BaseModel):
    """Complete calibration report."""

    model_config = ConfigDict()

    repo_name: str
    timestamp: datetime
    accuracy_report: AccuracyReport
    maturity_assessment: MaturityAssessment
    evolution_proposal: EvolutionProposal | None = None
    total_papers: int
    overall_accuracy: float
    recommendation_summary: str


class CalibrationReportMarkdown(BaseModel):
    """Markdown-rendered calibration report."""

    model_config = ConfigDict()

    content: str
    report: CalibrationReport


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(input: CalibrationInput) -> CalibrationReport:
    """Generate a complete calibration report.

    Orchestrates:
    1. Accuracy report from tracker
    2. Maturity assessment from assessor
    3. Misclassification analysis and mutation proposal (if errors exist)

    Args:
        input: Bundled calibration input with tracker, registry, and config.

    Returns:
        CalibrationReport with all metrics and recommendations.
    """
    accuracy = input.tracker.report()

    maturity = assess_maturity(
        tracker=input.tracker,
        registry=input.registry,
        repo_name=input.repo_name,
        current_level=input.current_maturity_level,
    )

    # Analyze misclassifications and propose mutations
    evolution: EvolutionProposal | None = None
    misses = input.tracker.misclassifications()
    if misses:
        patterns = analyze_misclassifications(input.tracker)
        if patterns:
            evolution = propose_mutations(patterns, input.registry)

    # Build recommendation summary
    parts = [f"Accuracy: {accuracy.overall_accuracy:.1%}"]
    parts.append(f"Maturity: {maturity.recommendation}")
    if evolution and evolution.mutations:
        parts.append(f"{len(evolution.mutations)} heuristic mutation(s) proposed")
    recommendation = " | ".join(parts)

    return CalibrationReport(
        repo_name=input.repo_name,
        timestamp=datetime.now(timezone.utc),
        accuracy_report=accuracy,
        maturity_assessment=maturity,
        evolution_proposal=evolution,
        total_papers=accuracy.total_records,
        overall_accuracy=accuracy.overall_accuracy,
        recommendation_summary=recommendation,
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(report: CalibrationReport) -> CalibrationReportMarkdown:
    """Render a CalibrationReport as human-readable markdown.

    Args:
        report: The calibration report to render.

    Returns:
        CalibrationReportMarkdown with full markdown content.
    """
    lines: list[str] = []

    lines.append(f"# Calibration Report: {report.repo_name}")
    lines.append("")

    # Accuracy Summary
    lines.append("## Accuracy Summary")
    lines.append("")
    lines.append(f"- **Overall Accuracy:** {report.overall_accuracy:.1%}")
    lines.append(f"- **Total Papers Evaluated:** {report.total_papers}")
    lines.append(
        f"- **Confidence-Accuracy Correlation:** "
        f"{report.accuracy_report.confidence_accuracy_correlation:.3f}"
    )
    lines.append("")

    # Per-type accuracy table
    lines.append("### Per-Type Accuracy")
    lines.append("")
    lines.append("| Innovation Type | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|")
    for pta in report.accuracy_report.per_type:
        lines.append(
            f"| {pta.innovation_type.value} | "
            f"{pta.precision:.2f} | "
            f"{pta.recall:.2f} | "
            f"{pta.f1_score:.2f} |"
        )
    lines.append("")

    # Confusion Matrix
    cm = report.accuracy_report.confusion_matrix
    lines.append("## Confusion Matrix")
    lines.append("")
    header = "| Predicted \\ Actual | " + " | ".join(cm.labels) + " |"
    lines.append(header)
    lines.append("|---|" + "|".join(["---"] * len(cm.labels)) + "|")
    for pred in cm.labels:
        row_vals = [str(cm.matrix[pred][actual]) for actual in cm.labels]
        lines.append(f"| {pred} | " + " | ".join(row_vals) + " |")
    lines.append("")

    # Maturity Assessment
    ma = report.maturity_assessment
    lines.append("## Maturity Assessment")
    lines.append("")
    lines.append(f"- **Current Level:** {ma.current_level}")
    lines.append(f"- **Target Level:** {ma.target_level}")
    lines.append(f"- **Recommendation:** {ma.recommendation}")
    if ma.unmet_requirements:
        lines.append("- **Unmet Requirements:**")
        for req in ma.unmet_requirements:
            lines.append(f"  - {req}")
    lines.append("")

    # Misclassification Patterns
    if report.evolution_proposal and report.evolution_proposal.patterns:
        lines.append("## Misclassification Patterns")
        lines.append("")
        for p in report.evolution_proposal.patterns:
            lines.append(
                f"- **{p.predicted_type.value} → {p.actual_type.value}**: "
                f"{p.count} occurrence(s), avg confidence {p.avg_confidence:.2f}"
            )
        lines.append("")

    # Proposed Mutations
    if report.evolution_proposal and report.evolution_proposal.mutations:
        lines.append("## Proposed Heuristic Mutations")
        lines.append("")
        for m in report.evolution_proposal.mutations:
            lines.append(f"- **{m.mutation_type}** on `{m.target_rule_id}`: {m.description}")
        lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    lines.append("")
    lines.append(report.recommendation_summary)
    lines.append("")

    content = "\n".join(lines)

    return CalibrationReportMarkdown(
        content=content,
        report=report,
    )
