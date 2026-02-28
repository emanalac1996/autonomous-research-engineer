"""Tests for video ingestion adapter (WU 7.1)."""

from research_engineer.comprehension.schema import SectionType
from research_engineer.integration.video_adapter import (
    SegmentTranscriptData,
    SlideData,
    VideoAdaptationResult,
    VideoPipelineOutput,
    adapt_video_pipeline_output,
    infer_section_type,
    segment_transcripts_to_sections,
    slide_data_to_section,
)


class TestInferSectionType:
    """Tests for infer_section_type()."""

    def test_method_keyword_maps_to_method(self):
        """Slide description containing 'architecture' maps to method."""
        assert infer_section_type("System Architecture Diagram") == SectionType.method

    def test_results_keyword_maps_to_results(self):
        """Slide description containing 'benchmark' maps to results."""
        assert infer_section_type("Benchmark Results") == SectionType.results

    def test_unknown_description_maps_to_other(self):
        """Slide description with no matching keyword defaults to other."""
        assert infer_section_type("Thank you slide") == SectionType.other


class TestSlideDataToSection:
    """Tests for slide_data_to_section()."""

    def test_slide_with_text_produces_section(self):
        """Slide with method description and text produces a method section."""
        slide = SlideData(
            slide_number=2,
            description="Method: Sparse Term Weight Generation",
            start_s=120.0,
            end_s=300.0,
            text="The technique uses a pre-trained language model.",
            word_count=8,
        )

        section = slide_data_to_section(slide, sequence=0)

        assert section is not None
        assert section.section_type == SectionType.method
        assert section.heading == "Method: Sparse Term Weight Generation"
        assert "pre-trained language model" in section.content

    def test_slide_with_empty_text_returns_none(self):
        """Slide with empty text returns None."""
        slide = SlideData(
            slide_number=1,
            description="Title Slide",
            text="",
        )

        assert slide_data_to_section(slide, sequence=0) is None


class TestSegmentTranscriptsToSections:
    """Tests for segment_transcripts_to_sections()."""

    def test_fallback_produces_other_sections(self):
        """Raw segment transcripts produce sections typed as 'other', ordered by index."""
        transcripts = [
            SegmentTranscriptData(
                text="Second segment text about evaluation.",
                segment_index=1,
            ),
            SegmentTranscriptData(
                text="First segment text about the approach.",
                segment_index=0,
            ),
        ]

        sections = segment_transcripts_to_sections(transcripts)

        assert len(sections) == 2
        assert all(s.section_type == SectionType.other for s in sections)
        # Should be sorted by segment_index
        assert sections[0].heading == "Segment 0"
        assert sections[1].heading == "Segment 1"


class TestAdaptVideoPipelineOutput:
    """Tests for adapt_video_pipeline_output()."""

    def test_full_adaptation_from_slide_transcripts(
        self, sample_video_pipeline_output,
    ):
        """Full video pipeline output produces valid VideoAdaptationResult."""
        result = adapt_video_pipeline_output(sample_video_pipeline_output)

        assert isinstance(result, VideoAdaptationResult)
        assert result.summary.title != ""
        assert result.summary.transformation_proposed != ""
        assert len(result.summary.sections) > 0
        assert result.slide_count == 4
        assert result.total_duration_s > 0
        assert len(result.slide_descriptions) == 4
        # No error-level warnings (fallback/missing warnings)
        assert not any("No slide transcripts" in w for w in result.warnings)
