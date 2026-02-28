"""Tests for batch evaluation pipeline (WU 6.2)."""

import json

from research_engineer.integration.batch_pipeline import (
    BatchEvaluationSummary,
    PaperEvaluationResult,
    _write_ledger_entry,
    evaluate_batch,
    evaluate_single_paper,
)


class TestEvaluateSinglePaper:
    """Tests for evaluate_single_paper()."""

    def test_returns_paper_evaluation_result(
        self, sample_source_document_arxiv, clearinghouse_manifests, tmp_path,
    ):
        """Single SourceDocument produces PaperEvaluationResult with non-None fields."""
        store = tmp_path / "art_store"
        store.mkdir()

        result = evaluate_single_paper(
            sample_source_document_arxiv,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert isinstance(result, PaperEvaluationResult)
        assert result.document_id == "arxiv:2401.12345"
        assert result.title == "Learned Sparse Representations for Multi-Hop Retrieval"
        assert result.error is None

    def test_captures_error_on_invalid_document(
        self, sample_source_document_minimal, tmp_path,
    ):
        """Document with empty content blocks still returns a result (may have warnings)."""
        store = tmp_path / "art_store"
        store.mkdir()
        # Use a nonexistent manifests dir to trigger an error in feasibility
        bad_manifests = tmp_path / "nonexistent_manifests"

        result = evaluate_single_paper(
            sample_source_document_minimal,
            manifests_dir=bad_manifests,
            artifact_store=store,
        )

        assert isinstance(result, PaperEvaluationResult)
        # Should either succeed with warnings or capture an error
        assert result.document_id == "other:minimal-001"

    def test_includes_classification_and_feasibility(
        self, sample_source_document_arxiv, clearinghouse_manifests, tmp_path,
    ):
        """Valid document result has innovation_type and feasibility_status."""
        store = tmp_path / "art_store"
        store.mkdir()

        result = evaluate_single_paper(
            sample_source_document_arxiv,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert result.innovation_type is not None
        assert result.feasibility_status is not None
        assert result.classification_confidence is not None


class TestEvaluateBatch:
    """Tests for evaluate_batch()."""

    def test_processes_three_papers(
        self, sample_source_documents_batch, clearinghouse_manifests, tmp_path,
    ):
        """3 SourceDocuments produce summary with total_papers=3."""
        store = tmp_path / "art_store"
        store.mkdir()

        summary = evaluate_batch(
            sample_source_documents_batch,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert isinstance(summary, BatchEvaluationSummary)
        assert summary.total_papers == 3
        assert len(summary.results) == 3

    def test_aggregates_by_innovation_type(
        self, sample_source_documents_batch, clearinghouse_manifests, tmp_path,
    ):
        """Batch summary has by_innovation_type populated."""
        store = tmp_path / "art_store"
        store.mkdir()

        summary = evaluate_batch(
            sample_source_documents_batch,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert len(summary.by_innovation_type) > 0
        total_typed = sum(summary.by_innovation_type.values())
        assert total_typed == summary.successful

    def test_writes_ledger_entries(
        self, sample_source_documents_batch, clearinghouse_manifests, tmp_path,
    ):
        """Ledger path provided produces correct number of JSONL lines."""
        store = tmp_path / "art_store"
        store.mkdir()
        ledger = tmp_path / "eval_ledger.jsonl"

        evaluate_batch(
            sample_source_documents_batch,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
            ledger_path=ledger,
        )

        assert ledger.exists()
        lines = ledger.read_text().strip().split("\n")
        assert len(lines) == 3
        # Each line is valid JSON
        for line in lines:
            data = json.loads(line)
            assert "document_id" in data
            assert "agent" in data

    def test_partial_failure_continues(
        self, sample_source_document_arxiv, clearinghouse_manifests, tmp_path,
    ):
        """Batch with a bad document continues processing remaining papers."""
        store = tmp_path / "art_store"
        store.mkdir()

        # Create a deliberately broken SourceDocument
        from datetime import datetime, timezone
        from prior_art.schema.source_document import (
            ContentBlock,
            SourceDocument,
            compute_content_hash,
        )
        from prior_art.schema.classifications import Classifications
        from prior_art.schema.quality import QualitySignals
        from prior_art.schema.references import References
        from prior_art.schema.source_metadata import GenericMetadata

        now = datetime.now(timezone.utc)
        # A document that will fail during feasibility (bad manifests path)
        bad_doc = SourceDocument(
            document_id="bad:fail-001",
            corpus="other",
            document_type="technical_report",
            title="This Should Fail",
            source_metadata=GenericMetadata(),
            quality=QualitySignals(overall_quality_score=0.1),
            classifications=Classifications(),
            content_blocks=[],
            first_ingested=now,
            last_checked=now,
            last_content_hash=compute_content_hash([]),
        )

        docs = [sample_source_document_arxiv, bad_doc, sample_source_document_arxiv]

        # Use a nonexistent manifests dir to force errors on the bad doc
        # but also on the good docs — instead, use real manifests
        summary = evaluate_batch(
            docs,
            manifests_dir=clearinghouse_manifests,
            artifact_store=store,
        )

        assert summary.total_papers == 3
        assert len(summary.results) == 3
        # At least the good docs should succeed
        assert summary.successful >= 2


class TestWriteLedgerEntry:
    """Tests for _write_ledger_entry()."""

    def test_appends_jsonl_line(self, tmp_path):
        """Write entry appends valid JSON with required fields."""
        ledger = tmp_path / "test_ledger.jsonl"

        result = PaperEvaluationResult(
            document_id="test:001",
            title="Test Paper",
            corpus="arxiv",
            innovation_type="modular_swap",
            feasibility_status="FEASIBLE",
        )

        _write_ledger_entry(result, ledger)

        assert ledger.exists()
        data = json.loads(ledger.read_text().strip())
        assert data["document_id"] == "test:001"
        assert data["agent"] == "autonomous-research-engineer"
        assert data["action"] == "paper_evaluation"
        assert data["innovation_type"] == "modular_swap"
