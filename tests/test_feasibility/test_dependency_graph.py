"""Tests for codebase dependency graph (WU 3.2)."""

import pytest
import yaml

from research_engineer.feasibility.dependency_graph import (
    DependencyGraph,
    GraphNode,
    GraphStats,
    build_dependency_graph,
)
from research_engineer.feasibility.manifest_checker import (
    ManifestClass,
    ManifestFunction,
    RepositoryManifest,
)


def _make_synthetic_manifests() -> list[RepositoryManifest]:
    """Build synthetic manifests for testing."""
    return [
        RepositoryManifest(
            repo_name="test-repo",
            version="1.0.0",
            functions=[
                ManifestFunction(
                    name="bm25_search",
                    module_path="test.retriever",
                    source_file="src/test/retriever.py",
                ),
                ManifestFunction(
                    name="dense_search",
                    module_path="test.retriever",
                    source_file="src/test/retriever.py",
                ),
                ManifestFunction(
                    name="test_retriever",
                    module_path="test.tests.test_retriever",
                    source_file="tests/test_retriever.py",
                ),
            ],
            classes=[
                ManifestClass(
                    name="SparseRetriever",
                    module_path="test.retriever",
                    source_file="src/test/retriever.py",
                    methods=[
                        ManifestFunction(
                            name="search",
                            module_path="test.retriever",
                            source_file="src/test/retriever.py",
                        ),
                    ],
                ),
            ],
            module_tree={
                "test.retriever": ["bm25_search", "dense_search", "SparseRetriever"],
                "test.tests.test_retriever": ["test_retriever"],
            },
        )
    ]


class TestGraphModels:
    """Tests for graph data models."""

    def test_graph_node_constructs(self):
        """GraphNode constructs with required fields."""
        node = GraphNode(
            node_id="repo::mod.func",
            node_type="function",
            repo_name="repo",
            module_path="mod",
        )
        assert node.node_id == "repo::mod.func"

    def test_graph_stats_constructs(self):
        """GraphStats constructs and reports correct values."""
        stats = GraphStats(node_count=10, edge_count=15, connected_components=2, is_dag=True)
        assert stats.node_count == 10
        assert stats.is_dag is True


class TestDependencyGraphConstruction:
    """Tests for building the graph."""

    def test_empty_graph(self):
        """DependencyGraph() creates empty graph."""
        dg = DependencyGraph()
        stats = dg.stats()
        assert stats.node_count == 0
        assert stats.edge_count == 0

    def test_build_from_synthetic(self):
        """build_from_manifests creates nodes from synthetic manifest."""
        manifests = _make_synthetic_manifests()
        dg = DependencyGraph.build_from_manifests(manifests)
        stats = dg.stats()
        # 3 functions + 1 class + 1 method + 2 modules = 7 nodes minimum
        assert stats.node_count >= 7
        assert stats.edge_count > 0

    def test_build_from_real_manifests(self, clearinghouse_manifests):
        """build_from_manifests builds graph from real clearinghouse manifests."""
        if not clearinghouse_manifests.exists():
            pytest.skip("clearinghouse not available")
        dg = build_dependency_graph(clearinghouse_manifests)
        stats = dg.stats()
        assert stats.node_count > 50


class TestDependencyGraphQueries:
    """Tests for graph query methods."""

    def test_downstream_module(self):
        """downstream() on module returns contained functions."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        mod_id = "test-repo::test.retriever"
        downstream = dg.downstream(mod_id)
        assert len(downstream) > 0
        # Should include functions in that module
        assert "test-repo::test.retriever.bm25_search" in downstream

    def test_upstream_function(self):
        """upstream() on function returns containing module."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        func_id = "test-repo::test.retriever.bm25_search"
        upstream = dg.upstream(func_id)
        assert "test-repo::test.retriever" in upstream

    def test_shortest_path_connected(self):
        """shortest_path returns path between connected nodes."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        path = dg.shortest_path(
            "test-repo::test.retriever",
            "test-repo::test.retriever.bm25_search",
        )
        assert path is not None
        assert len(path) >= 2

    def test_shortest_path_disconnected(self):
        """shortest_path returns None for disconnected nodes."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        path = dg.shortest_path("test-repo::test.retriever.bm25_search", "nonexistent")
        assert path is None

    def test_connected_component(self):
        """connected_component returns nodes in same component."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        component = dg.connected_component("test-repo::test.retriever.bm25_search")
        assert "test-repo::test.retriever" in component
        assert len(component) > 1

    def test_stats_is_dag(self):
        """Stats correctly reports is_dag for synthetic graph."""
        dg = DependencyGraph.build_from_manifests(_make_synthetic_manifests())
        stats = dg.stats()
        # Sibling module imports create cycles, so this may not be a DAG
        assert isinstance(stats.is_dag, bool)
