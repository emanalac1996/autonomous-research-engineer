"""Paper ingestion adapter: convert prior-art-retrieval SourceDocument to ComprehensionSummary.

Uses direct structured conversion — ContentBlocks already have block_type and
section_label which map to PaperSection.section_type. Reuses the parser's
extraction functions on the assembled sections.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from prior_art.schema.source_document import ContentBlock, SourceDocument

from research_engineer.comprehension.parser import (
    extract_claims,
    extract_inputs_outputs,
    extract_limitations,
    extract_math_core,
    extract_paper_terms,
    extract_transformation,
)
from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    PaperSection,
    SectionType,
)

# ---------------------------------------------------------------------------
# Block type → SectionType mapping
# ---------------------------------------------------------------------------

_BLOCK_TYPE_TO_SECTION: dict[str, SectionType] = {
    "abstract": SectionType.abstract,
    "benchmark_result": SectionType.results,
    "model_architecture": SectionType.method,
    "code": SectionType.method,
    "claim": SectionType.other,
    "table": SectionType.results,
}

_SECTION_LABEL_MAP: dict[str, SectionType] = {
    "abstract": SectionType.abstract,
    "introduction": SectionType.other,
    "method": SectionType.method,
    "methods": SectionType.method,
    "methodology": SectionType.method,
    "approach": SectionType.method,
    "experiment": SectionType.results,
    "experiments": SectionType.results,
    "results": SectionType.results,
    "evaluation": SectionType.results,
    "discussion": SectionType.limitations,
    "limitations": SectionType.limitations,
    "conclusion": SectionType.other,
    "related work": SectionType.other,
    "claims": SectionType.other,
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AdaptationResult(BaseModel):
    """Result of adapting a SourceDocument to ComprehensionSummary."""

    model_config = ConfigDict()

    summary: ComprehensionSummary
    source_document_id: str
    corpus: str
    quality_score: float
    warnings: list[str] = Field(default_factory=list)
    extraction_failures: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Conversion functions
# ---------------------------------------------------------------------------


def content_block_to_section(block: ContentBlock) -> PaperSection | None:
    """Convert a single ContentBlock to a PaperSection.

    Returns None for blocks that cannot be converted to textual sections
    (e.g. figure blocks without meaningful text).
    """
    # Skip figure blocks — no textual content
    if block.block_type == "figure":
        return None

    # Skip blocks with empty content
    if not block.content or not block.content.strip():
        return None

    # Determine section type
    if block.block_type in _BLOCK_TYPE_TO_SECTION:
        section_type = _BLOCK_TYPE_TO_SECTION[block.block_type]
    else:
        section_type = SectionType.other

    # For text blocks, refine by section_label
    if block.block_type == "text" and block.section_label:
        label_key = block.section_label.strip().lower()
        if label_key in _SECTION_LABEL_MAP:
            section_type = _SECTION_LABEL_MAP[label_key]

    heading = block.section_label or ""

    return PaperSection(
        section_type=section_type,
        heading=heading,
        content=block.content,
    )


def content_blocks_to_sections(blocks: list[ContentBlock]) -> list[PaperSection]:
    """Convert all ContentBlocks to PaperSections, ordered by sequence."""
    sorted_blocks = sorted(blocks, key=lambda b: b.sequence)
    sections: list[PaperSection] = []
    for block in sorted_blocks:
        section = content_block_to_section(block)
        if section is not None:
            sections.append(section)
    return sections


def _enrich_paper_terms(
    parser_terms: list[str],
    doc: SourceDocument,
) -> list[str]:
    """Merge parser-extracted terms with upstream classifications.

    Combines keywords, techniques, and tasks from the SourceDocument's
    Classifications into paper_terms, deduplicating case-insensitively.
    """
    upstream_terms: list[str] = []
    if doc.classifications:
        upstream_terms.extend(doc.classifications.keywords)
        upstream_terms.extend(doc.classifications.techniques)
        upstream_terms.extend(doc.classifications.tasks)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for term in parser_terms + upstream_terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            result.append(term)

    return result


def adapt_source_document(doc: SourceDocument) -> AdaptationResult:
    """Convert a SourceDocument to a ComprehensionSummary.

    Pipeline:
    1. Convert content_blocks → PaperSections (structured mapping)
    2. Title from doc.title
    3. Call parser extraction functions on assembled sections
    4. Enrich paper_terms with upstream classifications
    5. Build ComprehensionSummary
    6. Collect warnings for missing/empty fields
    """
    warnings: list[str] = []

    # 1. Convert content blocks to sections
    sections = content_blocks_to_sections(doc.content_blocks)

    if not sections:
        warnings.append("No content blocks could be converted to sections")

    # 2. Title
    title = doc.title or ""
    if not title:
        warnings.append("Document has no title")

    # Add title as a title section for term extraction
    all_sections = list(sections)
    if title:
        all_sections.insert(
            0,
            PaperSection(
                section_type=SectionType.title,
                heading="Title",
                content=title,
            ),
        )

    # 3. Call extraction functions
    claims = extract_claims(all_sections)
    math_core = extract_math_core(all_sections)
    limitations = extract_limitations(all_sections)
    paper_terms = extract_paper_terms(all_sections)
    inputs, outputs = extract_inputs_outputs(all_sections)

    # Transformation — with fallback to title
    transformation = extract_transformation(all_sections)
    if not transformation or not transformation.strip():
        # Fall back to title
        transformation = title if title else "Unknown transformation"
        warnings.append("Could not extract transformation_proposed; using title as fallback")

    # 4. Enrich paper terms
    paper_terms = _enrich_paper_terms(paper_terms, doc)

    # 5. Build ComprehensionSummary
    summary = ComprehensionSummary(
        title=title,
        transformation_proposed=transformation,
        inputs_required=inputs,
        outputs_produced=outputs,
        claims=claims,
        limitations=limitations,
        mathematical_core=math_core,
        sections=sections,
        paper_terms=paper_terms,
    )

    # 6. Quality score
    quality_score = 0.0
    if doc.quality:
        quality_score = doc.quality.overall_quality_score

    return AdaptationResult(
        summary=summary,
        source_document_id=doc.document_id,
        corpus=doc.corpus,
        quality_score=quality_score,
        warnings=warnings,
    )
