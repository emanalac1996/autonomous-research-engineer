"""Tests for heuristic evolver (WU 5.3)."""

import pytest
import yaml

from research_engineer.calibration.heuristic_evolver import (
    EvolutionProposal,
    EvolutionResult,
    MisclassificationPattern,
    RuleMutation,
    analyze_misclassifications,
    apply_evolution,
    propose_mutations,
)
from research_engineer.calibration.tracker import AccuracyRecord, AccuracyTracker
from research_engineer.classifier.seed_artifact import validate_heuristic_yaml
from research_engineer.classifier.types import InnovationType


def _make_tracker_with_misclassifications() -> AccuracyTracker:
    """Build tracker with 4 correct + 2 misclassifications."""
    tracker = AccuracyTracker()
    # 4 correct
    for i, itype in enumerate(InnovationType):
        tracker.add_record(AccuracyRecord(
            paper_id=f"correct-{i}",
            predicted_type=itype,
            ground_truth_type=itype,
            confidence=0.85,
        ))
    # 2 misclassifications
    tracker.add_record(AccuracyRecord(
        paper_id="miss-1",
        predicted_type=InnovationType.parameter_tuning,
        ground_truth_type=InnovationType.modular_swap,
        confidence=0.55,
    ))
    tracker.add_record(AccuracyRecord(
        paper_id="miss-2",
        predicted_type=InnovationType.pipeline_restructuring,
        ground_truth_type=InnovationType.architectural_innovation,
        confidence=0.50,
    ))
    return tracker


def _make_all_correct_tracker() -> AccuracyTracker:
    """Build tracker where all records are correct."""
    tracker = AccuracyTracker()
    for i, itype in enumerate(InnovationType):
        tracker.add_record(AccuracyRecord(
            paper_id=f"perfect-{i}",
            predicted_type=itype,
            ground_truth_type=itype,
            confidence=0.90,
        ))
    return tracker


class TestMisclassificationPattern:
    """Tests for MisclassificationPattern model."""

    def test_creation(self):
        """MisclassificationPattern constructs with all fields."""
        p = MisclassificationPattern(
            predicted_type=InnovationType.parameter_tuning,
            actual_type=InnovationType.modular_swap,
            count=3,
            fraction_of_total_errors=0.5,
            example_paper_ids=["p1", "p2"],
            avg_confidence=0.45,
        )
        assert p.count == 3
        assert p.predicted_type == InnovationType.parameter_tuning


class TestRuleMutation:
    """Tests for RuleMutation model."""

    def test_rejects_invalid_mutation_type(self):
        """RuleMutation rejects invalid mutation_type."""
        with pytest.raises(Exception):
            RuleMutation(
                mutation_type="delete_rule",
                description="bad mutation",
                parameter="weight",
                new_value="0.5",
            )


class TestEvolutionProposal:
    """Tests for EvolutionProposal model."""

    def test_json_roundtrip(self):
        """EvolutionProposal round-trips through JSON."""
        original = EvolutionProposal(
            patterns=[
                MisclassificationPattern(
                    predicted_type=InnovationType.parameter_tuning,
                    actual_type=InnovationType.modular_swap,
                    count=1,
                    fraction_of_total_errors=1.0,
                    avg_confidence=0.5,
                ),
            ],
            mutations=[
                RuleMutation(
                    mutation_type="add_keyword",
                    target_rule_id="rule_modular_swap",
                    description="Add keyword",
                    parameter="signals.transformation_keywords",
                    new_value="test_keyword",
                ),
            ],
            expected_accuracy_improvement=0.05,
            rationale="Test proposal",
        )
        json_str = original.model_dump_json()
        restored = EvolutionProposal.model_validate_json(json_str)
        assert len(restored.patterns) == 1
        assert len(restored.mutations) == 1


class TestAnalyzeMisclassifications:
    """Tests for analyze_misclassifications function."""

    def test_groups_correctly(self):
        """Groups misclassifications by (predicted, actual) correctly."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        assert len(patterns) == 2

        # Check both patterns exist
        pattern_keys = {(p.predicted_type.value, p.actual_type.value) for p in patterns}
        assert ("parameter_tuning", "modular_swap") in pattern_keys
        assert ("pipeline_restructuring", "architectural_innovation") in pattern_keys

    def test_no_misclassifications_returns_empty(self):
        """Returns empty list when all records correct."""
        tracker = _make_all_correct_tracker()
        patterns = analyze_misclassifications(tracker)
        assert patterns == []


class TestProposeMutations:
    """Tests for propose_mutations function."""

    def test_proposes_keyword_addition(self, seeded_artifact_registry):
        """Proposes add_keyword for param→swap pattern."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        proposal = propose_mutations(patterns, seeded_artifact_registry)

        keyword_mutations = [m for m in proposal.mutations if m.mutation_type == "add_keyword"]
        assert len(keyword_mutations) > 0
        # Should include mutation targeting modular_swap rule
        target_rules = {m.target_rule_id for m in keyword_mutations}
        assert "rule_modular_swap" in target_rules

    def test_proposes_weight_adjustment(self, seeded_artifact_registry):
        """Proposes weight adjustment for low-confidence misclassification."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        proposal = propose_mutations(patterns, seeded_artifact_registry)

        weight_mutations = [m for m in proposal.mutations if m.mutation_type == "adjust_weight"]
        assert len(weight_mutations) > 0


class TestApplyEvolution:
    """Tests for apply_evolution function."""

    def test_default_not_applied(self, seeded_artifact_registry):
        """auto_apply=False returns applied=False."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        proposal = propose_mutations(patterns, seeded_artifact_registry)

        result = apply_evolution(proposal, seeded_artifact_registry, auto_apply=False)
        assert result.applied is False
        assert result.artifact_id is None

    def test_auto_apply_updates_registry(self, seeded_artifact_registry):
        """auto_apply=True creates new artifact version in registry."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        proposal = propose_mutations(patterns, seeded_artifact_registry)

        result = apply_evolution(proposal, seeded_artifact_registry, auto_apply=True)
        assert result.applied is True
        assert result.artifact_id is not None

    def test_applied_yaml_validates(self, seeded_artifact_registry):
        """Applied YAML passes validate_heuristic_yaml."""
        tracker = _make_tracker_with_misclassifications()
        patterns = analyze_misclassifications(tracker)
        proposal = propose_mutations(patterns, seeded_artifact_registry)

        result = apply_evolution(proposal, seeded_artifact_registry, auto_apply=True)
        assert result.applied is True

        # Read back and validate
        from agent_factors.artifacts import ArtifactType
        from research_engineer.classifier.seed_artifact import CLASSIFIER_DOMAIN

        entries = seeded_artifact_registry.query(
            artifact_type=ArtifactType.evaluation_rubric,
            domain=CLASSIFIER_DOMAIN,
        )
        content = seeded_artifact_registry.get_content(entries[0].artifact_id)
        data = validate_heuristic_yaml(content)
        assert "rules" in data
