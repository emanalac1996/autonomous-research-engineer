"""Tests for serializer: ADR-005 Tier 1 markdown rendering and round-trip."""

from pathlib import Path

import pytest

from agent_factors.dag.parser import parse_blueprint
from agent_factors.dag.validator import validate_dag

from research_engineer.translator.serializer import serialize_blueprint, write_blueprint
from research_engineer.translator.translator import TranslationInput, translate


def _make_result(summary, classification, manifests_dir=None, ledger_path=None):
    """Helper to produce a TranslationResult."""
    inp = TranslationInput(
        summary=summary,
        classification=classification,
        manifests_dir=manifests_dir,
        ledger_path=ledger_path,
        date="2026-02-27",
    )
    return translate(inp)


class TestSerializeBlueprint:
    """Tests for serialize_blueprint rendering."""

    def test_returns_nonempty_string_starting_with_hash(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        result = _make_result(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
        )
        md = serialize_blueprint(result)
        assert isinstance(md, str)
        assert len(md) > 0
        assert md.startswith("# ")

    def test_contains_date_and_status(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        result = _make_result(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
        )
        md = serialize_blueprint(result)
        assert "**Date:**" in md
        assert "**Status:**" in md

    def test_contains_wu_table_header(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
    ):
        result = _make_result(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
        )
        md = serialize_blueprint(result)
        assert "| Working Unit |" in md

    def test_contains_wu_ids(
        self,
        sample_modular_swap_summary,
        sample_classification_modular_swap,
    ):
        result = _make_result(
            sample_modular_swap_summary,
            sample_classification_modular_swap,
        )
        md = serialize_blueprint(result)
        for wu in result.blueprint.all_working_units():
            assert f"Working Unit {wu.id}" in md

    def test_depends_on_dash_for_empty(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
    ):
        result = _make_result(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
        )
        md = serialize_blueprint(result)
        # First WU has no dependencies → should show "---"
        assert "---" in md

    def test_round_trip_parameter_tuning(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
        tmp_path,
    ):
        result = _make_result(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
        )
        path = write_blueprint(result, tmp_path)
        parsed = parse_blueprint(path)
        report = validate_dag(parsed)
        assert report.overall_passed, f"Failed: {report.failed_checks}"

    def test_round_trip_architectural(
        self,
        sample_architectural_summary,
        sample_classification_architectural,
        tmp_path,
    ):
        result = _make_result(
            sample_architectural_summary,
            sample_classification_architectural,
        )
        path = write_blueprint(result, tmp_path)
        parsed = parse_blueprint(path)
        report = validate_dag(parsed)
        assert report.overall_passed, f"Failed: {report.failed_checks}"


class TestWriteBlueprint:
    """Tests for write_blueprint file output."""

    def test_creates_file_at_expected_path(
        self,
        sample_parameter_tuning_summary,
        sample_classification_parameter_tuning,
        tmp_blueprint_output_dir,
    ):
        result = _make_result(
            sample_parameter_tuning_summary,
            sample_classification_parameter_tuning,
        )
        path = write_blueprint(result, tmp_blueprint_output_dir)
        assert path.exists()
        assert path.suffix == ".md"
        assert path.parent == tmp_blueprint_output_dir
        content = path.read_text()
        assert "# " in content
