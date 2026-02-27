"""Codebase dependency graph built from repository manifests.

Constructs a NetworkX DiGraph from manifest data where nodes are
functions/classes and edges are containment, method-of, and inferred
import relationships. Supports downstream, upstream, shortest-path,
and connected-component queries.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

try:
    import networkx as nx
except ImportError:
    raise ImportError(
        "networkx required for dependency graph: "
        "pip install autonomous-research-engineer[graph]"
    )

from research_engineer.feasibility.manifest_checker import (
    RepositoryManifest,
    load_all_manifests,
)


class GraphNode(BaseModel):
    """A node in the dependency graph."""

    model_config = ConfigDict()

    node_id: str
    node_type: str  # "function", "class", "module"
    repo_name: str
    module_path: str
    source_file: str | None = None


class GraphStats(BaseModel):
    """Summary statistics for a dependency graph."""

    model_config = ConfigDict()

    node_count: int = 0
    edge_count: int = 0
    connected_components: int = 0
    is_dag: bool = True


class DependencyGraph:
    """Wrapper around NetworkX DiGraph with manifest-based construction."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self.nodes: dict[str, GraphNode] = {}

    @classmethod
    def build_from_manifests(
        cls, manifests: list[RepositoryManifest]
    ) -> DependencyGraph:
        """Build a dependency graph from parsed manifests.

        Nodes: functions, classes, and modules.
        Edges: module→function "contains", class→method "method_of",
               module→module "imports" (sibling heuristic).
        """
        dg = cls()

        for manifest in manifests:
            repo = manifest.repo_name
            modules_seen: dict[str, str] = {}  # module_path -> node_id

            # Add function nodes with module→function edges
            for func in manifest.functions:
                func_id = f"{repo}::{func.module_path}.{func.name}"
                mod_id = f"{repo}::{func.module_path}"

                func_node = GraphNode(
                    node_id=func_id,
                    node_type="function",
                    repo_name=repo,
                    module_path=func.module_path,
                    source_file=func.source_file or None,
                )
                dg.nodes[func_id] = func_node
                dg.graph.add_node(func_id)

                # Ensure module node exists
                if mod_id not in dg.nodes:
                    dg.nodes[mod_id] = GraphNode(
                        node_id=mod_id,
                        node_type="module",
                        repo_name=repo,
                        module_path=func.module_path,
                    )
                    dg.graph.add_node(mod_id)
                modules_seen[func.module_path] = mod_id

                # Module → function "contains" edge
                dg.graph.add_edge(mod_id, func_id, edge_type="contains")

            # Add class nodes with method edges
            for cls_entry in manifest.classes:
                cls_id = f"{repo}::{cls_entry.module_path}.{cls_entry.name}"
                mod_id = f"{repo}::{cls_entry.module_path}"

                cls_node = GraphNode(
                    node_id=cls_id,
                    node_type="class",
                    repo_name=repo,
                    module_path=cls_entry.module_path,
                    source_file=cls_entry.source_file or None,
                )
                dg.nodes[cls_id] = cls_node
                dg.graph.add_node(cls_id)

                # Ensure module node
                if mod_id not in dg.nodes:
                    dg.nodes[mod_id] = GraphNode(
                        node_id=mod_id,
                        node_type="module",
                        repo_name=repo,
                        module_path=cls_entry.module_path,
                    )
                    dg.graph.add_node(mod_id)
                modules_seen[cls_entry.module_path] = mod_id

                # Module → class "contains" edge
                dg.graph.add_edge(mod_id, cls_id, edge_type="contains")

                # Class → method "method_of" edges
                for method in cls_entry.methods:
                    method_id = f"{repo}::{cls_entry.module_path}.{cls_entry.name}.{method.name}"
                    method_node = GraphNode(
                        node_id=method_id,
                        node_type="function",
                        repo_name=repo,
                        module_path=cls_entry.module_path,
                        source_file=method.source_file or None,
                    )
                    dg.nodes[method_id] = method_node
                    dg.graph.add_node(method_id)
                    dg.graph.add_edge(cls_id, method_id, edge_type="method_of")

            # Sibling module "imports" edges (same parent package)
            mod_paths = list(modules_seen.keys())
            for i, mp1 in enumerate(mod_paths):
                parent1 = mp1.rsplit(".", 1)[0] if "." in mp1 else ""
                for mp2 in mod_paths[i + 1 :]:
                    parent2 = mp2.rsplit(".", 1)[0] if "." in mp2 else ""
                    if parent1 and parent1 == parent2:
                        id1 = modules_seen[mp1]
                        id2 = modules_seen[mp2]
                        dg.graph.add_edge(id1, id2, edge_type="imports")
                        dg.graph.add_edge(id2, id1, edge_type="imports")

        return dg

    def downstream(self, node_id: str) -> set[str]:
        """All reachable nodes from node_id following outgoing edges."""
        if node_id not in self.graph:
            return set()
        return nx.descendants(self.graph, node_id)

    def upstream(self, node_id: str) -> set[str]:
        """All nodes that can reach node_id following incoming edges."""
        if node_id not in self.graph:
            return set()
        return nx.ancestors(self.graph, node_id)

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        """Shortest path between two nodes, or None if no path."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return None

    def connected_component(self, node_id: str) -> set[str]:
        """All nodes in the same weakly connected component."""
        if node_id not in self.graph:
            return set()
        undirected = self.graph.to_undirected()
        return nx.node_connected_component(undirected, node_id)

    def stats(self) -> GraphStats:
        """Compute graph statistics."""
        return GraphStats(
            node_count=self.graph.number_of_nodes(),
            edge_count=self.graph.number_of_edges(),
            connected_components=nx.number_weakly_connected_components(self.graph),
            is_dag=nx.is_directed_acyclic_graph(self.graph),
        )


def build_dependency_graph(manifests_dir: Path) -> DependencyGraph:
    """Build a dependency graph from all manifests in a directory.

    Args:
        manifests_dir: Path to directory containing manifest YAML files.

    Returns:
        DependencyGraph with nodes and edges from all manifests.
    """
    manifests = load_all_manifests(manifests_dir)
    return DependencyGraph.build_from_manifests(manifests)
