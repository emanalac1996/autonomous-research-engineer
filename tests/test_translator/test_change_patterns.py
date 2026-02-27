"""Tests for change_patterns: historical change pattern mining from ledger."""

from pathlib import Path

import pytest

from research_engineer.translator.change_patterns import (
    ChangePatternReport,
    ChangePatternStats,
    DEFAULT_PATTERN_STATS,
    _infer_innovation_type,
    mine_ledger,
)


class TestChangePatternStats:
    """ChangePatternStats model tests."""

    def test_construction_and_json_round_trip(self):
        stats = ChangePatternStats(
            avg_wu_count=5.0,
            avg_test_ratio=3.0,
            sample_count=10,
            common_phase_count=2,
        )
        data = stats.model_dump_json()
        restored = ChangePatternStats.model_validate_json(data)
        assert restored.avg_wu_count == 5.0
        assert restored.sample_count == 10


class TestChangePatternReport:
    """ChangePatternReport model tests."""

    def test_construction_with_empty_dicts(self):
        report = ChangePatternReport(
            by_meta_category={},
            by_innovation_type={},
            total_entries=0,
            entries_with_blueprint_ref=0,
        )
        assert report.total_entries == 0
        assert report.by_meta_category == {}


class TestMineLedger:
    """Tests for mine_ledger against real and synthetic data."""

    def test_real_ledger_returns_positive_total(self, clearinghouse_ledger):
        report = mine_ledger(clearinghouse_ledger)
        assert report.total_entries > 0

    def test_real_ledger_finds_blueprint_refs(self, clearinghouse_ledger):
        report = mine_ledger(clearinghouse_ledger)
        assert report.entries_with_blueprint_ref > 0

    def test_real_ledger_has_entries_with_blueprint_ref(self, clearinghouse_ledger):
        report = mine_ledger(clearinghouse_ledger)
        assert report.entries_with_blueprint_ref >= 1

    def test_real_ledger_has_nonzero_test_ratio(self, clearinghouse_ledger):
        report = mine_ledger(clearinghouse_ledger)
        has_ratio = any(
            stats.avg_test_ratio > 0
            for stats in report.by_innovation_type.values()
        )
        assert has_ratio

    def test_empty_file_returns_defaults(self, tmp_path):
        empty_ledger = tmp_path / "empty.jsonl"
        empty_ledger.write_text("")
        report = mine_ledger(empty_ledger)
        assert report.total_entries == 0
        assert len(report.by_innovation_type) >= 4

    def test_nonexistent_file_returns_defaults(self):
        report = mine_ledger(Path("/nonexistent/ledger.jsonl"))
        assert report.total_entries == 0
        assert len(report.by_innovation_type) >= 4


class TestInferInnovationType:
    """Tests for _infer_innovation_type helper."""

    def test_returns_none_for_unrecognizable(self):
        entry = {"title": "abc xyz 123", "description": "nothing here"}
        assert _infer_innovation_type(entry) is None


class TestDefaultPatternStats:
    """Tests for the DEFAULT_PATTERN_STATS constant."""

    def test_has_all_four_innovation_types(self):
        expected = {
            "parameter_tuning",
            "modular_swap",
            "pipeline_restructuring",
            "architectural_innovation",
        }
        assert set(DEFAULT_PATTERN_STATS.keys()) == expected

    def test_all_values_are_stats(self):
        for stats in DEFAULT_PATTERN_STATS.values():
            assert isinstance(stats, ChangePatternStats)
            assert stats.avg_wu_count > 0
