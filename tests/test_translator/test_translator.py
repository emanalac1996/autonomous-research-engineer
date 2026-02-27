"""Tests for translator: blueprint translation orchestrator."""

import pytest

from agent_factors.dag.schema import BlueprintStatus

from research_engineer.translator.translator import (
    TranslationInput,
    TranslationResult,
    translate,
)


class TestTranslationInput:
    """TranslationInput model tests."""

    def test_minimal_construction(
        self, sample_parameter_tuning_summary, sample_classification_parameter_tuning
    ):
        inp = TranslationInput(
            summary=sample_parameter_tuning_summary,
            classification=sample_classification_parameter_tuning,
        )
        assert inp.manifests_dir is None
        assert inp.ledger_path is None


class TestTranslationResult:
    """TranslationResult model tests."""

    def test_has_all_required_fields(
        self, sample_parameter_tuning_summary, sample_classification_parameter_tuning
    ):
        inp = TranslationInput(
            summary=sample_parameter_tuning_summary,
            classification=sample_classification_parameter_tuning,
        )
        result = translate(inp)
        assert result.blueprint is not None
        assert result.validation_report is not None
        assert result.file_targeting is not None
        assert result.change_patterns is not None
        assert result.test_estimate_low > 0
        assert result.test_estimate_high > 0


class TestTranslate:
    """Tests for translate() across innovation types."""

    def test_parameter_tuning_with_manifests(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
        clearinghouse_manifests,
    ):
        inp = TranslationInput(
            summary=sample_parameter_tuning_summary,
            classification=sample_classification_parameter_tuning,
            manifests_dir=clearinghouse_manifests,
        )
        result = translate(inp)
        assert result.blueprint.total_wu_count >= 1
        assert result.validation_report.overall_passed

    def test_modular_swap(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
        clearinghouse_manifests,
    ):
        inp = TranslationInput(
            summary=sample_modular_swap_summary,
            classification=sample_classification_modular_swap,
            manifests_dir=clearinghouse_manifests,
        )
        result = translate(inp)
        assert result.blueprint.total_wu_count >= 3
        assert result.validation_report.overall_passed

    def test_architectural_with_ledger(
        self,
        sample_architectural_summary,
        sample_classification_architectural,
        clearinghouse_manifests,
        clearinghouse_ledger,
    ):
        inp = TranslationInput(
            summary=sample_architectural_summary,
            classification=sample_classification_architectural,
            manifests_dir=clearinghouse_manifests,
            ledger_path=clearinghouse_ledger,
        )
        result = translate(inp)
        assert result.blueprint.total_wu_count >= 8
        assert result.validation_report.overall_passed

    def test_pipeline_restructuring(
        self,
        sample_pipeline_restructuring_summary,
        sample_classification_pipeline_restructuring,
    ):
        inp = TranslationInput(
            summary=sample_pipeline_restructuring_summary,
            classification=sample_classification_pipeline_restructuring,
        )
        result = translate(inp)
        assert result.blueprint.total_wu_count >= 5
        assert result.validation_report.overall_passed

    def test_all_blueprints_pass_dag_validation(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
    ):
        inp = TranslationInput(
            summary=sample_modular_swap_summary,
            classification=sample_classification_modular_swap,
        )
        result = translate(inp)
        assert result.validation_report.overall_passed is True

    def test_blueprint_name_contains_innovation_type(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        inp = TranslationInput(
            summary=sample_parameter_tuning_summary,
            classification=sample_classification_parameter_tuning,
        )
        result = translate(inp)
        name = result.blueprint.name.lower()
        assert len(name) > 0
        assert "parameter tuning" in name or "parameter" in name

    def test_blueprint_metadata_status_planned(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        inp = TranslationInput(
            summary=sample_parameter_tuning_summary,
            classification=sample_classification_parameter_tuning,
        )
        result = translate(inp)
        assert result.blueprint.metadata.status == BlueprintStatus.planned

    def test_test_estimates_positive_low_leq_high(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
    ):
        inp = TranslationInput(
            summary=sample_modular_swap_summary,
            classification=sample_classification_modular_swap,
        )
        result = translate(inp)
        assert result.test_estimate_low > 0
        assert result.test_estimate_high > 0
        assert result.test_estimate_low <= result.test_estimate_high
