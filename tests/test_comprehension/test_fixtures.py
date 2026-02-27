"""Tests for comprehension test fixtures (WU 1.4)."""

from research_engineer.comprehension.schema import ComprehensionSummary


class TestComprehensionFixtures:
    """Validate the three ComprehensionSummary fixtures."""

    def test_parameter_tuning_fixture_loads(self, sample_parameter_tuning_summary):
        """sample_parameter_tuning_summary is a valid ComprehensionSummary."""
        assert isinstance(sample_parameter_tuning_summary, ComprehensionSummary)
        assert "RRF" in sample_parameter_tuning_summary.title or "Weight" in sample_parameter_tuning_summary.title

    def test_modular_swap_fixture_loads(self, sample_modular_swap_summary):
        """sample_modular_swap_summary is a valid ComprehensionSummary."""
        assert isinstance(sample_modular_swap_summary, ComprehensionSummary)
        assert "Sparse" in sample_modular_swap_summary.title or "SPLADE" in sample_modular_swap_summary.title

    def test_architectural_fixture_loads(self, sample_architectural_summary):
        """sample_architectural_summary is a valid ComprehensionSummary."""
        assert isinstance(sample_architectural_summary, ComprehensionSummary)
        assert "Knowledge Graph" in sample_architectural_summary.title

    def test_fixtures_have_distinct_transformations(
        self,
        sample_parameter_tuning_summary,
        sample_modular_swap_summary,
        sample_architectural_summary,
    ):
        """All three fixtures have different transformation_proposed values."""
        transformations = {
            sample_parameter_tuning_summary.transformation_proposed,
            sample_modular_swap_summary.transformation_proposed,
            sample_architectural_summary.transformation_proposed,
        }
        assert len(transformations) == 3

    def test_fixtures_have_claims_with_metrics(
        self,
        sample_parameter_tuning_summary,
        sample_modular_swap_summary,
        sample_architectural_summary,
    ):
        """All three fixtures have at least one claim with metric_name."""
        for summary in [
            sample_parameter_tuning_summary,
            sample_modular_swap_summary,
            sample_architectural_summary,
        ]:
            assert len(summary.claims) >= 1
            assert any(c.metric_name is not None for c in summary.claims)
