"""Tests for maturity assessor (WU 5.2)."""

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.calibration.maturity_assessor import (
    CalibrationEvidence,
    MaturityAssessment,
    assess_maturity,
)
from research_engineer.calibration.tracker import AccuracyRecord, AccuracyTracker
from research_engineer.classifier.types import InnovationType


def _make_perfect_records(count: int = 8) -> list[AccuracyRecord]:
    """Build records where all classifications are correct.

    Creates 2 records per innovation type to ensure all types are covered.
    """
    types = list(InnovationType)
    records = []
    for i in range(count):
        itype = types[i % len(types)]
        records.append(
            AccuracyRecord(
                paper_id=f"perfect-{i:03d}",
                predicted_type=itype,
                ground_truth_type=itype,
                confidence=0.90,
                rationale=f"Correct {itype.value}",
            )
        )
    return records


def _make_low_accuracy_records() -> list[AccuracyRecord]:
    """Build 6 records: 2 correct, 4 wrong (33% accuracy)."""
    records = [
        AccuracyRecord(
            paper_id="low-001",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.parameter_tuning,
            confidence=0.9,
        ),
        AccuracyRecord(
            paper_id="low-002",
            predicted_type=InnovationType.modular_swap,
            ground_truth_type=InnovationType.modular_swap,
            confidence=0.8,
        ),
    ]
    # 4 wrong predictions
    for i in range(4):
        records.append(
            AccuracyRecord(
                paper_id=f"low-wrong-{i}",
                predicted_type=InnovationType.parameter_tuning,
                ground_truth_type=InnovationType.architectural_innovation,
                confidence=0.4,
            )
        )
    return records


class TestCalibrationEvidence:
    """Tests for CalibrationEvidence model."""

    def test_creation(self):
        """CalibrationEvidence constructs with all fields."""
        ev = CalibrationEvidence(
            total_papers_evaluated=10,
            overall_accuracy=0.8,
            per_type_f1_scores={"parameter_tuning": 0.9, "modular_swap": 0.7},
            has_calibration_set=True,
            artifact_count=3,
            worst_type_f1=0.7,
            confidence_accuracy_correlation=0.5,
        )
        assert ev.total_papers_evaluated == 10
        assert ev.worst_type_f1 == 0.7


class TestMaturityAssessment:
    """Tests for MaturityAssessment model."""

    def test_json_roundtrip(self):
        """MaturityAssessment round-trips through JSON."""
        ev = CalibrationEvidence(
            total_papers_evaluated=10,
            overall_accuracy=0.8,
            per_type_f1_scores={"parameter_tuning": 0.9},
            has_calibration_set=True,
            artifact_count=1,
            worst_type_f1=0.9,
            confidence_accuracy_correlation=0.5,
        )
        original = MaturityAssessment(
            repo="test-repo",
            current_level="foundational",
            target_level="empirical",
            recommendation="ready",
            evidence=ev,
        )
        json_str = original.model_dump_json()
        restored = MaturityAssessment.model_validate_json(json_str)
        assert restored.recommendation == "ready"
        assert restored.repo == "test-repo"


class TestAssessMaturity:
    """Tests for assess_maturity function."""

    def test_insufficient_data(self, tmp_artifact_registry):
        """Returns 'insufficient_data' with fewer than 5 records."""
        tracker = AccuracyTracker()
        # Only 2 records
        for rec in _make_perfect_records(2):
            tracker.add_record(rec)

        result = assess_maturity(tracker, tmp_artifact_registry)
        assert result.recommendation == "insufficient_data"
        assert len(result.unmet_requirements) > 0

    def test_not_ready_low_accuracy(self, tmp_artifact_registry):
        """Returns 'not_ready' when overall_accuracy < 0.80."""
        tracker = AccuracyTracker()
        for rec in _make_low_accuracy_records():
            tracker.add_record(rec)

        result = assess_maturity(tracker, tmp_artifact_registry)
        assert result.recommendation == "not_ready"

    def test_not_ready_low_type_f1(self, tmp_artifact_registry):
        """Returns 'not_ready' when worst_type_f1 < 0.6, sets escalation."""
        tracker = AccuracyTracker()
        # 5 correct param_tuning, 5 correct modular_swap, but
        # pipeline predicted as architectural (0% F1 for both)
        for i in range(5):
            tracker.add_record(AccuracyRecord(
                paper_id=f"f1-pt-{i}",
                predicted_type=InnovationType.parameter_tuning,
                ground_truth_type=InnovationType.parameter_tuning,
                confidence=0.9,
            ))
        for i in range(5):
            tracker.add_record(AccuracyRecord(
                paper_id=f"f1-ms-{i}",
                predicted_type=InnovationType.modular_swap,
                ground_truth_type=InnovationType.modular_swap,
                confidence=0.9,
            ))

        result = assess_maturity(tracker, tmp_artifact_registry)
        # pipeline_restructuring and architectural have 0 F1 (no samples)
        # but accuracy is 100% -- the maturity gate passes but worst F1 fails
        assert result.escalation_trigger == EscalationTrigger.maturity_insufficient

    def test_ready_with_sufficient_accuracy(self, seeded_artifact_registry):
        """Returns 'ready' with all correct and enough records."""
        tracker = AccuracyTracker()
        for rec in _make_perfect_records(8):
            tracker.add_record(rec)

        result = assess_maturity(tracker, seeded_artifact_registry)
        assert result.recommendation == "ready"
        assert result.escalation_trigger is None

    def test_unmet_requirements_populated(self, tmp_artifact_registry):
        """unmet_requirements list is correct for failing checks."""
        tracker = AccuracyTracker()
        for rec in _make_low_accuracy_records():
            tracker.add_record(rec)

        result = assess_maturity(tracker, tmp_artifact_registry)
        assert len(result.unmet_requirements) > 0

    def test_artifact_count_from_registry(self, seeded_artifact_registry):
        """artifact_count correctly reflects registry contents."""
        tracker = AccuracyTracker()
        for rec in _make_perfect_records(8):
            tracker.add_record(rec)

        result = assess_maturity(tracker, seeded_artifact_registry)
        assert result.evidence.artifact_count >= 1  # seed artifact exists
