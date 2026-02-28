"""Batch evaluation pipeline: process multiple papers through the full pipeline.

Runs each SourceDocument through adapt → topology → classify → feasibility,
with per-paper ledger logging and aggregate summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from prior_art.schema.source_document import SourceDocument

from research_engineer.integration.adapter import adapt_source_document


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class PaperEvaluationResult(BaseModel):
    """Result of evaluating a single paper through the pipeline."""

    model_config = ConfigDict()

    document_id: str
    title: str
    corpus: str
    adaptation_warnings: list[str] = Field(default_factory=list)
    innovation_type: str | None = None
    classification_confidence: float | None = None
    feasibility_status: str | None = None
    blueprint_path: str | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchEvaluationSummary(BaseModel):
    """Aggregate summary of a batch evaluation run."""

    model_config = ConfigDict()

    total_papers: int = 0
    successful: int = 0
    failed: int = 0
    by_innovation_type: dict[str, int] = Field(default_factory=dict)
    by_feasibility_status: dict[str, int] = Field(default_factory=dict)
    results: list[PaperEvaluationResult] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Single paper evaluation
# ---------------------------------------------------------------------------


def evaluate_single_paper(
    doc: SourceDocument,
    manifests_dir: Path,
    artifact_store: Path,
    translate: bool = False,
    output_dir: Path | None = None,
    ledger_path: Path | None = None,
) -> PaperEvaluationResult:
    """Evaluate a single paper through the full pipeline.

    Steps:
    1. adapt_source_document(doc) → AdaptationResult
    2. analyze_topology(summary) → TopologyChange
    3. classify(summary, topology, [], registry) → ClassificationResult
    4. assess_feasibility(summary, classification, manifests_dir)
    5. If translate and feasible: translate → write_blueprint
    """
    try:
        # 1. Adapt
        adaptation = adapt_source_document(doc)
        summary = adaptation.summary

        # 2. Topology
        from research_engineer.comprehension.topology import analyze_topology

        topology = analyze_topology(summary)

        # 3. Classify
        from agent_factors.artifacts import ArtifactRegistry
        from research_engineer.classifier.heuristics import classify
        from research_engineer.classifier.seed_artifact import register_seed_artifact

        artifact_store.mkdir(parents=True, exist_ok=True)
        registry = ArtifactRegistry(store_dir=artifact_store)
        register_seed_artifact(registry)

        classification = classify(summary, topology, [], registry)

        # 4. Feasibility
        from research_engineer.feasibility.gate import assess_feasibility

        feasibility = assess_feasibility(summary, classification, manifests_dir)

        result = PaperEvaluationResult(
            document_id=doc.document_id,
            title=doc.title,
            corpus=doc.corpus,
            adaptation_warnings=adaptation.warnings,
            innovation_type=classification.innovation_type.value,
            classification_confidence=classification.confidence,
            feasibility_status=feasibility.status.value,
        )

        # 5. Translate (optional)
        if translate and output_dir and feasibility.status.value in (
            "FEASIBLE", "FEASIBLE_WITH_ADAPTATION",
        ):
            from research_engineer.translator.serializer import write_blueprint
            from research_engineer.translator.translator import (
                TranslationInput,
                translate as do_translate,
            )

            translation_input = TranslationInput(
                summary=summary,
                classification=classification,
                manifests_dir=manifests_dir,
                ledger_path=ledger_path,
            )
            translation_result = do_translate(translation_input)
            blueprint_path = write_blueprint(translation_result, output_dir)
            result.blueprint_path = str(blueprint_path)

        return result

    except Exception as e:
        return PaperEvaluationResult(
            document_id=doc.document_id,
            title=doc.title,
            corpus=doc.corpus,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------


def evaluate_batch(
    documents: list[SourceDocument],
    manifests_dir: Path,
    artifact_store: Path,
    translate: bool = False,
    output_dir: Path | None = None,
    ledger_path: Path | None = None,
) -> BatchEvaluationSummary:
    """Evaluate multiple papers sequentially with per-paper ledger logging."""
    started_at = datetime.now(timezone.utc)
    results: list[PaperEvaluationResult] = []
    by_innovation_type: dict[str, int] = {}
    by_feasibility_status: dict[str, int] = {}
    successful = 0
    failed = 0

    for doc in documents:
        result = evaluate_single_paper(
            doc,
            manifests_dir=manifests_dir,
            artifact_store=artifact_store,
            translate=translate,
            output_dir=output_dir,
            ledger_path=ledger_path,
        )
        results.append(result)

        if result.error is not None:
            failed += 1
        else:
            successful += 1
            if result.innovation_type:
                by_innovation_type[result.innovation_type] = (
                    by_innovation_type.get(result.innovation_type, 0) + 1
                )
            if result.feasibility_status:
                by_feasibility_status[result.feasibility_status] = (
                    by_feasibility_status.get(result.feasibility_status, 0) + 1
                )

        # Write ledger entry
        if ledger_path:
            _write_ledger_entry(result, ledger_path)

    return BatchEvaluationSummary(
        total_papers=len(documents),
        successful=successful,
        failed=failed,
        by_innovation_type=by_innovation_type,
        by_feasibility_status=by_feasibility_status,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Ledger writing
# ---------------------------------------------------------------------------


def _write_ledger_entry(
    result: PaperEvaluationResult,
    ledger_path: Path,
) -> None:
    """Append a JSONL entry for a single paper evaluation."""
    entry = {
        "timestamp": result.timestamp.isoformat(),
        "agent": "autonomous-research-engineer",
        "action": "paper_evaluation",
        "document_id": result.document_id,
        "title": result.title,
        "corpus": result.corpus,
        "innovation_type": result.innovation_type,
        "feasibility_status": result.feasibility_status,
        "error": result.error,
        "affected_repos": ["autonomous-research-engineer"],
    }

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
