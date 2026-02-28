"""Integration: paper ingestion, batch evaluation, manifest freshness, video pipeline."""

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
from research_engineer.integration.video_adapter import (
    SegmentTranscriptData,
    SlideData,
    VideoAdaptationResult,
    VideoPipelineOutput,
    adapt_video_pipeline_output,
    infer_section_type,
    segment_transcripts_to_sections,
    slide_data_to_section,
)
from research_engineer.integration.video_comprehension import (
    augment_sections_with_visual_weight,
    build_video_comprehension_summary,
    extract_topology_signals,
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
    # video_adapter (7.1)
    "SegmentTranscriptData",
    "SlideData",
    "VideoAdaptationResult",
    "VideoPipelineOutput",
    "adapt_video_pipeline_output",
    "infer_section_type",
    "segment_transcripts_to_sections",
    "slide_data_to_section",
    # video_comprehension (7.2)
    "augment_sections_with_visual_weight",
    "build_video_comprehension_summary",
    "extract_topology_signals",
]
