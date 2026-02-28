"""Multi-modal comprehension: topology signals from visual slide elements.

Extends the comprehension pipeline to handle video slide+transcript input.
Detects architecture diagrams, pipeline flows, and system design slides as
topology-relevant visual signals, and augments section content accordingly.
"""

from __future__ import annotations

from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    PaperSection,
)
from research_engineer.integration.video_adapter import (
    VideoAdaptationResult,
    VideoPipelineOutput,
    adapt_video_pipeline_output,
)

# ---------------------------------------------------------------------------
# Topology visual keyword detection
# ---------------------------------------------------------------------------

_TOPOLOGY_VISUAL_KEYWORDS: list[str] = [
    "architecture",
    "system design",
    "pipeline",
    "data flow",
    "diagram",
    "flowchart",
    "block diagram",
    "system overview",
    "component diagram",
    "network topology",
    "infrastructure",
    "deployment",
]


def extract_topology_signals(slide_descriptions: list[str]) -> list[str]:
    """Extract topology-relevant signals from slide descriptions.

    Slides depicting architecture diagrams, pipeline flows, or system designs
    are strong indicators of proposed topology changes. Returns the descriptions
    that contain topology-relevant keywords.

    Args:
        slide_descriptions: List of slide description strings from video pipeline.

    Returns:
        List of descriptions that contain topology-relevant visual keywords.
    """
    signals: list[str] = []
    for desc in slide_descriptions:
        desc_lower = desc.lower()
        for keyword in _TOPOLOGY_VISUAL_KEYWORDS:
            if keyword in desc_lower:
                signals.append(desc)
                break  # avoid duplicates for same description
    return signals


# ---------------------------------------------------------------------------
# Visual weight augmentation
# ---------------------------------------------------------------------------


def augment_sections_with_visual_weight(
    sections: list[PaperSection],
    slide_descriptions: list[str],
) -> list[PaperSection]:
    """Augment sections from topology-relevant slides with visual weight.

    When a slide description indicates visual topology content (architecture
    diagram, pipeline flow, etc.), the corresponding section's content is
    prepended with the description, enriching the text that the topology
    analyzer's keyword detection processes.

    Args:
        sections: PaperSections derived from slide_transcripts.
        slide_descriptions: Corresponding slide descriptions (may differ in
            length from sections if some slides produced None sections).

    Returns:
        New list of PaperSections with enriched content where appropriate.
    """
    if not slide_descriptions:
        return sections

    # Build set of topology-relevant descriptions
    topology_descriptions: set[str] = set()
    for desc in slide_descriptions:
        desc_lower = desc.lower()
        for keyword in _TOPOLOGY_VISUAL_KEYWORDS:
            if keyword in desc_lower:
                topology_descriptions.add(desc)
                break

    if not topology_descriptions:
        return sections

    # Augment sections whose heading matches a topology-relevant description
    augmented: list[PaperSection] = []
    for section in sections:
        if section.heading in topology_descriptions:
            augmented.append(
                PaperSection(
                    section_type=section.section_type,
                    heading=section.heading,
                    content=f"{section.heading}. {section.content}",
                )
            )
        else:
            augmented.append(section)

    return augmented


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_video_comprehension_summary(
    output: VideoPipelineOutput,
) -> tuple[ComprehensionSummary, list[str]]:
    """Build a ComprehensionSummary from video pipeline output with visual topology signals.

    Orchestrates:
    1. adapt_video_pipeline_output() for base conversion (WU 7.1)
    2. extract_topology_signals() for visual topology evidence (WU 7.2)
    3. augment_sections_with_visual_weight() for topology enrichment
    4. Rebuild summary with augmented sections if topology signals found

    Args:
        output: Bundled video pipeline output.

    Returns:
        Tuple of (ComprehensionSummary, topology_signals).
        topology_signals is a list of slide descriptions with visual topology content.
    """
    adaptation: VideoAdaptationResult = adapt_video_pipeline_output(output)
    topology_signals = extract_topology_signals(adaptation.slide_descriptions)

    if not topology_signals:
        return adaptation.summary, []

    # Augment sections with visual weight
    augmented_sections = augment_sections_with_visual_weight(
        adaptation.summary.sections,
        adaptation.slide_descriptions,
    )

    # Rebuild summary with augmented sections
    summary = ComprehensionSummary(
        title=adaptation.summary.title,
        transformation_proposed=adaptation.summary.transformation_proposed,
        inputs_required=adaptation.summary.inputs_required,
        outputs_produced=adaptation.summary.outputs_produced,
        claims=adaptation.summary.claims,
        limitations=adaptation.summary.limitations,
        mathematical_core=adaptation.summary.mathematical_core,
        sections=augmented_sections,
        paper_terms=adaptation.summary.paper_terms,
    )

    return summary, topology_signals
