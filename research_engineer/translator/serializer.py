"""Blueprint serializer: render TranslationResult as ADR-005 Tier 1 markdown.

Produces markdown that round-trips through agent_factors.dag.parser.parse_blueprint()
and passes validate_dag().
"""

from __future__ import annotations

from pathlib import Path

from research_engineer.translator.translator import TranslationResult


def _format_depends_on(depends_on: list[str]) -> str:
    """Format depends_on list for table cell."""
    if not depends_on:
        return "---"
    return ", ".join(f"Working Unit {dep}" for dep in depends_on)


def serialize_blueprint(result: TranslationResult) -> str:
    """Render a TranslationResult as ADR-005 Tier 1 markdown.

    The output is designed to be parseable by parse_blueprint() and
    pass validate_dag().
    """
    bp = result.blueprint
    meta = bp.metadata
    lines: list[str] = []

    # Title
    lines.append(f"# {bp.name}")
    lines.append("")

    # Header metadata
    if meta.date:
        lines.append(f"**Date:** {meta.date}")
    lines.append(f"**Status:** {meta.status.value}")
    if meta.meta_category:
        lines.append(f"**Meta-category:** {meta.meta_category}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Phases
    for i, phase in enumerate(bp.phases, start=1):
        lines.append(f"## {i}. Phase {phase.id}: {phase.goal}")
        lines.append("")
        lines.append(f"**Goal:** {phase.goal}")
        lines.append("")

        # WU table
        lines.append(
            "| Working Unit | Description | Depends On | Acceptance Criteria |"
        )
        lines.append("|---|---|---|---|")

        for wu in phase.working_units:
            depends = _format_depends_on(wu.depends_on)
            desc = wu.description.replace("|", "/")
            ac = wu.acceptance_criteria.replace("|", "/") if wu.acceptance_criteria else ""
            lines.append(
                f"| Working Unit {wu.id} | {desc} | {depends} | {ac} |"
            )

        lines.append("")

        # Phase output
        if phase.output:
            lines.append(f"**Output:** {phase.output}")
        lines.append(
            f"**Test estimate:** {result.test_estimate_low}-{result.test_estimate_high} tests"
        )
        lines.append("")

    # Deferred items
    if bp.deferred_items:
        lines.append("## Deferred Items")
        lines.append("")
        lines.append("| ID | Item | Extension point | Trigger |")
        lines.append("|---|---|---|---|")
        for item in bp.deferred_items:
            item_text = item.item.replace("|", "/")
            ext = item.extension_point.replace("|", "/")
            trigger = item.trigger.replace("|", "/")
            lines.append(f"| {item.id} | {item_text} | {ext} | {trigger} |")
        lines.append("")

    return "\n".join(lines)


def write_blueprint(result: TranslationResult, output_dir: Path) -> Path:
    """Write a serialized blueprint to a file.

    Args:
        result: Translation result to serialize.
        output_dir: Directory to write the blueprint file into.

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build filename
    date_part = result.blueprint.metadata.date or "undated"
    name_part = result.blueprint.name.lower()
    # Sanitize for filename
    name_part = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in name_part
    )[:60]
    filename = f"{date_part}_{name_part}_blueprint.md"

    output_path = output_dir / filename
    content = serialize_blueprint(result)
    output_path.write_text(content, encoding="utf-8")

    return output_path
