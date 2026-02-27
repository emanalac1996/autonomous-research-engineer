"""Tests for classification types (WU 2.1)."""

import pytest
from pydantic import ValidationError

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.types import ClassificationResult, InnovationType


class TestInnovationType:
    """Tests for the InnovationType enum."""

    def test_has_four_values(self):
        """InnovationType has exactly 4 members."""
        assert len(InnovationType) == 4

    def test_values_are_strings(self):
        """All InnovationType values are strings."""
        for member in InnovationType:
            assert isinstance(member.value, str)

    def test_expected_members(self):
        """All expected innovation types are present."""
        expected = {
            "parameter_tuning",
            "modular_swap",
            "pipeline_restructuring",
            "architectural_innovation",
        }
        assert {m.value for m in InnovationType} == expected


class TestClassificationResult:
    """Tests for the ClassificationResult model."""

    def test_minimal_construction(self):
        """ClassificationResult constructs with required fields only."""
        result = ClassificationResult(
            innovation_type=InnovationType.parameter_tuning,
            confidence=0.8,
            rationale="Parameter tuning detected via keyword match",
        )
        assert result.innovation_type == InnovationType.parameter_tuning
        assert result.confidence == 0.8
        assert result.escalation_trigger is None

    def test_full_construction(self):
        """ClassificationResult constructs with all fields populated."""
        result = ClassificationResult(
            innovation_type=InnovationType.modular_swap,
            confidence=0.92,
            rationale="Modular swap: BM25 -> SPLADE",
            topology_signal="component_swap with confidence 0.67",
            manifest_evidence=["BM25 found in multimodal-rag-core"],
            escalation_trigger=EscalationTrigger.confidence_below_threshold,
        )
        assert result.topology_signal == "component_swap with confidence 0.67"
        assert len(result.manifest_evidence) == 1
        assert result.escalation_trigger == EscalationTrigger.confidence_below_threshold

    def test_json_roundtrip(self):
        """ClassificationResult round-trips through JSON."""
        original = ClassificationResult(
            innovation_type=InnovationType.pipeline_restructuring,
            confidence=0.75,
            rationale="Pipeline restructuring detected",
            topology_signal="stage_addition with confidence 0.5",
            manifest_evidence=["retrieval module found"],
        )
        json_str = original.model_dump_json()
        restored = ClassificationResult.model_validate_json(json_str)
        assert restored == original

    def test_rejects_empty_rationale(self):
        """ClassificationResult rejects empty rationale."""
        with pytest.raises(ValidationError, match="rationale"):
            ClassificationResult(
                innovation_type=InnovationType.parameter_tuning,
                confidence=0.5,
                rationale="",
            )

    def test_rejects_whitespace_rationale(self):
        """ClassificationResult rejects whitespace-only rationale."""
        with pytest.raises(ValidationError, match="rationale"):
            ClassificationResult(
                innovation_type=InnovationType.parameter_tuning,
                confidence=0.5,
                rationale="   ",
            )

    def test_rejects_confidence_above_one(self):
        """ClassificationResult rejects confidence > 1.0."""
        with pytest.raises(ValidationError):
            ClassificationResult(
                innovation_type=InnovationType.parameter_tuning,
                confidence=1.5,
                rationale="Should fail",
            )

    def test_rejects_confidence_below_zero(self):
        """ClassificationResult rejects confidence < 0.0."""
        with pytest.raises(ValidationError):
            ClassificationResult(
                innovation_type=InnovationType.parameter_tuning,
                confidence=-0.1,
                rationale="Should fail",
            )

    def test_escalation_trigger_defaults_none(self):
        """escalation_trigger defaults to None."""
        result = ClassificationResult(
            innovation_type=InnovationType.architectural_innovation,
            confidence=0.9,
            rationale="Architectural innovation with new graph stage",
        )
        assert result.escalation_trigger is None
