"""Blast radius analyzer: compute downstream impact of proposed changes.

Given target nodes (functions/classes to modify) and a dependency graph,
computes which downstream functions, tests, and contracts are affected.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from research_engineer.feasibility.dependency_graph import DependencyGraph


class RiskLevel(str, Enum):
    """Risk level based on blast radius size."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class BlastRadiusReport(BaseModel):
    """Result of blast radius analysis."""

    model_config = ConfigDict()

    target_nodes: list[str] = Field(default_factory=list)
    affected_functions: list[str] = Field(default_factory=list)
    affected_tests: list[str] = Field(default_factory=list)
    affected_contracts: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.low

    @computed_field
    @property
    def total_affected(self) -> int:
        return (
            len(self.affected_functions)
            + len(self.affected_tests)
            + len(self.affected_contracts)
        )


def _classify_risk(total_affected: int) -> RiskLevel:
    """Classify risk level from total affected count."""
    if total_affected <= 2:
        return RiskLevel.low
    if total_affected <= 10:
        return RiskLevel.medium
    if total_affected <= 30:
        return RiskLevel.high
    return RiskLevel.critical


def _is_test_node(node_id: str, graph: DependencyGraph) -> bool:
    """Check if a node represents a test."""
    node = graph.nodes.get(node_id)
    if node and "test" in node.module_path.lower():
        return True
    return "test" in node_id.lower()


def _is_contract_node(node_id: str, graph: DependencyGraph) -> bool:
    """Check if a node represents a contract."""
    node = graph.nodes.get(node_id)
    if node and "contract" in node.module_path.lower():
        return True
    return "contract" in node_id.lower()


def compute_blast_radius(
    target_nodes: list[str],
    graph: DependencyGraph,
) -> BlastRadiusReport:
    """Compute the blast radius for a set of target nodes.

    Args:
        target_nodes: Node IDs of functions/classes to modify.
        graph: The codebase dependency graph.

    Returns:
        BlastRadiusReport with affected functions, tests, contracts, and risk.
    """
    all_affected: set[str] = set()
    valid_targets: list[str] = []

    for node_id in target_nodes:
        if node_id in graph.graph:
            valid_targets.append(node_id)
            all_affected.update(graph.downstream(node_id))

    # Partition affected nodes
    affected_functions: list[str] = []
    affected_tests: list[str] = []
    affected_contracts: list[str] = []

    for node_id in sorted(all_affected):
        if _is_test_node(node_id, graph):
            affected_tests.append(node_id)
        elif _is_contract_node(node_id, graph):
            affected_contracts.append(node_id)
        else:
            affected_functions.append(node_id)

    total = len(affected_functions) + len(affected_tests) + len(affected_contracts)
    risk = _classify_risk(total)

    return BlastRadiusReport(
        target_nodes=valid_targets,
        affected_functions=affected_functions,
        affected_tests=affected_tests,
        affected_contracts=affected_contracts,
        risk_level=risk,
    )
