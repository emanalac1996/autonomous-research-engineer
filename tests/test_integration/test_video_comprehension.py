"""Tests for multi-modal comprehension extension (WU 7.2)."""

from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    PaperSection,
    SectionType,
)
from research_engineer.integration.video_comprehension import (
    augment_sections_with_visual_weight,
    build_video_comprehension_summary,
    extract_topology_signals,
)


class TestExtractTopologySignals:
    """Tests for extract_topology_signals()."""

    def test_architecture_slide_detected(self):
        """Description containing 'architecture' is detected as topology signal."""
        descriptions = ["System Architecture Overview", "Introduction", "Results Table"]

        signals = extract_topology_signals(descriptions)

        assert signals == ["System Architecture Overview"]

    def test_pipeline_diagram_detected(self):
        """Description containing 'pipeline' is detected as topology signal."""
        descriptions = ["Data Pipeline Flow", "Method Details"]

        signals = extract_topology_signals(descriptions)

        assert signals == ["Data Pipeline Flow"]

    def test_no_topology_signals_from_text_slides(self):
        """Descriptions with no topology keywords return empty list."""
        descriptions = ["Introduction", "Conclusion", "Thank You"]

        signals = extract_topology_signals(descriptions)

        assert signals == []


class TestAugmentSectionsWithVisualWeight:
    """Tests for augment_sections_with_visual_weight()."""

    def test_architecture_section_gets_enrichment(self):
        """Section from architecture slide has description prepended to content."""
        sections = [
            PaperSection(
                section_type=SectionType.method,
                heading="System Architecture Diagram",
                content="A graph module extracts entities.",
            ),
        ]
        descriptions = ["System Architecture Diagram"]

        augmented = augment_sections_with_visual_weight(sections, descriptions)

        assert len(augmented) == 1
        assert augmented[0].content.startswith("System Architecture Diagram.")
        assert "A graph module extracts entities." in augmented[0].content

    def test_non_topology_section_unchanged(self):
        """Section from non-topology slide retains original content."""
        sections = [
            PaperSection(
                section_type=SectionType.results,
                heading="Evaluation Results",
                content="MRR@10 improved by 18.4%.",
            ),
        ]
        descriptions = ["Evaluation Results"]

        augmented = augment_sections_with_visual_weight(sections, descriptions)

        assert len(augmented) == 1
        assert augmented[0].content == "MRR@10 improved by 18.4%."


class TestBuildVideoComprehensionSummary:
    """Tests for build_video_comprehension_summary()."""

    def test_full_video_comprehension_with_topology(
        self, sample_video_pipeline_output_with_architecture,
    ):
        """Video with architecture slide produces summary with topology signals."""
        summary, topology_signals = build_video_comprehension_summary(
            sample_video_pipeline_output_with_architecture,
        )

        assert isinstance(summary, ComprehensionSummary)
        assert len(topology_signals) >= 1
        assert any("Architecture" in s for s in topology_signals)
        # At least one section should have enriched content
        arch_sections = [
            s for s in summary.sections if "System Architecture Diagram" in s.content
        ]
        assert len(arch_sections) >= 1
