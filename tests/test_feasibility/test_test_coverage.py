"""Tests for test coverage assessor (WU 3.4)."""

from research_engineer.feasibility.dependency_graph import DependencyGraph, GraphNode
from research_engineer.feasibility.test_coverage import (
    CoverageAssessment,
    assess_test_coverage,
)


def _make_graph_with_tests() -> DependencyGraph:
    """Build a graph where func_a has test neighbors, func_b does not."""
    dg = DependencyGraph()

    dg.nodes["repo::mod.func_a"] = GraphNode(
        node_id="repo::mod.func_a", node_type="function", repo_name="repo", module_path="mod"
    )
    dg.nodes["repo::mod.func_b"] = GraphNode(
        node_id="repo::mod.func_b", node_type="function", repo_name="repo", module_path="mod"
    )
    dg.nodes["repo::tests.test_a"] = GraphNode(
        node_id="repo::tests.test_a", node_type="function", repo_name="repo", module_path="tests"
    )

    for nid in dg.nodes:
        dg.graph.add_node(nid)

    # func_a -> test_a (test depends on func_a)
    dg.graph.add_edge("repo::mod.func_a", "repo::tests.test_a", edge_type="contains")
    # func_b has no test neighbors

    return dg


class TestCoverageAssessment:
    """Tests for CoverageAssessment model."""

    def test_constructs_all_fields(self):
        """CoverageAssessment constructs with all fields."""
        ca = CoverageAssessment(
            covered_functions=["a", "b"],
            uncovered_functions=["c"],
            coverage_ratio=0.667,
            additional_tests_needed=1,
        )
        assert len(ca.covered_functions) == 2
        assert ca.additional_tests_needed == 1

    def test_json_roundtrip(self):
        """CoverageAssessment round-trips through JSON."""
        original = CoverageAssessment(
            covered_functions=["a"],
            uncovered_functions=["b"],
            coverage_ratio=0.5,
            additional_tests_needed=1,
        )
        json_str = original.model_dump_json()
        restored = CoverageAssessment.model_validate_json(json_str)
        assert restored == original

    def test_coverage_ratio_correct(self):
        """Coverage ratio is correctly computed."""
        ca = CoverageAssessment(
            covered_functions=["a", "b"],
            uncovered_functions=["c"],
            coverage_ratio=2.0 / 3.0,
            additional_tests_needed=1,
        )
        assert abs(ca.coverage_ratio - 0.667) < 0.01


class TestAssessTestCoverage:
    """Tests for assess_test_coverage function."""

    def test_covered_functions(self):
        """Functions with test neighbors are covered."""
        dg = _make_graph_with_tests()
        result = assess_test_coverage(["repo::mod.func_a"], dg)
        assert "repo::mod.func_a" in result.covered_functions
        assert result.coverage_ratio == 1.0

    def test_uncovered_functions(self):
        """Functions without test neighbors are uncovered."""
        dg = _make_graph_with_tests()
        result = assess_test_coverage(["repo::mod.func_b"], dg)
        assert "repo::mod.func_b" in result.uncovered_functions
        assert result.coverage_ratio == 0.0

    def test_empty_list(self):
        """Empty affected list returns ratio 1.0, additional=0."""
        dg = _make_graph_with_tests()
        result = assess_test_coverage([], dg)
        assert result.coverage_ratio == 1.0
        assert result.additional_tests_needed == 0

    def test_additional_tests_equals_uncovered(self):
        """additional_tests_needed equals length of uncovered."""
        dg = _make_graph_with_tests()
        result = assess_test_coverage(
            ["repo::mod.func_a", "repo::mod.func_b"], dg
        )
        assert result.additional_tests_needed == len(result.uncovered_functions)
