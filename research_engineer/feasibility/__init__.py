"""Stage 3: Feasibility gate — manifest checking, dependency graph, blast radius."""

from research_engineer.feasibility.blast_radius import (
    BlastRadiusReport,
    RiskLevel,
    compute_blast_radius,
)
from research_engineer.feasibility.dependency_graph import (
    DependencyGraph,
    GraphNode,
    GraphStats,
    build_dependency_graph,
)
from research_engineer.feasibility.gate import (
    FeasibilityResult,
    FeasibilityStatus,
    assess_feasibility,
)
from research_engineer.feasibility.manifest_checker import (
    ManifestCheckResult,
    RepositoryManifest,
    check_operations,
    load_all_manifests,
    load_manifest,
)
from research_engineer.feasibility.test_coverage import (
    CoverageAssessment,
    assess_test_coverage,
)

__all__ = [
    "BlastRadiusReport",
    "CoverageAssessment",
    "DependencyGraph",
    "FeasibilityResult",
    "FeasibilityStatus",
    "GraphNode",
    "GraphStats",
    "ManifestCheckResult",
    "RepositoryManifest",
    "RiskLevel",
    "assess_feasibility",
    "assess_test_coverage",
    "build_dependency_graph",
    "check_operations",
    "compute_blast_radius",
    "load_all_manifests",
    "load_manifest",
]
