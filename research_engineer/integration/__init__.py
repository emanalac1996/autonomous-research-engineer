"""Stage 6: Integration with prior-art-retrieval — paper ingestion, batch evaluation, manifest freshness."""

from research_engineer.integration.adapter import (
    AdaptationResult,
    adapt_source_document,
    content_block_to_section,
    content_blocks_to_sections,
)
from research_engineer.integration.batch_pipeline import (
    BatchEvaluationSummary,
    PaperEvaluationResult,
    evaluate_batch,
    evaluate_single_paper,
)
from research_engineer.integration.manifest_freshness import (
    FreshnessReport,
    ManifestFreshnessResult,
    check_all_manifests_freshness,
    check_manifest_freshness,
)

__all__ = [
    # adapter (6.1)
    "AdaptationResult",
    "adapt_source_document",
    "content_block_to_section",
    "content_blocks_to_sections",
    # batch_pipeline (6.2)
    "BatchEvaluationSummary",
    "PaperEvaluationResult",
    "evaluate_batch",
    "evaluate_single_paper",
    # manifest_freshness (6.3)
    "FreshnessReport",
    "ManifestFreshnessResult",
    "check_all_manifests_freshness",
    "check_manifest_freshness",
]
