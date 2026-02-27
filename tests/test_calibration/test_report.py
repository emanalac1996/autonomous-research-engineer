"""Tests for calibration report generator (WU 5.4)."""

from research_engineer.calibration.report import (
    CalibrationInput,
    CalibrationReport,
    CalibrationReportMarkdown,
    generate_report,
    render_markdown,
)
from research_engineer.calibration.tracker import AccuracyRecord, AccuracyTracker
from research_engineer.classifier.types import InnovationType


def _make_tracker_with_mix(tmp_path) -> AccuracyTracker:
    """Build a tracker with 4 correct + 2 wrong records."""
    tracker = AccuracyTracker(store_path=tmp_path / "report_test.jsonl")
    for i, itype in enumerate(InnovationType):
        tracker.add_record(AccuracyRecord(
            paper_id=f"report-ok-{i}",
            predicted_type=itype,
            ground_truth_type=itype,
            confidence=0.85,
        ))
    tracker.add_record(AccuracyRecord(
        paper_id="report-miss-1",
        predicted_type=InnovationType.parameter_tuning,
        ground_truth_type=InnovationType.modular_swap,
        confidence=0.55,
    ))
    tracker.add_record(AccuracyRecord(
        paper_id="report-miss-2",
        predicted_type=InnovationType.pipeline_restructuring,
        ground_truth_type=InnovationType.architectural_innovation,
        confidence=0.50,
    ))
    return tracker


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_returns_calibration_report(self, seeded_artifact_registry, tmp_path):
        """generate_report returns a CalibrationReport with all fields."""
        tracker = _make_tracker_with_mix(tmp_path)
        input = CalibrationInput(
            tracker=tracker,
            registry=seeded_artifact_registry,
        )
        report = generate_report(input)
        assert isinstance(report, CalibrationReport)
        assert report.total_papers == 6
        assert report.repo_name == "autonomous-research-engineer"

    def test_accuracy_matches_tracker(self, seeded_artifact_registry, tmp_path):
        """report.accuracy_report matches tracker.report()."""
        tracker = _make_tracker_with_mix(tmp_path)
        input = CalibrationInput(
            tracker=tracker,
            registry=seeded_artifact_registry,
        )
        report = generate_report(input)
        direct = tracker.report()
        assert report.accuracy_report.overall_accuracy == direct.overall_accuracy
        assert report.accuracy_report.total_records == direct.total_records

    def test_has_maturity_assessment(self, seeded_artifact_registry, tmp_path):
        """report has maturity_assessment populated."""
        tracker = _make_tracker_with_mix(tmp_path)
        input = CalibrationInput(
            tracker=tracker,
            registry=seeded_artifact_registry,
        )
        report = generate_report(input)
        assert report.maturity_assessment is not None
        assert report.maturity_assessment.repo == "autonomous-research-engineer"


class TestRenderMarkdown:
    """Tests for render_markdown function."""

    def test_contains_section_headers(self, seeded_artifact_registry, tmp_path):
        """Markdown output contains expected section headers."""
        tracker = _make_tracker_with_mix(tmp_path)
        input = CalibrationInput(
            tracker=tracker,
            registry=seeded_artifact_registry,
        )
        report = generate_report(input)
        md = render_markdown(report)

        assert isinstance(md, CalibrationReportMarkdown)
        assert "## Accuracy Summary" in md.content
        assert "## Confusion Matrix" in md.content
        assert "## Maturity Assessment" in md.content
        assert "## Recommendation" in md.content

    def test_contains_accuracy_value(self, seeded_artifact_registry, tmp_path):
        """Markdown includes the overall accuracy percentage."""
        tracker = _make_tracker_with_mix(tmp_path)
        input = CalibrationInput(
            tracker=tracker,
            registry=seeded_artifact_registry,
        )
        report = generate_report(input)
        md = render_markdown(report)

        # 4/6 = 66.7%
        assert "66.7%" in md.content
