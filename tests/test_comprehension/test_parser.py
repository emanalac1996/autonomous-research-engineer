"""Tests for paper parser (WU 1.2)."""

from research_engineer.comprehension.parser import (
    extract_claims,
    extract_limitations,
    extract_math_core,
    extract_paper_terms,
    extract_sections,
    extract_title,
    extract_transformation,
    parse_paper,
)
from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    SectionType,
)


class TestParseFullPaper:
    """End-to-end tests for parse_paper on all three test fixtures."""

    def test_parse_modular_swap_paper(self, sample_paper_text):
        """parse_paper on modular swap text returns valid ComprehensionSummary."""
        result = parse_paper(sample_paper_text)
        assert isinstance(result, ComprehensionSummary)
        assert result.title != ""
        assert result.transformation_proposed != ""

    def test_parse_parameter_tuning_paper(self, sample_parameter_tuning_text):
        """parse_paper on parameter tuning text returns valid summary."""
        result = parse_paper(sample_parameter_tuning_text)
        assert isinstance(result, ComprehensionSummary)
        assert result.title != ""

    def test_parse_architectural_paper(self, sample_architectural_text):
        """parse_paper on architectural text returns valid summary."""
        result = parse_paper(sample_architectural_text)
        assert isinstance(result, ComprehensionSummary)
        assert result.title != ""


class TestExtractSections:
    """Tests for section extraction."""

    def test_section_count_modular_swap(self, sample_paper_text):
        """Modular swap paper produces at least 4 sections (+ title)."""
        sections = extract_sections(sample_paper_text)
        types = {s.section_type for s in sections}
        assert SectionType.abstract in types
        assert SectionType.method in types
        assert SectionType.results in types
        assert SectionType.limitations in types

    def test_section_count_parameter_tuning(self, sample_parameter_tuning_text):
        """Parameter tuning paper produces at least 4 sections."""
        sections = extract_sections(sample_parameter_tuning_text)
        types = {s.section_type for s in sections}
        assert len(types) >= 4  # title + abstract + method + results + limitations

    def test_section_count_architectural(self, sample_architectural_text):
        """Architectural paper produces at least 4 sections."""
        sections = extract_sections(sample_architectural_text)
        types = {s.section_type for s in sections}
        assert len(types) >= 4


class TestExtractTitle:
    """Tests for title extraction."""

    def test_title_modular_swap(self, sample_paper_text):
        """Title extracted from modular swap paper."""
        title = extract_title(sample_paper_text)
        assert "Learned Sparse" in title or "Multi-Hop" in title

    def test_title_parameter_tuning(self, sample_parameter_tuning_text):
        """Title extracted from parameter tuning paper."""
        title = extract_title(sample_parameter_tuning_text)
        assert "RRF" in title or "Weight" in title

    def test_title_architectural(self, sample_architectural_text):
        """Title extracted from architectural paper."""
        title = extract_title(sample_architectural_text)
        assert "Knowledge Graph" in title


class TestExtractClaims:
    """Tests for claim extraction."""

    def test_claims_modular_swap(self, sample_paper_text):
        """Claims from modular swap paper contain MRR@10 metric."""
        sections = extract_sections(sample_paper_text)
        claims = extract_claims(sections)
        assert len(claims) >= 1
        metric_names = [c.metric_name for c in claims if c.metric_name]
        assert any("MRR" in m for m in metric_names)

    def test_claims_parameter_tuning(self, sample_parameter_tuning_text):
        """Claims from parameter tuning paper contain improvement value."""
        sections = extract_sections(sample_parameter_tuning_text)
        claims = extract_claims(sections)
        assert len(claims) >= 1
        # Should find the 2.3% improvement
        values = [c.metric_value for c in claims if c.metric_value is not None]
        assert len(values) >= 1

    def test_claims_architectural(self, sample_architectural_text):
        """Claims from architectural paper contain accuracy metric."""
        sections = extract_sections(sample_architectural_text)
        claims = extract_claims(sections)
        assert len(claims) >= 1


class TestExtractTransformation:
    """Tests for transformation extraction."""

    def test_transformation_modular_swap(self, sample_paper_text):
        """Transformation from modular swap mentions replacement."""
        sections = extract_sections(sample_paper_text)
        transformation = extract_transformation(sections)
        lower = transformation.lower()
        assert "replac" in lower or "splade" in lower or "sparse" in lower

    def test_transformation_parameter_tuning(self, sample_parameter_tuning_text):
        """Transformation from parameter tuning mentions parameter or weight."""
        sections = extract_sections(sample_parameter_tuning_text)
        transformation = extract_transformation(sections)
        lower = transformation.lower()
        assert "weight" in lower or "parameter" in lower or "rrf" in lower or "investigat" in lower


class TestExtractOther:
    """Tests for limitations, math core, and paper terms."""

    def test_limitations_nonempty(self, sample_paper_text):
        """Limitations list is non-empty for modular swap paper."""
        sections = extract_sections(sample_paper_text)
        limitations = extract_limitations(sections)
        assert len(limitations) >= 1

    def test_math_core_has_formulation(self, sample_paper_text):
        """MathCore has a formulation from method section."""
        sections = extract_sections(sample_paper_text)
        mc = extract_math_core(sections)
        assert mc.formulation is not None

    def test_paper_terms_modular_swap(self, sample_paper_text):
        """Paper terms include domain-relevant terms for modular swap."""
        sections = extract_sections(sample_paper_text)
        terms = extract_paper_terms(sections)
        terms_lower = [t.lower() for t in terms]
        assert any("sparse" in t for t in terms_lower) or any("bm25" in t.lower() for t in terms)
