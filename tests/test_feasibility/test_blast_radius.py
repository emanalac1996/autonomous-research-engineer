"""Tests for blast radius analyzer (WU 3.3)."""

from research_engineer.feasibility.blast_radius import (
    BlastRadiusReport,
    RiskLevel,
    _classify_risk,
    compute_blast_radius,
)
from research_engineer.feasibility.dependency_graph import DependencyGraph, GraphNode


def _make_graph_with_test_and_contract() -> DependencyGraph:
    """Build a graph with function, test, and contract nodes."""
    dg = DependencyGraph()

    # Module -> function (hub)
    dg.nodes["repo::mod"] = GraphNode(
        node_id="repo::mod", node_type="module", repo_name="repo", module_path="mod"
    )
    dg.nodes["repo::mod.func_a"] = GraphNode(
        node_id="repo::mod.func_a", node_type="function", repo_name="repo", module_path="mod"
    )
    dg.nodes["repo::mod.func_b"] = GraphNode(
        node_id="repo::mod.func_b", node_type="function", repo_name="repo", module_path="mod"
    )
    dg.nodes["repo::mod.test_helper"] = GraphNode(
        node_id="repo::mod.test_helper", node_type="function", repo_name="repo", module_path="mod.tests"
    )
    dg.nodes["repo::mod.contract_check"] = GraphNode(
        node_id="repo::mod.contract_check", node_type="function", repo_name="repo", module_path="mod.contracts"
    )
    dg.nodes["repo::mod.leaf"] = GraphNode(
        node_id="repo::mod.leaf", node_type="function", repo_name="repo", module_path="mod"
    )

    for nid in dg.nodes:
        dg.graph.add_node(nid)

    # Hub -> downstream nodes
    dg.graph.add_edge("repo::mod", "repo::mod.func_a", edge_type="contains")
    dg.graph.add_edge("repo::mod", "repo::mod.func_b", edge_type="contains")
    dg.graph.add_edge("repo::mod.func_a", "repo::mod.test_helper", edge_type="contains")
    dg.graph.add_edge("repo::mod.func_a", "repo::mod.contract_check", edge_type="contains")
    # Leaf has no downstream
    dg.graph.add_edge("repo::mod", "repo::mod.leaf", edge_type="contains")

    return dg


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_has_four_values(self):
        """RiskLevel has 4 members."""
        assert len(RiskLevel) == 4


class TestBlastRadiusReport:
    """Tests for BlastRadiusReport model."""

    def test_constructs_total_affected(self):
        """total_affected is computed correctly."""
        report = BlastRadiusReport(
            target_nodes=["a"],
            affected_functions=["f1", "f2"],
            affected_tests=["t1"],
            affected_contracts=["c1"],
            risk_level=RiskLevel.medium,
        )
        assert report.total_affected == 4

    def test_json_roundtrip(self):
        """BlastRadiusReport round-trips through JSON."""
        original = BlastRadiusReport(
            target_nodes=["a"],
            affected_functions=["f1"],
            risk_level=RiskLevel.low,
        )
        json_str = original.model_dump_json()
        restored = BlastRadiusReport.model_validate_json(json_str)
        assert restored.target_nodes == original.target_nodes
        assert restored.risk_level == original.risk_level


class TestComputeBlastRadius:
    """Tests for compute_blast_radius."""

    def test_leaf_node_empty(self):
        """Leaf node with no downstream returns empty report, risk=low."""
        dg = _make_graph_with_test_and_contract()
        report = compute_blast_radius(["repo::mod.leaf"], dg)
        assert report.affected_functions == []
        assert report.affected_tests == []
        assert report.risk_level == RiskLevel.low

    def test_hub_node_non_empty(self):
        """Hub node returns non-empty affected_functions."""
        dg = _make_graph_with_test_and_contract()
        report = compute_blast_radius(["repo::mod"], dg)
        assert len(report.affected_functions) > 0

    def test_identifies_test_nodes(self):
        """Test nodes identified via 'test' in module_path."""
        dg = _make_graph_with_test_and_contract()
        report = compute_blast_radius(["repo::mod.func_a"], dg)
        assert "repo::mod.test_helper" in report.affected_tests

    def test_identifies_contract_nodes(self):
        """Contract nodes identified via 'contract' in module_path."""
        dg = _make_graph_with_test_and_contract()
        report = compute_blast_radius(["repo::mod.func_a"], dg)
        assert "repo::mod.contract_check" in report.affected_contracts


class TestClassifyRisk:
    """Tests for _classify_risk boundaries."""

    def test_boundary_values(self):
        """Risk classification at boundary values."""
        assert _classify_risk(0) == RiskLevel.low
        assert _classify_risk(2) == RiskLevel.low
        assert _classify_risk(3) == RiskLevel.medium
        assert _classify_risk(10) == RiskLevel.medium
        assert _classify_risk(11) == RiskLevel.high
        assert _classify_risk(30) == RiskLevel.high
        assert _classify_risk(31) == RiskLevel.critical
