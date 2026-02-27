"""Tests for calibration CLI script (WU 5.5)."""

import json

from research_engineer.calibration.tracker import AccuracyRecord, AccuracyTracker
from research_engineer.classifier.types import InnovationType


def _write_sample_records(tmp_path):
    """Write sample AccuracyRecords to a JSONL file and return path."""
    records_path = tmp_path / "test_records.jsonl"
    tracker = AccuracyTracker(store_path=records_path)

    # 4 correct records (one per type)
    for i, itype in enumerate(InnovationType):
        tracker.add_record(AccuracyRecord(
            paper_id=f"cli-{i}",
            predicted_type=itype,
            ground_truth_type=itype,
            confidence=0.85,
        ))

    # 1 misclassification
    tracker.add_record(AccuracyRecord(
        paper_id="cli-miss",
        predicted_type=InnovationType.parameter_tuning,
        ground_truth_type=InnovationType.modular_swap,
        confidence=0.55,
    ))

    return records_path


class TestCalibrationReportScript:
    """Tests for scripts/calibration_report.py."""

    def test_script_exists(self, repo_root):
        """Script file exists."""
        assert (repo_root / "scripts" / "calibration_report.py").is_file()

    def test_importable_has_main(self):
        """Script is importable and has main() function."""
        from scripts.calibration_report import main
        assert callable(main)

    def test_json_output_valid(self, tmp_path):
        """--json produces valid JSON with expected keys."""
        records_path = _write_sample_records(tmp_path)
        store_dir = tmp_path / "art_store"
        store_dir.mkdir()

        from scripts.calibration_report import main
        import io
        import sys

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            exit_code = main([
                "--records", str(records_path),
                "--artifact-store", str(store_dir),
                "--json",
            ])
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        data = json.loads(output)
        assert "repo_name" in data
        assert "overall_accuracy" in data
        assert "maturity_assessment" in data

    def test_markdown_output_contains_headers(self, tmp_path):
        """Default output contains expected markdown section headers."""
        records_path = _write_sample_records(tmp_path)
        store_dir = tmp_path / "art_store"
        store_dir.mkdir()

        from scripts.calibration_report import main
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            main([
                "--records", str(records_path),
                "--artifact-store", str(store_dir),
            ])
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert "## Accuracy Summary" in output
        assert "## Maturity Assessment" in output
