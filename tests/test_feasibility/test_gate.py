"""Tests for feasibility gate orchestrator (WU 3.5)."""

import yaml

from agent_factors.g_layer.escalation import EscalationTrigger

from research_engineer.classifier.types import ClassificationResult, InnovationType
from research_engineer.feasibility.blast_radius import BlastRadiusReport, RiskLevel
from research_engineer.feasibility.gate import (
    FeasibilityResult,
    FeasibilityStatus,
    _build_operations_list,
    _gate_architectural_innovation,
    _gate_modular_swap,
    _gate_parameter_tuning,
    _gate_pipeline_restructuring,
    assess_feasibility,
)
from research_engineer.feasibility.manifest_checker import ManifestCheckResult, OperationMatch
from research_engineer.feasibility.test_coverage import CoverageAssessment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_classification(
    innovation_type: InnovationType,
    confidence: float = 0.85,
) -> ClassificationResult:
    """Build a ClassificationResult for testing."""
    return ClassificationResult(
        innovation_type=innovation_type,
        confidence=confidence,
        rationale=f"Test classification: {innovation_type.value}",
        topology_signal="test topology signal",
    )


def _make_manifest_check(
    coverage: float,
    matched_count: int = 2,
    unmatched_count: int = 0,
) -> ManifestCheckResult:
    """Build a ManifestCheckResult for testing."""
    matched = [
        OperationMatch(
            operation=f"op_{i}",
            repo_name="test-repo",
            function_name=f"func_{i}",
            module_path="test.mod",
            match_type="exact_function",
        )
        for i in range(matched_count)
    ]
    unmatched = [f"unknown_op_{i}" for i in range(unmatched_count)]
    return ManifestCheckResult(
        matched_operations=matched,
        unmatched_operations=unmatched,
        manifests_loaded=["test-repo"],
        coverage_ratio=coverage,
    )


def _make_blast_radius(risk: RiskLevel = RiskLevel.low) -> BlastRadiusReport:
    """Build a BlastRadiusReport for testing."""
    return BlastRadiusReport(
        target_nodes=["node_a"],
        affected_functions=["func_1"],
        risk_level=risk,
    )


def _make_coverage(ratio: float = 0.8) -> CoverageAssessment:
    """Build a CoverageAssessment for testing."""
    covered = ["f1", "f2"] if ratio > 0 else []
    uncovered = ["f3"] if ratio < 1.0 else []
    return CoverageAssessment(
        covered_functions=covered,
        uncovered_functions=uncovered,
        coverage_ratio=ratio,
        additional_tests_needed=len(uncovered),
    )


def _write_synthetic_manifest(tmp_path):
    """Write a synthetic manifest YAML and return the directory."""
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir(exist_ok=True)
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
                "docstring": "Dense retrieval using embeddings",
            },
            {
                "name": "reciprocal_rank_fusion",
                "module_path": "test.fusion",
                "source_file": "src/test/fusion.py",
                "docstring": "Reciprocal rank fusion for hybrid retrieval",
            },
        ],
        "classes": [
            {
                "name": "SparseRetriever",
                "module_path": "test.retriever",
                "source_file": "src/test/retriever.py",
                "methods": [
                    {
                        "name": "search",
                        "module_path": "test.retriever",
                        "source_file": "src/test/retriever.py",
                    },
                ],
            },
        ],
        "module_tree": {
            "test.retriever": ["bm25_search", "dense_search", "SparseRetriever"],
            "test.fusion": ["reciprocal_rank_fusion"],
        },
    }
    manifest_path = manifests_dir / "test-repo.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)
    return manifests_dir


# ---------------------------------------------------------------------------
# Tests: FeasibilityStatus enum
# ---------------------------------------------------------------------------


class TestFeasibilityStatus:
    """Tests for FeasibilityStatus enum."""

    def test_has_four_values(self):
        """FeasibilityStatus has 4 members."""
        assert len(FeasibilityStatus) == 4

    def test_values_are_strings(self):
        """FeasibilityStatus values are strings."""
        for status in FeasibilityStatus:
            assert isinstance(status.value, str)


# ---------------------------------------------------------------------------
# Tests: FeasibilityResult model
# ---------------------------------------------------------------------------


class TestFeasibilityResult:
    """Tests for FeasibilityResult model."""

    def test_constructs_minimal(self):
        """FeasibilityResult constructs with minimal fields (parameter_tuning: no blast_radius)."""
        result = FeasibilityResult(
            status=FeasibilityStatus.FEASIBLE,
            innovation_type=InnovationType.parameter_tuning,
            manifest_check=_make_manifest_check(0.8),
            rationale="Feasible for parameter tuning",
        )
        assert result.status == FeasibilityStatus.FEASIBLE
        assert result.blast_radius is None
        assert result.coverage is None

    def test_constructs_full(self):
        """FeasibilityResult constructs with all sub-analyses populated."""
        result = FeasibilityResult(
            status=FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
            innovation_type=InnovationType.pipeline_restructuring,
            manifest_check=_make_manifest_check(0.6),
            blast_radius=_make_blast_radius(),
            coverage=_make_coverage(0.5),
            rationale="Pipeline restructuring feasible with adaptation",
            adaptation_notes=["Low test coverage"],
        )
        assert result.blast_radius is not None
        assert result.coverage is not None
        assert len(result.adaptation_notes) == 1

    def test_rejects_empty_rationale(self):
        """FeasibilityResult rejects empty rationale."""
        import pytest

        with pytest.raises(Exception):
            FeasibilityResult(
                status=FeasibilityStatus.FEASIBLE,
                innovation_type=InnovationType.parameter_tuning,
                manifest_check=_make_manifest_check(0.8),
                rationale="   ",
            )

    def test_json_roundtrip(self):
        """FeasibilityResult round-trips through JSON."""
        original = FeasibilityResult(
            status=FeasibilityStatus.ESCALATE,
            innovation_type=InnovationType.architectural_innovation,
            manifest_check=_make_manifest_check(0.3, matched_count=1, unmatched_count=2),
            blast_radius=_make_blast_radius(RiskLevel.high),
            coverage=_make_coverage(0.4),
            rationale="Architectural innovation escalated",
            escalation_trigger=EscalationTrigger.novel_primitive,
        )
        json_str = original.model_dump_json()
        restored = FeasibilityResult.model_validate_json(json_str)
        assert restored.status == original.status
        assert restored.innovation_type == original.innovation_type
        assert restored.escalation_trigger == original.escalation_trigger


# ---------------------------------------------------------------------------
# Tests: gate logic per innovation type
# ---------------------------------------------------------------------------


class TestGateParameterTuning:
    """Tests for _gate_parameter_tuning logic."""

    def test_feasible_high_coverage(self):
        """FEASIBLE when coverage >= 0.5."""
        status, _, trigger, _ = _gate_parameter_tuning(
            _make_manifest_check(0.8),
            _make_classification(InnovationType.parameter_tuning),
        )
        assert status == FeasibilityStatus.FEASIBLE
        assert trigger is None

    def test_not_feasible_zero_coverage(self):
        """NOT_FEASIBLE when coverage == 0.0."""
        status, _, _, _ = _gate_parameter_tuning(
            _make_manifest_check(0.0, matched_count=0, unmatched_count=3),
            _make_classification(InnovationType.parameter_tuning),
        )
        assert status == FeasibilityStatus.NOT_FEASIBLE

    def test_escalate_low_confidence(self):
        """ESCALATE when confidence < 0.6."""
        status, _, trigger, _ = _gate_parameter_tuning(
            _make_manifest_check(0.8),
            _make_classification(InnovationType.parameter_tuning, confidence=0.3),
        )
        assert status == FeasibilityStatus.ESCALATE
        assert trigger == EscalationTrigger.confidence_below_threshold

    def test_adaptation_partial_coverage(self):
        """FEASIBLE_WITH_ADAPTATION when coverage > 0 but < 0.5."""
        status, _, _, notes = _gate_parameter_tuning(
            _make_manifest_check(0.3, matched_count=1, unmatched_count=2),
            _make_classification(InnovationType.parameter_tuning),
        )
        assert status == FeasibilityStatus.FEASIBLE_WITH_ADAPTATION
        assert len(notes) > 0


class TestGateModularSwap:
    """Tests for _gate_modular_swap logic."""

    def test_feasible_good_coverage_low_risk(self):
        """FEASIBLE when coverage >= 0.5 and risk is low."""
        status, _, _, _ = _gate_modular_swap(
            _make_manifest_check(0.8),
            _make_blast_radius(RiskLevel.low),
            _make_classification(InnovationType.modular_swap),
        )
        assert status == FeasibilityStatus.FEASIBLE

    def test_escalate_critical_risk(self):
        """ESCALATE when risk is critical."""
        status, _, trigger, _ = _gate_modular_swap(
            _make_manifest_check(0.8),
            _make_blast_radius(RiskLevel.critical),
            _make_classification(InnovationType.modular_swap),
        )
        assert status == FeasibilityStatus.ESCALATE
        assert trigger == EscalationTrigger.novel_primitive


class TestGateArchitecturalInnovation:
    """Tests for _gate_architectural_innovation logic."""

    def test_escalate_high_unmatched(self):
        """ESCALATE when >50% of operations are unmatched."""
        status, _, trigger, _ = _gate_architectural_innovation(
            _make_manifest_check(0.3, matched_count=1, unmatched_count=3),
            _make_blast_radius(RiskLevel.low),
            _make_coverage(0.8),
            _make_classification(InnovationType.architectural_innovation),
        )
        assert status == FeasibilityStatus.ESCALATE
        assert trigger == EscalationTrigger.novel_primitive

    def test_not_feasible_very_high_unmatched(self):
        """NOT_FEASIBLE when >80% of operations are unmatched."""
        status, _, _, _ = _gate_architectural_innovation(
            _make_manifest_check(0.1, matched_count=1, unmatched_count=9),
            _make_blast_radius(RiskLevel.low),
            _make_coverage(0.8),
            _make_classification(InnovationType.architectural_innovation),
        )
        assert status == FeasibilityStatus.NOT_FEASIBLE


# ---------------------------------------------------------------------------
# Tests: assess_feasibility end-to-end
# ---------------------------------------------------------------------------


class TestAssessFeasibility:
    """Tests for assess_feasibility end-to-end."""

    def test_parameter_tuning_feasible(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        """Parameter tuning against synthetic manifest returns FEASIBLE or FEASIBLE_WITH_ADAPTATION."""
        manifests_dir = _write_synthetic_manifest(tmp_path)
        classification = _make_classification(InnovationType.parameter_tuning)
        result = assess_feasibility(
            sample_parameter_tuning_summary, classification, manifests_dir
        )
        assert result.status in (
            FeasibilityStatus.FEASIBLE,
            FeasibilityStatus.FEASIBLE_WITH_ADAPTATION,
        )
        assert result.innovation_type == InnovationType.parameter_tuning
        assert result.blast_radius is None  # parameter_tuning skips blast radius

    def test_modular_swap_has_blast_radius(
        self, sample_modular_swap_summary, tmp_path
    ):
        """Modular swap returns a result with blast_radius populated."""
        manifests_dir = _write_synthetic_manifest(tmp_path)
        classification = _make_classification(InnovationType.modular_swap)
        result = assess_feasibility(
            sample_modular_swap_summary, classification, manifests_dir
        )
        assert result.blast_radius is not None
        assert isinstance(result.blast_radius, BlastRadiusReport)

    def test_pipeline_restructuring_has_coverage(
        self, sample_pipeline_restructuring_summary, tmp_path
    ):
        """Pipeline restructuring returns a result with coverage populated."""
        manifests_dir = _write_synthetic_manifest(tmp_path)
        classification = _make_classification(InnovationType.pipeline_restructuring)
        result = assess_feasibility(
            sample_pipeline_restructuring_summary, classification, manifests_dir
        )
        assert result.coverage is not None
        assert isinstance(result.coverage, CoverageAssessment)

    def test_architectural_escalate_novel(
        self, sample_architectural_summary, tmp_path
    ):
        """Architectural innovation with novel primitives triggers ESCALATE or NOT_FEASIBLE."""
        manifests_dir = _write_synthetic_manifest(tmp_path)
        classification = _make_classification(InnovationType.architectural_innovation)
        result = assess_feasibility(
            sample_architectural_summary, classification, manifests_dir
        )
        # Architectural summary has many terms not in manifest, so high unmatched ratio
        assert result.status in (
            FeasibilityStatus.ESCALATE,
            FeasibilityStatus.NOT_FEASIBLE,
        )

    def test_not_feasible_empty_manifests(
        self, sample_parameter_tuning_summary, tmp_path
    ):
        """Empty manifests dir results in NOT_FEASIBLE (coverage == 0)."""
        empty_dir = tmp_path / "empty_manifests"
        empty_dir.mkdir()
        classification = _make_classification(InnovationType.parameter_tuning)
        result = assess_feasibility(
            sample_parameter_tuning_summary, classification, empty_dir
        )
        assert result.status == FeasibilityStatus.NOT_FEASIBLE

    def test_build_operations_list(self, sample_parameter_tuning_summary):
        """_build_operations_list extracts inputs + outputs + paper_terms."""
        ops = _build_operations_list(sample_parameter_tuning_summary)
        assert len(ops) > 0
        # Should include items from inputs_required
        assert "BM25 retrieval scores" in ops
        # Should include items from paper_terms
        assert "BM25" in ops
