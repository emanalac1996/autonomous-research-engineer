"""Tests for heuristic engine (WU 2.2)."""

import pytest

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.heuristics import classify, load_heuristic_rules
from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary, MathCore
from research_engineer.comprehension.topology import TopologyChange, TopologyChangeType


class TestLoadHeuristicRules:
    """Tests for loading rules from the artifact registry."""

    def test_returns_non_empty(self, seeded_artifact_registry):
        """load_heuristic_rules returns a non-empty list."""
        rules = load_heuristic_rules(seeded_artifact_registry)
        assert len(rules) > 0

    def test_sorted_by_priority(self, seeded_artifact_registry):
        """Rules are sorted by priority (ascending)."""
        rules = load_heuristic_rules(seeded_artifact_registry)
        priorities = [r["priority"] for r in rules]
        assert priorities == sorted(priorities)

    def test_auto_registers_seed(self, tmp_artifact_registry):
        """load_heuristic_rules auto-registers seed if registry is empty."""
        rules = load_heuristic_rules(tmp_artifact_registry)
        assert len(rules) == 5


class TestClassifyParameterTuning:
    """Tests for parameter tuning classification."""

    def test_parameter_tuning_fixture(
        self,
        sample_parameter_tuning_summary,
        sample_topology_none,
        seeded_artifact_registry,
    ):
        """Parameter tuning summary classified as parameter_tuning."""
        result = classify(
            sample_parameter_tuning_summary,
            sample_topology_none,
            [],
            seeded_artifact_registry,
        )
        assert result.innovation_type == InnovationType.parameter_tuning

    def test_parameter_tuning_confidence(
        self,
        sample_parameter_tuning_summary,
        sample_topology_none,
        seeded_artifact_registry,
    ):
        """Parameter tuning has reasonable confidence."""
        result = classify(
            sample_parameter_tuning_summary,
            sample_topology_none,
            [],
            seeded_artifact_registry,
        )
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence > 0.5


class TestClassifyModularSwap:
    """Tests for modular swap classification."""

    def test_modular_swap_fixture(
        self,
        sample_modular_swap_summary,
        sample_topology_component_swap,
        seeded_artifact_registry,
    ):
        """Modular swap summary classified as modular_swap."""
        result = classify(
            sample_modular_swap_summary,
            sample_topology_component_swap,
            [],
            seeded_artifact_registry,
        )
        assert result.innovation_type == InnovationType.modular_swap


class TestClassifyArchitecturalInnovation:
    """Tests for architectural innovation classification."""

    def test_architectural_fixture(
        self,
        sample_architectural_summary,
        sample_topology_stage_addition,
        seeded_artifact_registry,
    ):
        """Architectural summary classified as architectural_innovation."""
        result = classify(
            sample_architectural_summary,
            sample_topology_stage_addition,
            [],
            seeded_artifact_registry,
        )
        assert result.innovation_type == InnovationType.architectural_innovation


class TestClassifyPipelineRestructuring:
    """Tests for pipeline restructuring classification."""

    def test_pipeline_restructuring_fixture(
        self,
        sample_pipeline_restructuring_summary,
        seeded_artifact_registry,
    ):
        """Pipeline restructuring summary classified as pipeline_restructuring."""
        topology = TopologyChange(
            change_type=TopologyChangeType.flow_restructuring,
            affected_stages=["retrieval", "reranking", "generation"],
            confidence=0.67,
            evidence=["flow_restructuring keyword: 'restructure'"],
        )
        result = classify(
            sample_pipeline_restructuring_summary,
            topology,
            [],
            seeded_artifact_registry,
        )
        assert result.innovation_type == InnovationType.pipeline_restructuring


class TestClassifyOutputFields:
    """Tests for classification result fields."""

    def test_rationale_non_empty(
        self,
        sample_parameter_tuning_summary,
        sample_topology_none,
        seeded_artifact_registry,
    ):
        """Classification rationale is non-empty."""
        result = classify(
            sample_parameter_tuning_summary,
            sample_topology_none,
            [],
            seeded_artifact_registry,
        )
        assert len(result.rationale) > 0

    def test_topology_signal_populated(
        self,
        sample_parameter_tuning_summary,
        sample_topology_none,
        seeded_artifact_registry,
    ):
        """Classification topology_signal is populated."""
        result = classify(
            sample_parameter_tuning_summary,
            sample_topology_none,
            [],
            seeded_artifact_registry,
        )
        assert "none" in result.topology_signal

    def test_manifest_evidence_passed_through(
        self,
        sample_modular_swap_summary,
        sample_topology_component_swap,
        seeded_artifact_registry,
    ):
        """Manifest evidence is passed through to result."""
        evidence = ["BM25 found in multimodal-rag-core"]
        result = classify(
            sample_modular_swap_summary,
            sample_topology_component_swap,
            evidence,
            seeded_artifact_registry,
        )
        assert result.manifest_evidence == evidence


class TestClassifyEscalation:
    """Tests for escalation on low-confidence inputs."""

    def test_ambiguous_input_triggers_escalation(self, seeded_artifact_registry):
        """An ambiguous input with no clear signals triggers escalation."""
        ambiguous_summary = ComprehensionSummary(
            title="Ambiguous Paper",
            transformation_proposed="Some vague modification to the system",
            inputs_required=[],
            outputs_produced=[],
            mathematical_core=MathCore(),
            paper_terms=[],
        )
        topology = TopologyChange(
            change_type=TopologyChangeType.none,
            affected_stages=[],
            confidence=0.1,
            evidence=["no topology-change keywords detected"],
        )
        result = classify(
            ambiguous_summary,
            topology,
            [],
            seeded_artifact_registry,
        )
        assert result.escalation_trigger == EscalationTrigger.confidence_below_threshold

    def test_clear_input_no_escalation(
        self,
        sample_parameter_tuning_summary,
        sample_topology_none,
        seeded_artifact_registry,
    ):
        """A clear input does not trigger escalation."""
        result = classify(
            sample_parameter_tuning_summary,
            sample_topology_none,
            [],
            seeded_artifact_registry,
        )
        assert result.escalation_trigger is None
