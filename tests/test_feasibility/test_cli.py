"""Tests for feasibility CLI scripts (WU 3.6)."""

import json
from pathlib import Path

import yaml

from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary


def _write_synthetic_manifest(manifests_dir: Path) -> None:
    """Write a synthetic manifest YAML to directory."""
    manifest = {
        "repo_name": "test-repo",
        "version": "1.0.0",
        "functions": [
            {
                "name": "bm25_search",
                "module_path": "test.retriever",
                "source_file": "src/test/retriever.py",
                "docstring": "BM25 sparse retrieval function",
            },
            {
                "name": "dense_search",
                "module_path": "test.retriever",
                "source_file": "src/test/retriever.py",
            },
            {
                "name": "reciprocal_rank_fusion",
                "module_path": "test.fusion",
                "source_file": "src/test/fusion.py",
            },
        ],
        "classes": [],
        "module_tree": {
            "test.retriever": ["bm25_search", "dense_search"],
            "test.fusion": ["reciprocal_rank_fusion"],
        },
    }
    with open(manifests_dir / "test-repo.yaml", "w") as f:
        yaml.dump(manifest, f)


class TestCheckFeasibilityScript:
    """Tests for scripts/check_feasibility.py."""

    def test_script_exists(self, repo_root):
        """Script file exists."""
        assert (repo_root / "scripts" / "check_feasibility.py").is_file()

    def test_importable_with_main(self):
        """Script is importable and has main() function."""
        from scripts.check_feasibility import main
        assert callable(main)

    def test_end_to_end_parameter_tuning(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        """End-to-end: parameter_tuning summary + classification -> exit 0."""
        # Write summary JSON
        summary_path = tmp_path / "summary.json"
        summary_path.write_text(sample_parameter_tuning_summary.model_dump_json())

        # Write classification JSON
        classification = ClassificationResult(
            innovation_type=InnovationType.parameter_tuning,
            confidence=0.85,
            rationale="Test parameter tuning classification",
        )
        classification_path = tmp_path / "classification.json"
        classification_path.write_text(classification.model_dump_json())

        # Write synthetic manifest
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        _write_synthetic_manifest(manifests_dir)

        from scripts.check_feasibility import main
        exit_code = main([
            "--input", str(summary_path),
            "--classification", str(classification_path),
            "--manifests-dir", str(manifests_dir),
        ])
        assert exit_code == 0  # FEASIBLE or FEASIBLE_WITH_ADAPTATION

    def test_exit_code_2_on_invalid_json(self, tmp_path):
        """Invalid JSON input returns exit code 2."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("not valid json {{{")
        classification_path = tmp_path / "classification.json"
        classification_path.write_text("also bad json")

        from scripts.check_feasibility import main
        exit_code = main([
            "--input", str(bad_json),
            "--classification", str(classification_path),
        ])
        assert exit_code == 2


class TestBuildDepGraphScript:
    """Tests for scripts/build_dep_graph.py."""

    def test_script_exists(self, repo_root):
        """Script file exists."""
        assert (repo_root / "scripts" / "build_dep_graph.py").is_file()

    def test_importable_with_main(self):
        """Script is importable and has main() function."""
        from scripts.build_dep_graph import main
        assert callable(main)

    def test_stats_with_synthetic(self, tmp_path):
        """--stats returns exit code 0 with synthetic manifests."""
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        _write_synthetic_manifest(manifests_dir)

        from scripts.build_dep_graph import main
        exit_code = main(["--manifests-dir", str(manifests_dir), "--stats"])
        assert exit_code == 0

    def test_default_with_synthetic(self, tmp_path):
        """Default (no flags) returns exit code 0 with synthetic manifests."""
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        _write_synthetic_manifest(manifests_dir)

        from scripts.build_dep_graph import main
        exit_code = main(["--manifests-dir", str(manifests_dir)])
        assert exit_code == 0
