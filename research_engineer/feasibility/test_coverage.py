"""Test coverage assessor: check test coverage for affected functions.

Given a list of affected functions from blast radius analysis, checks
whether existing tests cover the affected area using graph connectivity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from research_engineer.feasibility.dependency_graph import DependencyGraph


class CoverageAssessment(BaseModel):
    """Result of test coverage assessment."""

    model_config = ConfigDict()

    covered_functions: list[str] = []
    uncovered_functions: list[str] = []
    coverage_ratio: float = 1.0
    additional_tests_needed: int = 0

    @field_validator("coverage_ratio")
    @classmethod
    def clamp_coverage(cls, v: float) -> float:
        return max(0.0, min(v, 1.0))


def _is_test_node(node_id: str, graph: DependencyGraph) -> bool:
    """Check if a node represents a test."""
    node = graph.nodes.get(node_id)
    if node and "test" in node.module_path.lower():
        return True
    return "test" in node_id.lower()


def assess_test_coverage(
    affected_functions: list[str],
    graph: DependencyGraph,
) -> CoverageAssessment:
    """Assess test coverage for affected functions.

    For each affected function, checks if any test node exists in its
    upstream or downstream within the dependency graph.

    Args:
        affected_functions: List of function node IDs to assess.
        graph: The codebase dependency graph.

    Returns:
        CoverageAssessment with covered/uncovered functions and ratio.
    """
    if not affected_functions:
        return CoverageAssessment(
            covered_functions=[],
            uncovered_functions=[],
            coverage_ratio=1.0,
            additional_tests_needed=0,
        )

    covered: list[str] = []
    uncovered: list[str] = []

    for func_id in affected_functions:
        # Check upstream and downstream for test nodes
        neighbors = graph.upstream(func_id) | graph.downstream(func_id)
        has_test = any(_is_test_node(n, graph) for n in neighbors)

        if has_test:
            covered.append(func_id)
        else:
            uncovered.append(func_id)

    total = len(covered) + len(uncovered)
    ratio = len(covered) / max(total, 1)

    return CoverageAssessment(
        covered_functions=covered,
        uncovered_functions=uncovered,
        coverage_ratio=ratio,
        additional_tests_needed=len(uncovered),
    )
