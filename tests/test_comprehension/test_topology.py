"""Tests for topology analyzer (WU 1.3)."""

import pytest
from pydantic import ValidationError

from research_engineer.comprehension.schema import ComprehensionSummary
from research_engineer.comprehension.topology import (
    TopologyChange,
    TopologyChangeType,
    analyze_topology,
)


class TestTopologyChangeOnFixtures:
    """Test topology detection on the three ComprehensionSummary fixtures."""

    def test_no_topology_change_parameter_tuning(self, sample_parameter_tuning_summary):
        """Parameter tuning summary returns TopologyChangeType.none."""
        result = analyze_topology(sample_parameter_tuning_summary)
        assert result.change_type == TopologyChangeType.none

    def test_component_swap_modular(self, sample_modular_swap_summary):
        """Modular swap summary returns TopologyChangeType.component_swap."""
        result = analyze_topology(sample_modular_swap_summary)
        assert result.change_type == TopologyChangeType.component_swap

    def test_stage_addition_architectural(self, sample_architectural_summary):
        """Architectural summary returns TopologyChangeType.stage_addition."""
        result = analyze_topology(sample_architectural_summary)
        assert result.change_type == TopologyChangeType.stage_addition


class TestTopologyChangeSynthetic:
    """Test topology detection on synthetic summaries."""

    def test_stage_removal(self):
        """Synthetic summary with 'remove the reranking stage' returns stage_removal."""
        summary = ComprehensionSummary(
            transformation_proposed="Remove the reranking stage from the pipeline to reduce latency",
            inputs_required=["retrieval results"],
            outputs_produced=["unranked results"],
        )
        result = analyze_topology(summary)
        assert result.change_type == TopologyChangeType.stage_removal

    def test_flow_restructuring(self):
        """Synthetic summary with 'restructure' returns flow_restructuring."""
        summary = ComprehensionSummary(
            transformation_proposed="Restructure the pipeline to reorder retrieval and generation stages with different routing",
        )
        result = analyze_topology(summary)
        assert result.change_type == TopologyChangeType.flow_restructuring


class TestTopologyChangeProperties:
    """Test structural properties of TopologyChange results."""

    def test_evidence_nonempty(self, sample_modular_swap_summary):
        """All results include at least one evidence string."""
        result = analyze_topology(sample_modular_swap_summary)
        assert len(result.evidence) >= 1

    def test_confidence_range(
        self,
        sample_parameter_tuning_summary,
        sample_modular_swap_summary,
        sample_architectural_summary,
    ):
        """Confidence is in [0.0, 1.0] for all test cases."""
        for summary in [
            sample_parameter_tuning_summary,
            sample_modular_swap_summary,
            sample_architectural_summary,
        ]:
            result = analyze_topology(summary)
            assert 0.0 <= result.confidence <= 1.0

    def test_affected_stages_populated_for_architectural(self, sample_architectural_summary):
        """Stage addition result has at least one affected stage."""
        result = analyze_topology(sample_architectural_summary)
        assert len(result.affected_stages) >= 1


class TestTopologyChangeModel:
    """Test TopologyChange model validation."""

    def test_json_roundtrip(self):
        """TopologyChange round-trips through JSON."""
        original = TopologyChange(
            change_type=TopologyChangeType.component_swap,
            affected_stages=["retrieval"],
            confidence=0.8,
            evidence=["swap keyword: 'replace'"],
        )
        json_str = original.model_dump_json()
        restored = TopologyChange.model_validate_json(json_str)
        assert restored == original

    def test_rejects_confidence_out_of_range(self):
        """TopologyChange rejects confidence outside [0, 1]."""
        with pytest.raises(ValidationError):
            TopologyChange(
                change_type=TopologyChangeType.none,
                confidence=1.5,
            )
