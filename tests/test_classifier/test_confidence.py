"""Tests for confidence scoring (WU 2.4)."""

import pytest

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.confidence import (
    check_escalation,
    compute_confidence,
)
from research_engineer.classifier.types import InnovationType
from research_engineer.comprehension.topology import TopologyChange, TopologyChangeType


def _make_topology(
    change_type: TopologyChangeType = TopologyChangeType.none,
    confidence: float = 0.67,
) -> TopologyChange:
    """Helper to build a TopologyChange quickly."""
    return TopologyChange(
        change_type=change_type,
        affected_stages=[],
        confidence=confidence,
        evidence=["test"],
    )


class TestComputeConfidence:
    """Tests for the compute_confidence function."""

    def test_high_confidence_all_signals_agree(self):
        """High confidence when heuristic, topology, and manifest all agree."""
        topology = _make_topology(TopologyChangeType.none, confidence=0.9)
        conf = compute_confidence(
            heuristic_match_strength=1.0,
            topology=topology,
            innovation_type=InnovationType.parameter_tuning,
            manifest_evidence_count=3,
        )
        assert conf > 0.85

    def test_low_confidence_weak_heuristic(self):
        """Low confidence when heuristic match is weak."""
        topology = _make_topology(TopologyChangeType.none, confidence=0.5)
        conf = compute_confidence(
            heuristic_match_strength=0.1,
            topology=topology,
            innovation_type=InnovationType.parameter_tuning,
            manifest_evidence_count=0,
        )
        assert conf < 0.6

    def test_always_in_zero_one(self):
        """Confidence is always in [0, 1]."""
        for h in [0.0, 0.5, 1.0]:
            for ct in TopologyChangeType:
                topology = _make_topology(ct, confidence=1.0)
                for it in InnovationType:
                    conf = compute_confidence(h, topology, it, 5)
                    assert 0.0 <= conf <= 1.0, f"Out of range: {conf}"

    def test_manifest_evidence_boosts(self):
        """More manifest evidence increases confidence."""
        topology = _make_topology(TopologyChangeType.component_swap)
        conf_0 = compute_confidence(0.5, topology, InnovationType.modular_swap, 0)
        conf_3 = compute_confidence(0.5, topology, InnovationType.modular_swap, 3)
        assert conf_3 > conf_0

    def test_topology_agreement_boosts(self):
        """Agreeing topology boosts confidence vs mismatched."""
        topo_agree = _make_topology(TopologyChangeType.component_swap)
        topo_mismatch = _make_topology(TopologyChangeType.stage_addition)
        conf_agree = compute_confidence(0.5, topo_agree, InnovationType.modular_swap, 0)
        conf_mismatch = compute_confidence(0.5, topo_mismatch, InnovationType.modular_swap, 0)
        assert conf_agree > conf_mismatch

    def test_contradiction_lowers(self):
        """Contradicting topology (parameter_tuning + stage_addition) gives lowest topology contrib."""
        topo_contradict = _make_topology(TopologyChangeType.stage_addition)
        conf = compute_confidence(
            0.5, topo_contradict, InnovationType.parameter_tuning, 0
        )
        # With 0.0 topology agreement and 0 manifest, confidence = 0.5 * 0.5 = 0.25
        assert conf < 0.3

    def test_pipeline_restructuring_agrees_with_flow(self):
        """Pipeline restructuring agrees with flow_restructuring topology."""
        topo = _make_topology(TopologyChangeType.flow_restructuring, confidence=0.8)
        conf = compute_confidence(0.8, topo, InnovationType.pipeline_restructuring, 1)
        assert conf > 0.6


class TestCheckEscalation:
    """Tests for check_escalation."""

    def test_low_confidence_triggers(self):
        """Confidence 0.3 triggers escalation."""
        trigger = check_escalation(0.3, InnovationType.parameter_tuning)
        assert trigger == EscalationTrigger.confidence_below_threshold

    def test_high_confidence_no_trigger(self):
        """Confidence 0.9 does not trigger escalation."""
        trigger = check_escalation(0.9, InnovationType.parameter_tuning)
        assert trigger is None

    def test_threshold_boundary(self):
        """Confidence exactly at 0.6 does not trigger escalation."""
        trigger = check_escalation(0.6, InnovationType.modular_swap)
        assert trigger is None
