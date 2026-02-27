"""Accuracy tracker: record classification predictions vs ground truth.

Persists AccuracyRecords to JSONL, computes confusion matrices,
per-type precision/recall/F1, and overall accuracy metrics.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from research_engineer.classifier.types import InnovationType


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AccuracyRecord(BaseModel):
    """Single classification accuracy record: predicted vs ground truth."""

    model_config = ConfigDict()

    paper_id: str
    predicted_type: InnovationType
    ground_truth_type: InnovationType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def is_correct(self) -> bool:
        return self.predicted_type == self.ground_truth_type

    @field_validator("paper_id")
    @classmethod
    def paper_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("paper_id must not be empty")
        return v


class ClassificationConfusionMatrix(BaseModel):
    """4x4 confusion matrix for the innovation type classifier."""

    model_config = ConfigDict()

    matrix: dict[str, dict[str, int]]
    labels: list[str]
    total_records: int
    correct_count: int

    @computed_field
    @property
    def overall_accuracy(self) -> float:
        return self.correct_count / self.total_records if self.total_records > 0 else 0.0


class PerTypeAccuracy(BaseModel):
    """Accuracy metrics for a single innovation type."""

    model_config = ConfigDict()

    innovation_type: InnovationType
    true_positives: int
    false_positives: int
    false_negatives: int
    total_actual: int

    @computed_field
    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @computed_field
    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @computed_field
    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


class AccuracyReport(BaseModel):
    """Full accuracy report from the tracker."""

    model_config = ConfigDict()

    confusion_matrix: ClassificationConfusionMatrix
    per_type: list[PerTypeAccuracy]
    overall_accuracy: float
    total_records: int
    confidence_accuracy_correlation: float


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------


class AccuracyTracker:
    """Track classification accuracy over time.

    Persists records to a JSONL file and computes accuracy metrics.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        """Initialize tracker, optionally loading existing records.

        Args:
            store_path: Path to JSONL file for persistence. If None,
                        records are only kept in memory.
        """
        self._store_path = store_path
        self._records: list[AccuracyRecord] = []

        if store_path and store_path.exists():
            with open(store_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._records.append(
                            AccuracyRecord.model_validate_json(line)
                        )

    def add_record(self, record: AccuracyRecord) -> None:
        """Add a record and persist to JSONL if store_path is set."""
        self._records.append(record)
        if self._store_path:
            with open(self._store_path, "a") as f:
                f.write(record.model_dump_json() + "\n")

    def records(self) -> list[AccuracyRecord]:
        """Return all records."""
        return list(self._records)

    def confusion_matrix(self) -> ClassificationConfusionMatrix:
        """Compute 4x4 confusion matrix from all records."""
        labels = [t.value for t in InnovationType]
        matrix: dict[str, dict[str, int]] = {
            pred: {actual: 0 for actual in labels} for pred in labels
        }
        correct = 0

        for rec in self._records:
            matrix[rec.predicted_type.value][rec.ground_truth_type.value] += 1
            if rec.is_correct:
                correct += 1

        return ClassificationConfusionMatrix(
            matrix=matrix,
            labels=labels,
            total_records=len(self._records),
            correct_count=correct,
        )

    def per_type_accuracy(self) -> list[PerTypeAccuracy]:
        """Compute per-type precision/recall/F1."""
        labels = list(InnovationType)
        cm = self.confusion_matrix()
        result: list[PerTypeAccuracy] = []

        for itype in labels:
            tp = cm.matrix[itype.value][itype.value]
            fp = sum(
                cm.matrix[itype.value][other.value]
                for other in labels
                if other != itype
            )
            fn = sum(
                cm.matrix[other.value][itype.value]
                for other in labels
                if other != itype
            )
            total_actual = sum(
                cm.matrix[pred.value][itype.value] for pred in labels
            )
            result.append(
                PerTypeAccuracy(
                    innovation_type=itype,
                    true_positives=tp,
                    false_positives=fp,
                    false_negatives=fn,
                    total_actual=total_actual,
                )
            )

        return result

    def report(self) -> AccuracyReport:
        """Generate full accuracy report."""
        cm = self.confusion_matrix()
        per_type = self.per_type_accuracy()
        corr = self.confidence_accuracy_correlation()

        return AccuracyReport(
            confusion_matrix=cm,
            per_type=per_type,
            overall_accuracy=cm.overall_accuracy,
            total_records=cm.total_records,
            confidence_accuracy_correlation=corr,
        )

    def misclassifications(self) -> list[AccuracyRecord]:
        """Return only misclassified records."""
        return [r for r in self._records if not r.is_correct]

    def confidence_accuracy_correlation(self) -> float:
        """Compute point-biserial correlation between confidence and correctness.

        Uses stdlib only (no numpy). Returns 0.0 if insufficient data
        or zero variance.
        """
        if len(self._records) < 2:
            return 0.0

        correct_confs = [r.confidence for r in self._records if r.is_correct]
        incorrect_confs = [r.confidence for r in self._records if not r.is_correct]

        if not correct_confs or not incorrect_confs:
            return 0.0

        n = len(self._records)
        n1 = len(correct_confs)
        n0 = len(incorrect_confs)

        mean_correct = sum(correct_confs) / n1
        mean_incorrect = sum(incorrect_confs) / n0

        all_confs = [r.confidence for r in self._records]
        mean_all = sum(all_confs) / n
        var_all = sum((c - mean_all) ** 2 for c in all_confs) / n

        if var_all == 0:
            return 0.0

        std_all = math.sqrt(var_all)
        r_pb = (mean_correct - mean_incorrect) / std_all * math.sqrt(n1 * n0 / (n * n))

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, r_pb))
