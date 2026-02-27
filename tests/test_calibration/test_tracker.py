"""Tests for accuracy tracker (WU 5.1)."""

from research_engineer.calibration.tracker import (
    AccuracyRecord,
    AccuracyReport,
    AccuracyTracker,
    ClassificationConfusionMatrix,
    PerTypeAccuracy,
)
from research_engineer.classifier.types import InnovationType


def _make_sample_records() -> list[AccuracyRecord]:
    """Build 6 sample records: 4 correct, 2 wrong."""
    return [
        AccuracyRecord(
            paper_id="paper-001",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.parameter_tuning,
            confidence=0.85,
            rationale="Correct parameter tuning",
        ),
        AccuracyRecord(
            paper_id="paper-002",
            predicted_type=InnovationType.modular_swap,
            ground_truth_type=InnovationType.modular_swap,
            confidence=0.78,
            rationale="Correct modular swap",
        ),
        AccuracyRecord(
            paper_id="paper-003",
            predicted_type=InnovationType.pipeline_restructuring,
            ground_truth_type=InnovationType.pipeline_restructuring,
            confidence=0.72,
            rationale="Correct pipeline restructuring",
        ),
        AccuracyRecord(
            paper_id="paper-004",
            predicted_type=InnovationType.architectural_innovation,
            ground_truth_type=InnovationType.architectural_innovation,
            confidence=0.81,
            rationale="Correct architectural",
        ),
        # Misclassifications
        AccuracyRecord(
            paper_id="paper-005",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.modular_swap,
            confidence=0.55,
            rationale="Misclassified swap as tuning",
        ),
        AccuracyRecord(
            paper_id="paper-006",
            predicted_type=InnovationType.pipeline_restructuring,
            ground_truth_type=InnovationType.architectural_innovation,
            confidence=0.60,
            rationale="Misclassified architectural as restructuring",
        ),
    ]


class TestAccuracyRecord:
    """Tests for AccuracyRecord model."""

    def test_creation_and_is_correct(self):
        """AccuracyRecord with matching types has is_correct=True."""
        rec = AccuracyRecord(
            paper_id="test-1",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.parameter_tuning,
            confidence=0.9,
        )
        assert rec.is_correct is True

        rec2 = AccuracyRecord(
            paper_id="test-2",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.modular_swap,
            confidence=0.5,
        )
        assert rec2.is_correct is False

    def test_json_roundtrip(self):
        """AccuracyRecord round-trips through JSON."""
        original = AccuracyRecord(
            paper_id="test-rt",
            predicted_type=InnovationType.modular_swap,
            ground_truth_type=InnovationType.modular_swap,
            confidence=0.75,
            rationale="test roundtrip",
        )
        json_str = original.model_dump_json()
        restored = AccuracyRecord.model_validate_json(json_str)
        assert restored.paper_id == original.paper_id
        assert restored.predicted_type == original.predicted_type
        assert restored.is_correct == original.is_correct


class TestAccuracyTracker:
    """Tests for AccuracyTracker class."""

    def test_add_and_retrieve(self):
        """add_record then records() returns the record."""
        tracker = AccuracyTracker()
        rec = AccuracyRecord(
            paper_id="add-1",
            predicted_type=InnovationType.parameter_tuning,
            ground_truth_type=InnovationType.parameter_tuning,
            confidence=0.9,
        )
        tracker.add_record(rec)
        assert len(tracker.records()) == 1
        assert tracker.records()[0].paper_id == "add-1"

    def test_confusion_matrix_correct(self):
        """Confusion matrix counts are correct for sample data."""
        tracker = AccuracyTracker()
        for rec in _make_sample_records():
            tracker.add_record(rec)

        cm = tracker.confusion_matrix()
        assert cm.total_records == 6
        assert cm.correct_count == 4
        # Check specific cells: param_tuning predicted 2x (1 correct + 1 wrong)
        assert cm.matrix["parameter_tuning"]["parameter_tuning"] == 1
        assert cm.matrix["parameter_tuning"]["modular_swap"] == 1

    def test_per_type_accuracy(self):
        """Per-type precision/recall/F1 are computed correctly."""
        tracker = AccuracyTracker()
        for rec in _make_sample_records():
            tracker.add_record(rec)

        per_type = tracker.per_type_accuracy()
        # parameter_tuning: TP=1, FP=1 (predicted param but was swap), FN=0
        pt = next(p for p in per_type if p.innovation_type == InnovationType.parameter_tuning)
        assert pt.true_positives == 1
        assert pt.false_positives == 1
        assert pt.precision == 0.5  # 1/(1+1)
        assert pt.recall == 1.0  # 1/(1+0)

    def test_overall_accuracy(self):
        """Overall accuracy = 4/6 ≈ 0.667."""
        tracker = AccuracyTracker()
        for rec in _make_sample_records():
            tracker.add_record(rec)

        report = tracker.report()
        assert abs(report.overall_accuracy - 4 / 6) < 0.01

    def test_misclassifications_returns_only_wrong(self):
        """misclassifications() returns only the 2 misclassified records."""
        tracker = AccuracyTracker()
        for rec in _make_sample_records():
            tracker.add_record(rec)

        misses = tracker.misclassifications()
        assert len(misses) == 2
        assert all(not r.is_correct for r in misses)
        paper_ids = {r.paper_id for r in misses}
        assert paper_ids == {"paper-005", "paper-006"}

    def test_persistence_to_jsonl(self, tmp_path):
        """Records survive tracker re-initialization from same file."""
        store = tmp_path / "accuracy.jsonl"
        tracker1 = AccuracyTracker(store_path=store)
        for rec in _make_sample_records():
            tracker1.add_record(rec)

        # Re-create tracker from same file
        tracker2 = AccuracyTracker(store_path=store)
        assert len(tracker2.records()) == 6
        assert tracker2.confusion_matrix().correct_count == 4
