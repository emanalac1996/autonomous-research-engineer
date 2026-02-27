"""Tests for manifest_targeter: file targeting from clearinghouse manifests."""

from pathlib import Path

import pytest

from research_engineer.classifier.types import InnovationType
from research_engineer.translator.manifest_targeter import (
    FileTarget,
    FileTargeting,
    identify_targets,
)


class TestFileTarget:
    """FileTarget model construction and serialization."""

    def test_construction_and_json_round_trip(self):
        ft = FileTarget(
            source_file="src/retrieval.py",
            repo_name="multimodal-rag-core",
            reason="matches term 'retrieval'",
        )
        data = ft.model_dump_json()
        restored = FileTarget.model_validate_json(data)
        assert restored.source_file == ft.source_file
        assert restored.repo_name == ft.repo_name
        assert restored.reason == ft.reason


class TestFileTargeting:
    """FileTargeting model validation."""

    def test_construction_with_defaults(self):
        targeting = FileTargeting()
        assert targeting.files_created == []
        assert targeting.files_modified == []
        assert targeting.target_repos == []

    def test_construction_with_values(self):
        targeting = FileTargeting(
            files_created=[
                FileTarget(
                    source_file="src/new.py",
                    repo_name="repo",
                    reason="new module",
                )
            ],
            files_modified=[
                FileTarget(
                    source_file="src/old.py",
                    repo_name="repo",
                    reason="matches term",
                )
            ],
            target_repos=["repo"],
        )
        assert len(targeting.files_created) == 1
        assert len(targeting.files_modified) == 1


class TestIdentifyTargets:
    """Tests for identify_targets against real and synthetic manifests."""

    def test_parameter_tuning_with_manifests(
        self, sample_parameter_tuning_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_parameter_tuning_summary,
            InnovationType.parameter_tuning,
            clearinghouse_manifests,
        )
        assert isinstance(result, FileTargeting)
        # parameter_tuning should produce no files_created
        assert len(result.files_created) == 0

    def test_modular_swap_has_files_modified(
        self, sample_modular_swap_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_modular_swap_summary,
            InnovationType.modular_swap,
            clearinghouse_manifests,
        )
        assert len(result.files_modified) >= 1

    def test_modular_swap_has_files_created(
        self, sample_modular_swap_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_modular_swap_summary,
            InnovationType.modular_swap,
            clearinghouse_manifests,
        )
        assert len(result.files_created) >= 1

    def test_architectural_has_files_created(
        self, sample_architectural_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_architectural_summary,
            InnovationType.architectural_innovation,
            clearinghouse_manifests,
        )
        assert len(result.files_created) >= 2

    def test_target_repos_populated(
        self, sample_modular_swap_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_modular_swap_summary,
            InnovationType.modular_swap,
            clearinghouse_manifests,
        )
        assert len(result.target_repos) >= 1
        for repo in result.target_repos:
            assert isinstance(repo, str) and len(repo) > 0

    def test_handles_missing_manifests_dir(self, sample_parameter_tuning_summary):
        result = identify_targets(
            sample_parameter_tuning_summary,
            InnovationType.parameter_tuning,
            Path("/nonexistent/manifests"),
        )
        assert isinstance(result, FileTargeting)
        assert len(result.files_modified) == 0

    def test_handles_empty_manifests_dir(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        empty_dir = tmp_path / "empty_manifests"
        empty_dir.mkdir()
        result = identify_targets(
            sample_parameter_tuning_summary,
            InnovationType.parameter_tuning,
            empty_dir,
        )
        assert isinstance(result, FileTargeting)
        assert len(result.files_modified) == 0

    def test_all_source_files_non_empty(
        self, sample_modular_swap_summary, clearinghouse_manifests
    ):
        result = identify_targets(
            sample_modular_swap_summary,
            InnovationType.modular_swap,
            clearinghouse_manifests,
        )
        for ft in result.files_modified + result.files_created:
            assert isinstance(ft.source_file, str)
            assert len(ft.source_file) > 0
