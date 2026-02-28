# Phase 7: Integration with Video Pipeline — Implementation Plan

## Context

Phases 0–6 are complete (343 tests). Phase 7 connects the autonomous-research-engineer
pipeline to multimodal-rag-core's video pipeline so conference talk videos (slide images +
ASR transcripts) can be fed through classification → feasibility → blueprint.

multimodal-rag-core (v0.2.0, manifest refreshed 2026-02-28) has no single unified video
output — stages produce independent types: `VideoSegment`, `SegmentTranscript`,
`SlideTranscript`, `UniqueSlide`, `SlideExtractionResult`. Phase 7 defines a bundling
model (`VideoPipelineOutput`) and conversion logic to produce `ComprehensionSummary`.

**Key design decision:** Mirror models instead of hard imports. We define `SlideData` and
`SegmentTranscriptData` as lightweight Pydantic models matching the essential fields from
multimodal-rag-core types. This keeps multimodal-rag-core as an optional dependency —
the adapter works without it installed at runtime.

---

## Implementation Order

```
pyproject.toml (add video optional dep)
       │
       v
   WU 7.1: video_adapter.py (VideoPipelineOutput → ComprehensionSummary)
       │
       v
   WU 7.2: video_comprehension.py (topology signals from visual slides)
       │
       v
   WU 7.3: test_video_end_to_end.py (full pipeline integration tests)
       │
       v
   conftest fixtures + __init__.py exports
```

---

## WU 7.1: Video Ingestion Adapter

**Create** `research_engineer/integration/video_adapter.py`

Follows the Phase 6 `adapter.py` pattern exactly: Pydantic models, conversion functions,
orchestrator that calls the parser's `extract_*` functions on assembled sections.

### Models

| Model | Key Fields |
|-------|-----------|
| `SlideData` | `slide_number: int`, `description: str`, `start_s: float`, `end_s: float`, `text: str`, `word_count: int` — mirrors `SlideTranscript` from `multimodal_rag.asr.slide_transcript_sync` |
| `SegmentTranscriptData` | `text: str`, `language: str`, `duration_s: float`, `word_count: int`, `segment_index: int \| None` — mirrors `SegmentTranscript` from `multimodal_rag.asr.transcriber` |
| `VideoPipelineOutput` | `title: str`, `video_path: str`, `slide_transcripts: list[SlideData]`, `segment_transcripts: list[SegmentTranscriptData]`, `metadata: dict` |
| `VideoAdaptationResult` | `summary: ComprehensionSummary`, `video_path: str`, `source_type: str = "video_pipeline"`, `quality_score: float`, `slide_count: int`, `total_duration_s: float`, `warnings: list[str]`, `slide_descriptions: list[str]` |

### Slide Description → SectionType Mapping

`_SLIDE_DESCRIPTION_KEYWORDS` dict (case-insensitive keyword → SectionType):
- abstract/overview → `.abstract`
- method/approach/algorithm/implementation/architecture/design → `.method`
- experiment/results/evaluation/benchmark/performance/comparison → `.results`
- limitation/discussion/future work → `.limitations`
- introduction/conclusion/summary/references/thank/q&a/questions → `.other`

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `infer_section_type` | `(description: str) → SectionType` | Keyword match on slide description, default `.other` |
| `slide_data_to_section` | `(slide: SlideData, sequence: int) → PaperSection \| None` | Single slide → section; None if empty text |
| `segment_transcripts_to_sections` | `(transcripts: list[SegmentTranscriptData]) → list[PaperSection]` | Fallback: raw segments → sections (all typed `.other`) |
| `adapt_video_pipeline_output` | `(output: VideoPipelineOutput) → VideoAdaptationResult` | Full pipeline (see below) |

### adapt_video_pipeline_output pipeline

1. If `output.slide_transcripts` non-empty: convert each to `PaperSection` via `slide_data_to_section`, collect `slide_descriptions`
2. Else if `output.segment_transcripts` non-empty: fallback via `segment_transcripts_to_sections`, add warning
3. Else: empty sections, add warning
4. Insert title as `SectionType.title` section for term extraction
5. Call `extract_claims`, `extract_math_core`, `extract_limitations`, `extract_paper_terms`, `extract_transformation`, `extract_inputs_outputs` on assembled sections
6. Fallback `transformation_proposed` to title if extraction empty
7. Compute quality heuristic: `(min(section_count/5, 1) + min(word_count/500, 1)) / 2`
8. Return `VideoAdaptationResult` with `slide_descriptions` for WU 7.2

**Imports from own parser:** `extract_claims`, `extract_math_core`, `extract_paper_terms`, `extract_transformation`, `extract_limitations`, `extract_inputs_outputs`
**No imports from multimodal-rag-core** — mirror models only.

### Tests (`tests/test_integration/test_video_adapter.py`) — 7 tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_method_keyword_maps_to_method` | `infer_section_type("System Architecture Overview") == SectionType.method` |
| 2 | `test_results_keyword_maps_to_results` | `infer_section_type("Benchmark Results") == SectionType.results` |
| 3 | `test_unknown_description_maps_to_other` | `infer_section_type("Thank you slide") == SectionType.other` |
| 4 | `test_slide_with_text_produces_section` | SlideData with method description → PaperSection with `section_type=method` |
| 5 | `test_slide_with_empty_text_returns_none` | SlideData with `text=""` → None |
| 6 | `test_fallback_produces_other_sections` | 2 SegmentTranscriptData → 2 PaperSections with `section_type=other`, ordered by `segment_index` |
| 7 | `test_full_adaptation_from_slide_transcripts` | VideoPipelineOutput with 4 slides → VideoAdaptationResult with non-empty summary, correct slide_count, slide_descriptions populated, no error warnings |

---

## WU 7.2: Multi-modal Comprehension Extension

**Create** `research_engineer/integration/video_comprehension.py`

The blueprint requires: "extend parser to handle slide+transcript input alongside pure text;
weight visual elements (diagrams, architecture figures) as topology signals."

### How topology signals work

`analyze_topology()` (in `comprehension/topology.py`) does keyword matching on
`transformation_proposed` + abstract/method section content. It looks for phrases like
"new stage", "intermediate representation", "new pipeline stage" (stage_addition keywords),
"replace", "swap" (component_swap keywords), etc.

Visual topology signals from video: slides described as "System Architecture Diagram" or
"Data Pipeline Flow" indicate the speaker is presenting topology changes. We enrich the
section content by prepending the slide description, which naturally adds terms like
"architecture", "pipeline" into the text the topology analyzer sees.

### Constants

`_TOPOLOGY_VISUAL_KEYWORDS`: list of keywords indicating topology-relevant visual content:
`"architecture"`, `"system design"`, `"pipeline"`, `"data flow"`, `"diagram"`,
`"flowchart"`, `"block diagram"`, `"system overview"`, `"component diagram"`,
`"network topology"`, `"infrastructure"`, `"deployment"`

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `extract_topology_signals` | `(slide_descriptions: list[str]) → list[str]` | Return descriptions containing topology visual keywords |
| `augment_sections_with_visual_weight` | `(sections: list[PaperSection], slide_descriptions: list[str]) → list[PaperSection]` | For architecture/diagram slides, prepend description to section content |
| `build_video_comprehension_summary` | `(output: VideoPipelineOutput) → tuple[ComprehensionSummary, list[str]]` | Orchestrator: adapt → extract signals → augment → return (summary, topology_signals) |

### augment_sections_with_visual_weight logic

1. Build set of topology-relevant slide indices from `slide_descriptions`
2. For each section, check if its heading matches a topology-relevant description
3. If match: prepend `"{description}. "` to section content
4. Return new list of PaperSections

### build_video_comprehension_summary pipeline

1. `adapt_video_pipeline_output(output)` → VideoAdaptationResult
2. `extract_topology_signals(adaptation.slide_descriptions)` → topology_signals
3. If signals found: `augment_sections_with_visual_weight(summary.sections, slide_descriptions)`
4. Rebuild ComprehensionSummary with augmented sections
5. Return `(summary, topology_signals)`

### Tests (`tests/test_integration/test_video_comprehension.py`) — 6 tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_architecture_slide_detected` | `["System Architecture Overview", "Intro", "Results"]` → returns `["System Architecture Overview"]` |
| 2 | `test_pipeline_diagram_detected` | `["Data Pipeline Flow", "Method"]` → returns `["Data Pipeline Flow"]` |
| 3 | `test_no_topology_signals_from_text_slides` | `["Introduction", "Conclusion", "Thank You"]` → returns `[]` |
| 4 | `test_architecture_section_gets_enrichment` | Section from architecture slide has description prepended to content |
| 5 | `test_non_topology_section_unchanged` | Section from results slide has original content unchanged |
| 6 | `test_full_video_comprehension_with_topology` | VideoPipelineOutput with architecture slide → summary is ComprehensionSummary, topology_signals non-empty, at least one section contains enriched content |

---

## WU 7.3: End-to-End Integration Tests

**Create** `tests/test_integration/test_video_end_to_end.py` — 5 tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_video_to_classification` | VideoPipelineOutput → `build_video_comprehension_summary` → `analyze_topology` → `classify` → ClassificationResult with non-None `innovation_type` and `confidence` in [0,1] |
| 2 | `test_architecture_slides_detect_topology` | VideoPipelineOutput with "System Architecture Diagram" slide + text mentioning "new pipeline stage" → topology_signals ≥ 1, TopologyChange.change_type ≠ `none` |
| 3 | `test_video_to_feasibility` | Full pipeline: video → summary → topology → classify → `assess_feasibility` → FeasibilityResult with non-None `status` |
| 4 | `test_agent_factors_imports_during_video` | Verify agent-factors imports (ArtifactRegistry, check_maturity_eligibility, EscalationTrigger, CatalogLoader) all work — mirrors Phase 6 pattern |
| 5 | `test_mixed_video_and_paper_evaluation` | 1 VideoPipelineOutput + 1 SourceDocument (arxiv fixture) → both produce valid ClassificationResult through same downstream pipeline |

---

## Conftest Fixtures (append to `tests/conftest.py`)

| Fixture | Returns |
|---------|---------|
| `sample_video_pipeline_output` | VideoPipelineOutput with 4 slides (abstract, method, results, limitations) — learned sparse retrieval talk |
| `sample_video_pipeline_output_with_architecture` | VideoPipelineOutput with "System Architecture Diagram" slide — knowledge graph construction talk |
| `sample_video_pipeline_output_empty` | VideoPipelineOutput with no slides/transcripts (edge case) |
| `sample_video_pipeline_output_segments_only` | VideoPipelineOutput with segment_transcripts but no slide sync (fallback path) |

---

## __init__.py Exports

Add to `research_engineer/integration/__init__.py`:

```python
# video_adapter (7.1)
"SegmentTranscriptData", "SlideData", "VideoAdaptationResult", "VideoPipelineOutput",
"adapt_video_pipeline_output", "infer_section_type", "segment_transcripts_to_sections",
"slide_data_to_section",
# video_comprehension (7.2)
"augment_sections_with_visual_weight", "build_video_comprehension_summary",
"extract_topology_signals",
```

---

## pyproject.toml Changes

```toml
[project.optional-dependencies]
graph = ["networkx>=3.0"]
integration = ["prior-art-retrieval"]
video = ["multimodal-rag-core"]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "prior-art-retrieval",
    "multimodal-rag-core",
]
```

**Setup:** `pip install -e "../multimodal-rag-core" --break-system-packages && pip install -e ".[dev]" --break-system-packages`

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Modify | `pyproject.toml` | setup |
| Create | `research_engineer/integration/video_adapter.py` | 7.1 |
| Create | `research_engineer/integration/video_comprehension.py` | 7.2 |
| Modify | `research_engineer/integration/__init__.py` | all |
| Create | `tests/test_integration/test_video_adapter.py` | 7.1 |
| Create | `tests/test_integration/test_video_comprehension.py` | 7.2 |
| Create | `tests/test_integration/test_video_end_to_end.py` | 7.3 |
| Modify | `tests/conftest.py` (append 4 fixtures) | all |

**Total new tests: 18** (within blueprint estimate of 15–20)
**Running total: 343 + 18 = ~361 tests**

---

## Verification

```bash
pip install -e "../multimodal-rag-core" --break-system-packages
pip install -e ".[dev]" --break-system-packages
python3 -m pytest tests/test_integration/test_video_adapter.py -v       # 7 tests
python3 -m pytest tests/test_integration/test_video_comprehension.py -v # 6 tests
python3 -m pytest tests/test_integration/test_video_end_to_end.py -v    # 5 tests
python3 -m pytest tests/ -v                                              # all ~361 tests
python3 -c "from research_engineer.integration import adapt_video_pipeline_output, build_video_comprehension_summary, extract_topology_signals"
```
