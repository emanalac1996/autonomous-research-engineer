"""End-to-end video integration tests (WU 7.3).

Tests the full pipeline from VideoPipelineOutput through comprehension,
classification, feasibility, and mixed video+paper evaluation.
"""

from research_engineer.comprehension.topology import TopologyChangeType, analyze_topology
from research_engineer.integration.video_adapter import adapt_video_pipeline_output
from research_engineer.integration.video_comprehension import (
    build_video_comprehension_summary,
)


class TestVideoEndToEndPipeline:
    """End-to-end video pipeline integration tests."""

    def test_video_to_classification(
        self, sample_video_pipeline_output, clearinghouse_manifests, tmp_path,
    ):
        """VideoPipelineOutput runs through full pipeline to ClassificationResult."""
        summary, _ = build_video_comprehension_summary(sample_video_pipeline_output)
        topology = analyze_topology(summary)

        store = tmp_path / "art_store"
        store.mkdir()

        from agent_factors.artifacts import ArtifactRegistry
        from research_engineer.classifier.heuristics import classify
        from research_engineer.classifier.seed_artifact import register_seed_artifact

        registry = ArtifactRegistry(store_dir=store)
        register_seed_artifact(registry)
        classification = classify(summary, topology, [], registry)

        assert classification.innovation_type is not None
        assert 0.0 <= classification.confidence <= 1.0

    def test_architecture_slides_detect_topology(
        self, sample_video_pipeline_output_with_architecture,
    ):
        """Video with architecture slide detects non-none topology change."""
        summary, topology_signals = build_video_comprehension_summary(
            sample_video_pipeline_output_with_architecture,
        )

        assert len(topology_signals) >= 1
        assert any("Architecture" in s for s in topology_signals)

        topology = analyze_topology(summary)
        assert topology.change_type != TopologyChangeType.none

    def test_video_to_feasibility(
        self, sample_video_pipeline_output, clearinghouse_manifests, tmp_path,
    ):
        """Full pipeline: video -> summary -> topology -> classify -> feasibility."""
        summary, _ = build_video_comprehension_summary(sample_video_pipeline_output)
        topology = analyze_topology(summary)

        store = tmp_path / "art_store"
        store.mkdir()

        from agent_factors.artifacts import ArtifactRegistry
        from research_engineer.classifier.heuristics import classify
        from research_engineer.classifier.seed_artifact import register_seed_artifact
        from research_engineer.feasibility.gate import assess_feasibility

        registry = ArtifactRegistry(store_dir=store)
        register_seed_artifact(registry)
        classification = classify(summary, topology, [], registry)

        feasibility = assess_feasibility(
            summary, classification, clearinghouse_manifests,
        )

        assert feasibility.status is not None
        assert feasibility.innovation_type == classification.innovation_type

    def test_agent_factors_imports_during_video(self):
        """All agent-factors imports work during video pipeline execution."""
        from agent_factors.artifacts import ArtifactRegistry
        from agent_factors.g_layer.maturity import check_maturity_eligibility
        from agent_factors.g_layer.escalation import EscalationTrigger
        from agent_factors.catalog import CatalogLoader

        assert ArtifactRegistry is not None
        assert check_maturity_eligibility is not None
        assert EscalationTrigger is not None
        assert CatalogLoader is not None

    def test_mixed_video_and_paper_evaluation(
        self, sample_video_pipeline_output, sample_source_document_arxiv,
        clearinghouse_manifests, tmp_path,
    ):
        """Video and paper both produce valid ClassificationResults."""
        store = tmp_path / "art_store"
        store.mkdir()

        from agent_factors.artifacts import ArtifactRegistry
        from research_engineer.classifier.heuristics import classify
        from research_engineer.classifier.seed_artifact import register_seed_artifact
        from research_engineer.integration.adapter import adapt_source_document

        registry = ArtifactRegistry(store_dir=store)
        register_seed_artifact(registry)

        # Video path
        video_summary, _ = build_video_comprehension_summary(
            sample_video_pipeline_output,
        )
        video_topology = analyze_topology(video_summary)
        video_classification = classify(video_summary, video_topology, [], registry)

        # Paper path
        adaptation = adapt_source_document(sample_source_document_arxiv)
        paper_topology = analyze_topology(adaptation.summary)
        paper_classification = classify(
            adaptation.summary, paper_topology, [], registry,
        )

        # Both produce valid classifications
        assert video_classification.innovation_type is not None
        assert paper_classification.innovation_type is not None
        assert 0.0 <= video_classification.confidence <= 1.0
        assert 0.0 <= paper_classification.confidence <= 1.0
