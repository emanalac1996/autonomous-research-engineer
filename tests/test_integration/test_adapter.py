"""Tests for paper ingestion adapter (WU 6.1)."""

from prior_art.schema.source_document import ContentBlock

from research_engineer.comprehension.schema import SectionType
from research_engineer.integration.adapter import (
    AdaptationResult,
    adapt_source_document,
    content_block_to_section,
    content_blocks_to_sections,
)


class TestContentBlockToSection:
    """Tests for content_block_to_section()."""

    def test_abstract_block_maps_to_abstract_section(self):
        """block_type='abstract' produces SectionType.abstract."""
        block = ContentBlock(
            block_id="test_abs_0",
            block_type="abstract",
            content="We propose a new method for retrieval.",
            section_label="Abstract",
            sequence=0,
        )
        section = content_block_to_section(block)
        assert section is not None
        assert section.section_type == SectionType.abstract
        assert section.content == block.content

    def test_text_block_with_method_label(self):
        """block_type='text' with section_label='Method' produces SectionType.method."""
        block = ContentBlock(
            block_id="test_method_0",
            block_type="text",
            content="The technique uses a pre-trained model.",
            section_label="Method",
            sequence=1,
        )
        section = content_block_to_section(block)
        assert section is not None
        assert section.section_type == SectionType.method

    def test_text_block_without_label_maps_to_other(self):
        """block_type='text' with no section_label produces SectionType.other."""
        block = ContentBlock(
            block_id="test_text_0",
            block_type="text",
            content="Some general text content.",
            sequence=0,
        )
        section = content_block_to_section(block)
        assert section is not None
        assert section.section_type == SectionType.other

    def test_figure_block_returns_none(self):
        """block_type='figure' returns None (skipped)."""
        block = ContentBlock(
            block_id="test_fig_0",
            block_type="figure",
            content="Figure 1 caption",
            section_label="Figures",
            sequence=0,
        )
        section = content_block_to_section(block)
        assert section is None


class TestContentBlocksToSections:
    """Tests for content_blocks_to_sections()."""

    def test_ordered_by_sequence(self):
        """Blocks with out-of-order sequences produce correctly ordered sections."""
        blocks = [
            ContentBlock(
                block_id="b2", block_type="text",
                content="Third block.", sequence=2,
            ),
            ContentBlock(
                block_id="b0", block_type="abstract",
                content="First block.", sequence=0,
            ),
            ContentBlock(
                block_id="b1", block_type="text",
                content="Second block.", section_label="Method", sequence=1,
            ),
        ]
        sections = content_blocks_to_sections(blocks)
        assert len(sections) == 3
        assert sections[0].section_type == SectionType.abstract
        assert sections[1].section_type == SectionType.method
        assert sections[2].section_type == SectionType.other

    def test_empty_blocks_returns_empty(self):
        """Empty block list produces empty section list."""
        sections = content_blocks_to_sections([])
        assert sections == []


class TestAdaptSourceDocument:
    """Tests for adapt_source_document()."""

    def test_full_arxiv_document_produces_valid_summary(
        self, sample_source_document_arxiv,
    ):
        """Full arXiv SourceDocument produces ComprehensionSummary with expected fields."""
        result = adapt_source_document(sample_source_document_arxiv)

        assert isinstance(result, AdaptationResult)
        assert result.source_document_id == "arxiv:2401.12345"
        assert result.corpus == "arxiv"
        assert result.quality_score == 0.72

        summary = result.summary
        assert summary.title == "Learned Sparse Representations for Multi-Hop Retrieval"
        assert summary.transformation_proposed  # non-empty
        assert len(summary.sections) >= 4  # abstract + method + results + limitations
        assert len(summary.claims) > 0  # should extract MRR@10 claim

    def test_empty_content_blocks_produces_minimal_summary(
        self, sample_source_document_minimal,
    ):
        """Empty content_blocks produces summary with title and warning."""
        result = adapt_source_document(sample_source_document_minimal)

        assert result.summary.title == "Minimal Document With No Content Blocks"
        assert any("No content blocks" in w for w in result.warnings)
        # transformation_proposed should fall back to title
        assert result.summary.transformation_proposed

    def test_paper_terms_enriched_from_classifications(
        self, sample_source_document_arxiv,
    ):
        """Classifications keywords/techniques/tasks are merged into paper_terms."""
        result = adapt_source_document(sample_source_document_arxiv)
        terms_lower = [t.lower() for t in result.summary.paper_terms]

        # From classifications.keywords
        assert "splade" in terms_lower
        # From classifications.techniques
        assert "sparse_retrieval" in terms_lower
        # From classifications.tasks
        assert "retrieval" in terms_lower
