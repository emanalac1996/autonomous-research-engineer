"""End-to-end integration tests (WU 6.4).

Tests the full pipeline from SourceDocument through classification,
feasibility, and batch evaluation using real clearinghouse manifests.
"""

from research_engineer.integration.adapter import adapt_source_document
from research_engineer.integration.batch_pipeline import evaluate_batch, evaluate_single_paper
from research_engineer.integration.manifest_freshness import check_all_manifests_freshness


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    def test_arxiv_document_to_classification(
        self, sample_source_document_arxiv, clearinghouse_manifests, tmp_path,
    ):
        """arXiv SourceDocument runs through full pipeline to classification."""
        store = tmp_path / "art_store"
        store.mkdir()

        result = evaluate_single_paper(
            sample_source_document_arxiv,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert result.error is None
        assert result.innovation_type is not None
        assert result.feasibility_status is not None
        assert result.document_id == "arxiv:2401.12345"

    def test_patent_document_to_classification(
        self, sample_source_document_patent, clearinghouse_manifests, tmp_path,
    ):
        """USPTO SourceDocument produces a valid classification."""
        store = tmp_path / "art_store"
        store.mkdir()

        # Adapt + classify
        adaptation = adapt_source_document(sample_source_document_patent)
        summary = adaptation.summary

        assert summary.title == "Optimal RRF Weight Selection for Hybrid Retrieval"
        assert summary.transformation_proposed

        from research_engineer.comprehension.topology import analyze_topology
        from agent_factors.artifacts import ArtifactRegistry
        from research_engineer.classifier.heuristics import classify
        from research_engineer.classifier.seed_artifact import register_seed_artifact

        topology = analyze_topology(summary)
        registry = ArtifactRegistry(store_dir=store)
        register_seed_artifact(registry)
        classification = classify(summary, topology, [], registry)

        assert classification.innovation_type is not None
        assert 0.0 <= classification.confidence <= 1.0

    def test_pipeline_with_manifest_freshness_check(
        self, sample_source_document_arxiv, clearinghouse_manifests, tmp_path,
    ):
        """Freshness check on real manifests succeeds, then evaluate paper."""
        report = check_all_manifests_freshness(clearinghouse_manifests)

        assert report.manifests_checked > 0
        # Real manifests should have generated_at
        assert report.missing_timestamp_count == 0

        # Now evaluate the paper
        store = tmp_path / "art_store"
        store.mkdir()

        result = evaluate_single_paper(
            sample_source_document_arxiv,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert result.error is None

    def test_no_agent_factors_import_errors(self):
        """All agent-factors imports work during pipeline execution."""
        from agent_factors.artifacts import ArtifactRegistry
        from agent_factors.g_layer.maturity import check_maturity_eligibility
        from agent_factors.g_layer.escalation import EscalationTrigger
        from agent_factors.catalog import CatalogLoader

        assert ArtifactRegistry is not None
        assert check_maturity_eligibility is not None
        assert EscalationTrigger is not None
        assert CatalogLoader is not None

    def test_batch_end_to_end(
        self, sample_source_documents_batch, clearinghouse_manifests, tmp_path,
    ):
        """3 SourceDocuments → evaluate_batch → BatchEvaluationSummary."""
        store = tmp_path / "art_store"
        store.mkdir()

        summary = evaluate_batch(
            sample_source_documents_batch,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert summary.total_papers == 3
        assert len(summary.results) == 3
        # All should have innovation_type set (even if different types)
        for result in summary.results:
            if result.error is None:
                assert result.innovation_type is not None
        assert summary.successful >= 2  # at minimum the arxiv + arch docs succeed
