"""Tests for comprehension schema models (WU 1.1)."""

import pytest
from pydantic import ValidationError

from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    MathCore,
    PaperClaim,
    PaperSection,
    SectionType,
)


class TestComprehensionSummary:
    """Tests for the ComprehensionSummary model."""

    def test_minimal_construction(self):
        """Construct with only transformation_proposed; defaults work."""
        summary = ComprehensionSummary(
            transformation_proposed="Replace BM25 with learned sparse retrieval",
        )
        assert summary.transformation_proposed == "Replace BM25 with learned sparse retrieval"
        assert summary.title == ""
        assert summary.inputs_required == []
        assert summary.outputs_produced == []
        assert summary.claims == []
        assert summary.limitations == []
        assert summary.mathematical_core.formulation is None
        assert summary.sections == []
        assert summary.paper_terms == []

    def test_full_construction(self):
        """Construct with all fields populated."""
        summary = ComprehensionSummary(
            title="Test Paper",
            transformation_proposed="Swap retriever component",
            inputs_required=["query text", "index"],
            outputs_produced=["ranked results"],
            claims=[
                PaperClaim(claim_text="Improves MRR by 10%", metric_name="MRR", metric_value=10.0),
            ],
            limitations=["Only tested on English"],
            mathematical_core=MathCore(
                formulation="score = f(q, d)",
                complexity="O(n log n)",
                assumptions=["Documents are pre-indexed"],
            ),
            sections=[
                PaperSection(section_type=SectionType.abstract, content="We propose..."),
            ],
            paper_terms=["BM25", "sparse retrieval"],
        )
        assert summary.title == "Test Paper"
        assert len(summary.claims) == 1
        assert len(summary.sections) == 1
        assert summary.mathematical_core.complexity == "O(n log n)"
        assert "BM25" in summary.paper_terms

    def test_json_roundtrip(self):
        """model_dump_json then model_validate_json is identity."""
        original = ComprehensionSummary(
            title="Roundtrip Test",
            transformation_proposed="Test transformation",
            inputs_required=["input_a"],
            outputs_produced=["output_b"],
            claims=[PaperClaim(claim_text="Claim A", metric_name="F1", metric_value=0.95)],
            limitations=["Limitation 1"],
            mathematical_core=MathCore(formulation="x = y + z", assumptions=["a > 0"]),
            sections=[PaperSection(section_type=SectionType.method, content="Method content")],
            paper_terms=["term1", "term2"],
        )
        json_str = original.model_dump_json()
        restored = ComprehensionSummary.model_validate_json(json_str)
        assert restored == original

    def test_rejects_empty_transformation(self):
        """Empty transformation_proposed raises ValidationError."""
        with pytest.raises(ValidationError, match="transformation_proposed"):
            ComprehensionSummary(transformation_proposed="")

    def test_rejects_whitespace_transformation(self):
        """Whitespace-only transformation_proposed raises ValidationError."""
        with pytest.raises(ValidationError, match="transformation_proposed"):
            ComprehensionSummary(transformation_proposed="   ")


class TestPaperClaim:
    """Tests for the PaperClaim model."""

    def test_valid_claim(self):
        """Construct valid PaperClaim with all fields."""
        claim = PaperClaim(
            claim_text="Achieves 0.847 MRR@10",
            metric_name="MRR@10",
            metric_value=0.847,
            baseline_comparison=0.620,
            dataset="Natural Questions",
        )
        assert claim.metric_value == 0.847
        assert claim.baseline_comparison == 0.620

    def test_rejects_empty_claim_text(self):
        """Empty claim_text raises ValidationError."""
        with pytest.raises(ValidationError, match="claim_text"):
            PaperClaim(claim_text="")

    def test_optional_metrics(self):
        """PaperClaim with only claim_text is valid."""
        claim = PaperClaim(claim_text="Qualitative improvement observed")
        assert claim.metric_name is None
        assert claim.metric_value is None
        assert claim.baseline_comparison is None
        assert claim.dataset is None


class TestMathCore:
    """Tests for the MathCore model."""

    def test_defaults(self):
        """MathCore() has None formulation, None complexity, empty assumptions."""
        mc = MathCore()
        assert mc.formulation is None
        assert mc.complexity is None
        assert mc.assumptions == []


class TestPaperSection:
    """Tests for the PaperSection model."""

    def test_valid_section(self):
        """Construct valid PaperSection."""
        section = PaperSection(
            section_type=SectionType.abstract,
            heading="Abstract",
            content="We propose a new method...",
        )
        assert section.section_type == SectionType.abstract
        assert section.heading == "Abstract"

    def test_rejects_empty_content(self):
        """Empty content raises ValidationError."""
        with pytest.raises(ValidationError, match="content"):
            PaperSection(section_type=SectionType.method, content="  ")
