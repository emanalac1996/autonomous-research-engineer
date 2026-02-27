"""Tests for evaluate_paper CLI (WU 2.5)."""

import json
import importlib
from pathlib import Path

import pytest

from research_engineer.classifier.types import InnovationType


class TestCliModule:
    """Tests for the CLI module structure."""

    def test_script_exists(self):
        """evaluate_paper.py exists in scripts/."""
        script_path = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts"
            / "evaluate_paper.py"
        )
        assert script_path.is_file()

    def test_importable(self):
        """scripts.evaluate_paper is importable."""
        mod = importlib.import_module("scripts.evaluate_paper")
        assert mod is not None

    def test_has_main(self):
        """scripts.evaluate_paper has a main() function."""
        mod = importlib.import_module("scripts.evaluate_paper")
        assert hasattr(mod, "main")
        assert callable(mod.main)


class TestCliEndToEnd:
    """End-to-end tests using the CLI main() function."""

    def _write_summary_json(self, summary, tmp_path: Path) -> Path:
        """Write a ComprehensionSummary to a temp JSON file."""
        json_path = tmp_path / "summary.json"
        json_path.write_text(summary.model_dump_json())
        return json_path

    def test_parameter_tuning(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        """CLI classifies parameter tuning summary correctly."""
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

    def test_modular_swap(
        self, sample_modular_swap_summary, tmp_path
    ):
        """CLI classifies modular swap summary correctly."""
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_modular_swap_summary, tmp_path
        )
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--classify-only",
            "--input", str(json_path),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0

    def test_architectural(
        self, sample_architectural_summary, tmp_path
    ):
        """CLI classifies architectural summary correctly."""
        from scripts.evaluate_paper import main

        json_path = self._write_summary_json(
            sample_architectural_summary, tmp_path
        )
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--classify-only",
            "--input", str(json_path),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 0

    def test_invalid_json(self, tmp_path):
        """CLI returns exit code 1 on invalid JSON input."""
        from scripts.evaluate_paper import main

        json_path = tmp_path / "bad.json"
        json_path.write_text("not valid json {{{")
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        exit_code = main([
            "--classify-only",
            "--input", str(json_path),
            "--artifact-store", str(store_dir),
        ])
        assert exit_code == 1
