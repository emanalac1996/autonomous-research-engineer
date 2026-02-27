"""Tests for wu_decomposer: WU decomposition by innovation type."""

import pytest

from agent_factors.dag.schema import Blueprint, Phase, WorkingUnit, WUStatus
from agent_factors.dag.validator import validate_dag

from research_engineer.classifier.types import InnovationType
from research_engineer.translator.manifest_targeter import FileTargeting
from research_engineer.translator.wu_decomposer import (
    DEFAULT_WU_RANGES,
    DecompositionConfig,
    _adjust_wu_count,
    decompose,
    validate_decomposition,
)


class TestDecompositionConfig:
    """DecompositionConfig model tests."""

    def test_construction_with_defaults(self):
        config = DecompositionConfig()
        assert "parameter_tuning" in config.wu_count_ranges
        assert config.test_ratio == 3.0
        assert config.default_effort == "1-2 days"


class TestDecompose:
    """Tests for decompose() across all innovation types."""

    def test_parameter_tuning_returns_1_to_3_wus(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        wus = decompose(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
            FileTargeting(),
        )
        assert 1 <= len(wus) <= 3

    def test_modular_swap_returns_3_to_5_wus(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
        sample_file_targeting_modular_swap,
    ):
        wus = decompose(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
            sample_file_targeting_modular_swap,
        )
        assert 3 <= len(wus) <= 5

    def test_pipeline_restructuring_returns_5_to_12_wus(
        self,
        sample_pipeline_restructuring_summary,
        sample_classification_pipeline_restructuring,
    ):
        wus = decompose(
            sample_pipeline_restructuring_summary,
            sample_classification_pipeline_restructuring,
            FileTargeting(),
        )
        assert 5 <= len(wus) <= 12

    def test_architectural_returns_8_to_20_wus(
        self,
        sample_architectural_summary,
        sample_classification_architectural,
    ):
        wus = decompose(
            sample_architectural_summary,
            sample_classification_architectural,
            FileTargeting(),
        )
        assert 8 <= len(wus) <= 20

    def test_all_wu_ids_valid_format(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
        sample_file_targeting_modular_swap,
    ):
        import re
        wus = decompose(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
            sample_file_targeting_modular_swap,
        )
        for wu in wus:
            assert re.match(r"^\d+(\.\d+)+$", wu.id), f"Invalid WU ID: {wu.id}"

    def test_all_decompositions_pass_dag_validation(
        self,
        sample_architectural_summary,
        sample_classification_architectural,
    ):
        wus = decompose(
            sample_architectural_summary,
            sample_classification_architectural,
            FileTargeting(),
        )
        blueprint = Blueprint(
            name="test",
            phases=[Phase(id="1", working_units=wus)],
        )
        report = validate_dag(blueprint)
        assert report.overall_passed, f"Failed checks: {report.failed_checks}"

    def test_first_wu_no_deps_last_reachable(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
    ):
        wus = decompose(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
            FileTargeting(),
        )
        assert wus[0].depends_on == []
        # Verify last WU is reachable (DAG validation covers this)
        blueprint = Blueprint(
            name="test",
            phases=[Phase(id="1", working_units=wus)],
        )
        report = validate_dag(blueprint)
        assert report.overall_passed

    def test_files_populated_on_some_wus(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
        sample_file_targeting_modular_swap,
    ):
        wus = decompose(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
            sample_file_targeting_modular_swap,
        )
        has_files = any(
            wu.files_created or wu.files_modified for wu in wus
        )
        assert has_files

    def test_acceptance_criteria_nonempty(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        wus = decompose(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
            FileTargeting(),
        )
        for wu in wus:
            assert wu.acceptance_criteria, f"WU {wu.id} missing acceptance criteria"


class TestAdjustWuCount:
    """Tests for _adjust_wu_count with historical data."""

    def test_nudges_count_with_historical_data(self, sample_change_pattern_report):
        from research_engineer.translator.wu_decomposer import _adjust_wu_count

        config = DecompositionConfig()
        result = _adjust_wu_count(
            5, "modular_swap", sample_change_pattern_report, config
        )
        assert 3 <= result <= 5


class TestValidateDecomposition:
    """Tests for validate_decomposition."""

    def test_returns_false_for_circular_dependency(self):
        wus = [
            WorkingUnit(
                id="1.1",
                description="A",
                depends_on=["1.2"],
                acceptance_criteria="done",
            ),
            WorkingUnit(
                id="1.2",
                description="B",
                depends_on=["1.1"],
                acceptance_criteria="done",
            ),
        ]
        assert validate_decomposition(wus, "parameter_tuning") is False
