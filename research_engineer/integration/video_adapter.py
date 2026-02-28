"""Video ingestion adapter: convert video pipeline output to ComprehensionSummary.

Defines mirror models (SlideData, SegmentTranscriptData) matching multimodal-rag-core
types without hard import dependency. Converts slide transcripts or raw segment
transcripts to PaperSections, then reuses the parser's extraction functions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
# Mirror models (no multimodal-rag-core import required)
# ---------------------------------------------------------------------------


class SlideData(BaseModel):
    """Serializable slide+transcript data from the video pipeline.

    Mirrors the essential fields of multimodal_rag.asr.slide_transcript_sync.SlideTranscript
    without requiring a hard import dependency.
    """

    model_config = ConfigDict()

    slide_number: int = 0
    description: str = ""
    start_s: float = 0.0
    end_s: float = 0.0
    text: str = ""
    word_count: int = 0


class SegmentTranscriptData(BaseModel):
    """Serializable transcript data for a single video segment.

    Mirrors multimodal_rag.asr.transcriber.SegmentTranscript.
    """

    model_config = ConfigDict()

    text: str = ""
    language: str = "en"
    duration_s: float = 0.0
    word_count: int = 0
    segment_index: int | None = None


class VideoPipelineOutput(BaseModel):
    """Bundled output from the multimodal-rag-core video pipeline.

    Since multimodal-rag-core produces independent typed outputs from each
    stage, this model bundles the relevant outputs into a single structure
    that the video adapter can consume.
    """

    model_config = ConfigDict()

    title: str = ""
    video_path: str = ""
    slide_transcripts: list[SlideData] = Field(default_factory=list)
    segment_transcripts: list[SegmentTranscriptData] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class VideoAdaptationResult(BaseModel):
    """Result of adapting video pipeline output to ComprehensionSummary."""

    model_config = ConfigDict()

    summary: ComprehensionSummary
    video_path: str = ""
    source_type: str = "video_pipeline"
    quality_score: float = 0.0
    slide_count: int = 0
    total_duration_s: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    slide_descriptions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Slide description → SectionType mapping
# ---------------------------------------------------------------------------

_SLIDE_DESCRIPTION_KEYWORDS: dict[str, SectionType] = {
    "abstract": SectionType.abstract,
    "overview": SectionType.abstract,
    "method": SectionType.method,
    "approach": SectionType.method,
    "algorithm": SectionType.method,
    "implementation": SectionType.method,
    "architecture": SectionType.method,
    "design": SectionType.method,
    "experiment": SectionType.results,
    "results": SectionType.results,
    "evaluation": SectionType.results,
    "benchmark": SectionType.results,
    "performance": SectionType.results,
    "comparison": SectionType.results,
    "limitation": SectionType.limitations,
    "discussion": SectionType.limitations,
    "future work": SectionType.limitations,
    "introduction": SectionType.other,
    "conclusion": SectionType.other,
    "summary": SectionType.other,
    "references": SectionType.other,
    "thank": SectionType.other,
    "q&a": SectionType.other,
    "questions": SectionType.other,
}


# ---------------------------------------------------------------------------
# Conversion functions
# ---------------------------------------------------------------------------


def infer_section_type(description: str) -> SectionType:
    """Infer SectionType from a slide description using keyword matching.

    Args:
        description: The slide description text (from ground truth or VLM).

    Returns:
        SectionType based on keyword match, defaulting to SectionType.other.
    """
    desc_lower = description.lower()
    for keyword, section_type in _SLIDE_DESCRIPTION_KEYWORDS.items():
        if keyword in desc_lower:
            return section_type
    return SectionType.other


def slide_data_to_section(slide: SlideData, sequence: int) -> PaperSection | None:
    """Convert a single slide's data to a PaperSection.

    Returns None if the slide has no transcript text.

    Args:
        slide: SlideData from the video pipeline.
        sequence: Ordering index for this section.

    Returns:
        PaperSection or None if no textual content.
    """
    if not slide.text or not slide.text.strip():
        return None

    section_type = infer_section_type(slide.description)

    return PaperSection(
        section_type=section_type,
        heading=slide.description or f"Slide {slide.slide_number}",
        content=slide.text.strip(),
    )


def segment_transcripts_to_sections(
    transcripts: list[SegmentTranscriptData],
) -> list[PaperSection]:
    """Convert segment transcripts to PaperSections (fallback path).

    Used when slide-transcript sync data is not available. All sections
    are typed as 'other' since raw segments lack structural information.

    Args:
        transcripts: List of segment transcripts ordered by segment_index.

    Returns:
        List of PaperSections, one per non-empty transcript.
    """
    sorted_transcripts = sorted(
        transcripts,
        key=lambda t: t.segment_index if t.segment_index is not None else 0,
    )
    sections: list[PaperSection] = []
    for t in sorted_transcripts:
        if not t.text or not t.text.strip():
            continue
        idx = t.segment_index if t.segment_index is not None else len(sections)
        sections.append(
            PaperSection(
                section_type=SectionType.other,
                heading=f"Segment {idx}",
                content=t.text.strip(),
            )
        )
    return sections


def adapt_video_pipeline_output(
    output: VideoPipelineOutput,
) -> VideoAdaptationResult:
    """Convert video pipeline output to a ComprehensionSummary.

    Pipeline:
    1. Convert slide_transcripts -> PaperSections (preferred path)
       OR segment_transcripts -> PaperSections (fallback path)
    2. Title from output.title
    3. Call parser extraction functions on assembled sections
    4. Build ComprehensionSummary
    5. Collect warnings for missing/empty fields

    Args:
        output: Bundled video pipeline output.

    Returns:
        VideoAdaptationResult with summary, metadata, and warnings.
    """
    warnings: list[str] = []
    slide_descriptions: list[str] = []

    # 1. Convert to sections
    if output.slide_transcripts:
        sections: list[PaperSection] = []
        for i, st in enumerate(output.slide_transcripts):
            section = slide_data_to_section(st, sequence=i)
            if section is not None:
                sections.append(section)
            slide_descriptions.append(st.description)
        if not sections:
            warnings.append("All slide transcripts had empty text")
    elif output.segment_transcripts:
        sections = segment_transcripts_to_sections(output.segment_transcripts)
        warnings.append(
            "No slide-transcript sync available; using raw segment transcripts"
        )
    else:
        sections = []
        warnings.append("No slide transcripts or segment transcripts provided")

    # 2. Title
    title = output.title or ""
    if not title:
        warnings.append("Video pipeline output has no title")

    # Add title section for term extraction
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
    inputs, outputs_produced = extract_inputs_outputs(all_sections)

    # Transformation
    transformation = extract_transformation(all_sections)
    if not transformation or not transformation.strip():
        transformation = title if title else "Unknown transformation from video"
        warnings.append(
            "Could not extract transformation_proposed; using title as fallback"
        )

    # 4. Build ComprehensionSummary
    summary = ComprehensionSummary(
        title=title,
        transformation_proposed=transformation,
        inputs_required=inputs,
        outputs_produced=outputs_produced,
        claims=claims,
        limitations=limitations,
        mathematical_core=math_core,
        sections=sections,
        paper_terms=paper_terms,
    )

    # 5. Quality score heuristic
    total_words = sum(len(s.content.split()) for s in sections)
    section_score = min(len(sections) / 5.0, 1.0)
    word_score = min(total_words / 500.0, 1.0)
    quality_score = (section_score + word_score) / 2.0

    # Duration
    total_duration_s = 0.0
    if output.slide_transcripts:
        ends = [st.end_s for st in output.slide_transcripts if st.end_s > 0]
        if ends:
            total_duration_s = max(ends)
    elif output.segment_transcripts:
        total_duration_s = sum(t.duration_s for t in output.segment_transcripts)

    return VideoAdaptationResult(
        summary=summary,
        video_path=output.video_path,
        quality_score=quality_score,
        slide_count=len(output.slide_transcripts),
        total_duration_s=total_duration_s,
        warnings=warnings,
        slide_descriptions=slide_descriptions,
    )
