"""Tests for manifest checker (WU 3.1)."""

import pytest
import yaml

from research_engineer.feasibility.manifest_checker import (
    ManifestCheckResult,
    ManifestFunction,
    OperationMatch,
    RepositoryManifest,
    check_operations,
    load_all_manifests,
    load_manifest,
)


class TestRepositoryManifest:
    """Tests for the RepositoryManifest model."""

    def test_constructs_minimal(self):
        """RepositoryManifest constructs with repo_name only."""
        m = RepositoryManifest(repo_name="test-repo")
        assert m.repo_name == "test-repo"
        assert m.functions == []
        assert m.classes == []

    def test_json_roundtrip(self):
        """RepositoryManifest round-trips through JSON."""
        original = RepositoryManifest(
            repo_name="test-repo",
            version="1.0.0",
            functions=[ManifestFunction(name="foo", module_path="test.mod")],
        )
        json_str = original.model_dump_json()
        restored = RepositoryManifest.model_validate_json(json_str)
        assert restored == original


class TestManifestCheckResult:
    """Tests for ManifestCheckResult model."""

    def test_constructs_with_matched_unmatched(self):
        """ManifestCheckResult constructs with both lists."""
        result = ManifestCheckResult(
            matched_operations=[
                OperationMatch(
                    operation="BM25",
                    repo_name="test-repo",
                    function_name="bm25_search",
                    match_type="exact_function",
                )
            ],
            unmatched_operations=["quantum_fusion"],
            manifests_loaded=["test-repo"],
            coverage_ratio=0.5,
        )
        assert len(result.matched_operations) == 1
        assert len(result.unmatched_operations) == 1

    def test_coverage_ratio_computed(self):
        """Coverage ratio is correctly set (2 matched, 1 unmatched = 0.667)."""
        result = ManifestCheckResult(
            matched_operations=[
                OperationMatch(operation="a", repo_name="r", match_type="exact_function"),
                OperationMatch(operation="b", repo_name="r", match_type="exact_function"),
            ],
            unmatched_operations=["c"],
            coverage_ratio=2.0 / 3.0,
        )
        assert abs(result.coverage_ratio - 0.667) < 0.01


class TestLoadManifest:
    """Tests for manifest loading."""

    def test_loads_synthetic_yaml(self, tmp_path):
        """load_manifest parses a synthetic YAML manifest."""
        manifest_data = {
            "repo_name": "test-repo",
            "version": "0.1.0",
            "functions": [
                {
                    "name": "bm25_search",
                    "module_path": "test.retriever",
                    "parameters": [{"name": "query", "type_annotation": "str"}],
                    "return_type": "list",
                    "docstring": "BM25 sparse retrieval search.",
                    "source_file": "src/test/retriever.py",
                    "line_number": 10,
                }
            ],
            "classes": [
                {
                    "name": "SparseRetriever",
                    "module_path": "test.retriever",
                    "bases": ["BaseRetriever"],
                    "docstring": "Sparse retrieval component.",
                    "source_file": "src/test/retriever.py",
                    "line_number": 50,
                }
            ],
            "module_tree": {"test.retriever": ["bm25_search", "SparseRetriever"]},
        }
        yaml_path = tmp_path / "test_repo.yaml"
        yaml_path.write_text(yaml.dump(manifest_data))

        result = load_manifest(yaml_path)
        assert result.repo_name == "test-repo"
        assert len(result.functions) == 1
        assert len(result.classes) == 1
        assert result.functions[0].name == "bm25_search"

    def test_load_all_missing_dir(self, tmp_path):
        """load_all_manifests returns empty list for missing dir."""
        result = load_all_manifests(tmp_path / "nonexistent")
        assert result == []

    def test_load_all_real_manifests(self, clearinghouse_manifests):
        """load_all_manifests loads real clearinghouse manifests."""
        if not clearinghouse_manifests.exists():
            pytest.skip("clearinghouse not available")
        result = load_all_manifests(clearinghouse_manifests)
        assert len(result) >= 3
        assert all(m.repo_name for m in result)


class TestCheckOperations:
    """Tests for operation checking."""

    def test_matches_bm25(self, clearinghouse_manifests):
        """'bm25' matches against real manifests."""
        if not clearinghouse_manifests.exists():
            pytest.skip("clearinghouse not available")
        manifests = load_all_manifests(clearinghouse_manifests)
        result = check_operations(["bm25"], manifests)
        assert len(result.matched_operations) >= 1

    def test_fabricated_unmatched(self, clearinghouse_manifests):
        """Fabricated term ends up in unmatched_operations."""
        if not clearinghouse_manifests.exists():
            pytest.skip("clearinghouse not available")
        manifests = load_all_manifests(clearinghouse_manifests)
        result = check_operations(["quantum_entanglement_retrieval"], manifests)
        assert "quantum_entanglement_retrieval" in result.unmatched_operations

    def test_empty_operations(self):
        """Empty operations returns empty matched and 0.0 ratio."""
        result = check_operations([], [])
        assert result.matched_operations == []
        assert result.coverage_ratio == 0.0
