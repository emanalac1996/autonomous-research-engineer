"""Tests for vocabulary mapping (WU 1.5)."""

import pytest

from research_engineer.comprehension.vocabulary import (
    ManifestMatch,
    PatternMatch,
    VocabularyMapping,
    build_vocabulary_mapping,
    match_terms_to_manifests,
    match_terms_to_patterns,
)


class TestVocabularyMappingModel:
    """Tests for VocabularyMapping model validation."""

    def test_model_valid(self):
        """VocabularyMapping constructs with all fields."""
        vm = VocabularyMapping(
            paper_terms=["BM25", "sparse retrieval"],
            pattern_matches=[
                PatternMatch(
                    paper_term="sparse retrieval",
                    pattern_id="retrieval-relevance-001",
                    score=0.5,
                    formal_class="multi_objective_optimization",
                    matched_phrases=["sparse retrieval"],
                ),
            ],
            manifest_matches=[
                ManifestMatch(
                    paper_term="BM25",
                    repo_name="multimodal-rag-core",
                    function_name="bm25_search",
                    module_path="multimodal_rag.retriever",
                ),
            ],
            unmapped_terms=[],
        )
        assert len(vm.pattern_matches) == 1
        assert len(vm.manifest_matches) == 1

    def test_json_roundtrip(self):
        """VocabularyMapping round-trips through JSON."""
        original = VocabularyMapping(
            paper_terms=["test_term"],
            pattern_matches=[],
            manifest_matches=[],
            unmapped_terms=["test_term"],
        )
        json_str = original.model_dump_json()
        restored = VocabularyMapping.model_validate_json(json_str)
        assert restored == original


class TestMatchTermsToPatterns:
    """Tests for matching terms to Pattern Library."""

    def test_sparse_retrieval_matches(self, clearinghouse_root):
        """'sparse retrieval' produces at least one PatternMatch."""
        if not clearinghouse_root.exists():
            pytest.skip("clearinghouse not available")
        matches = match_terms_to_patterns(
            ["sparse retrieval"], clearinghouse_root
        )
        assert len(matches) >= 1
        assert all(m.score > 0.0 for m in matches)

    def test_retrieval_ranking_matches(self, clearinghouse_root):
        """'retrieval ranking' produces at least one PatternMatch."""
        if not clearinghouse_root.exists():
            pytest.skip("clearinghouse not available")
        matches = match_terms_to_patterns(
            ["retrieval ranking"], clearinghouse_root
        )
        assert len(matches) >= 1


class TestMatchTermsToManifests:
    """Tests for matching terms to manifest entries."""

    def test_bm25_matches_manifest(self, clearinghouse_manifests):
        """'bm25' produces at least one ManifestMatch from manifests."""
        if not clearinghouse_manifests.exists():
            pytest.skip("manifests not available")
        matches = match_terms_to_manifests(["bm25"], clearinghouse_manifests)
        assert len(matches) >= 1
        assert all(isinstance(m, ManifestMatch) for m in matches)

    def test_fabricated_term_unmatched(self, clearinghouse_manifests):
        """A fabricated term produces no manifest matches."""
        if not clearinghouse_manifests.exists():
            pytest.skip("manifests not available")
        matches = match_terms_to_manifests(
            ["quantum_entanglement_retrieval"], clearinghouse_manifests
        )
        assert len(matches) == 0


class TestBuildVocabularyMapping:
    """Tests for the full build_vocabulary_mapping pipeline."""

    def test_modular_swap_terms(self, clearinghouse_root):
        """Full mapping from modular swap fixture terms produces non-empty results."""
        if not clearinghouse_root.exists():
            pytest.skip("clearinghouse not available")
        terms = ["sparse retrieval", "BM25", "SPLADE", "inverted index"]
        result = build_vocabulary_mapping(terms, clearinghouse_root)
        assert isinstance(result, VocabularyMapping)
        assert len(result.pattern_matches) + len(result.manifest_matches) > 0

    def test_unmapped_terms_identified(self, clearinghouse_root):
        """A fabricated term ends up in unmapped_terms."""
        if not clearinghouse_root.exists():
            pytest.skip("clearinghouse not available")
        terms = ["quantum_entanglement_retrieval"]
        result = build_vocabulary_mapping(terms, clearinghouse_root)
        assert "quantum_entanglement_retrieval" in result.unmapped_terms
