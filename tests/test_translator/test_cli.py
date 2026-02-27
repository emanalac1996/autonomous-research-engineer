"""Tests for evaluate_paper CLI --translate pipeline (WU 4.6)."""

import importlib
import json
from pathlib import Path

import pytest


class TestCliTranslateModule:
    """Tests for the CLI module with --translate support."""

    def test_script_exists(self):
        script_path = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts"
            / "evaluate_paper.py"
        )
        assert script_path.is_file()

    def test_importable_has_main(self):
        mod = importlib.import_module("scripts.evaluate_paper")
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_translate_flag_accepted(self, tmp_path):
        """--translate flag is accepted without error."""
        from scripts.evaluate_paper import main

        json_path = tmp_path / "empty.json"
        json_path.write_text("{}")
        # Should fail on validation, but --translate flag itself is accepted
        exit_code = main([
            "--translate",
            "--input", str(json_path),
        ])
        # Will be 1 due to validation error, but flag was accepted (no argparse error)
        assert exit_code == 1


class TestCliTranslateEndToEnd:
    """End-to-end tests for --translate pipeline."""

    def _write_summary_json(self, summary, tmp_path: Path) -> Path:
        json_path = tmp_path / "summary.json"
        json_path.write_text(summary.model_dump_json())
        return json_path

    def test_parameter_tuning_creates_blueprint(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_parameter_tuning_summary, tmp_path
        )
        output_dir = tmp_path / "blueprints"
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--translate",
            "--input", str(json_path),
            "--output-dir", str(output_dir),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0
        # Blueprint file should exist
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1

    def test_modular_swap_valid_blueprint(
        self, sample_modular_swap_summary, tmp_path, capsys
    ):
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_modular_swap_summary, tmp_path
        )
        output_dir = tmp_path / "blueprints"
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--translate",
            "--input", str(json_path),
            "--output-dir", str(output_dir),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["validation_passed"] is True
        assert output["wu_count"] >= 3

    def test_written_file_contains_adr005_markers(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_parameter_tuning_summary, tmp_path
        )
        output_dir = tmp_path / "blueprints"
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        main([
            "--translate",
            "--input", str(json_path),
            "--output-dir", str(output_dir),
            "--artifact-store", str(store_dir),
        ])

        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "Working Unit" in content
        assert "**Status:**" in content

    def test_exit_code_0_on_success(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_parameter_tuning_summary, tmp_path
        )
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--translate",
            "--input", str(json_path),
            "--output-dir", str(tmp_path / "out"),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0

    def test_classify_only_still_works(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        """Regression: --classify-only still works after --translate addition."""
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_parameter_tuning_summary, tmp_path
        )
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--classify-only",
            "--input", str(json_path),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0
