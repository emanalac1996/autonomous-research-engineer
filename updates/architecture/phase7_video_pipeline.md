# Phase 7 Architecture: Integration with Video Pipeline

## Overview

Phase 7 bridges the multimodal-rag-core video pipeline (slide extraction + ASR)
with the autonomous-research-engineer pipeline. Conference talk videos processed
by multimodal-rag-core can now be automatically evaluated for innovation type,
feasibility, and blueprint generation.

```
multimodal-rag-core                 autonomous-research-engineer
┌─────────────────┐               ┌──────────────────────────┐
│ SlideTranscript   │               │                          │
│ SegmentTranscript │──→ Mirror ──→ │ video_adapter.py (7.1)   │
│ UniqueSlide       │   Models     │   SlideData → PaperSection│
│ VideoSegment      │               │   → ComprehensionSummary │
└─────────────────┘               │                          │
                                   │ video_comprehension (7.2) │
                                   │   topology signal detect  │
                                   │   visual weight augment   │
                                   │                          │
                                   │ end-to-end (7.3)         │
                                   │   video → classify →      │
                                   │   feasibility → blueprint │
                                   └──────────────────────────┘
```

## Module Details

### 7.1 Video Ingestion Adapter (`video_adapter.py`)

Converts video pipeline output → `ComprehensionSummary` (Stage 1 output).

**Strategy: Mirror models with keyword mapping.**

Defines `SlideData` and `SegmentTranscriptData` as lightweight Pydantic models matching
multimodal-rag-core's `SlideTranscript` and `SegmentTranscript` — no hard import required.

Slide description keywords map to SectionType:

| Keywords | → SectionType |
|----------|---------------|
| abstract, overview | abstract |
| method, approach, algorithm, architecture, design | method |
| experiment, results, evaluation, benchmark | results |
| limitation, discussion, future work | limitations |
| introduction, conclusion, thank, q&a | other |

After section assembly, reuses parser extraction functions:
- `extract_claims(sections)` — metric extraction from results/abstract
- `extract_math_core(sections)` — formulation/complexity from method
- `extract_paper_terms(sections)` — term matching + classification enrichment
- `extract_transformation(sections)` — proposal verb detection
- `extract_limitations(sections)` — sentence splitting
- `extract_inputs_outputs(sections)` — requirement/output detection

Two conversion paths:
1. **Preferred:** `slide_transcripts` → `slide_data_to_section()` per slide
2. **Fallback:** `segment_transcripts` → `segment_transcripts_to_sections()` (all typed `other`)

### 7.2 Multi-modal Comprehension (`video_comprehension.py`)

Extends comprehension to detect topology signals from visual slide content.

`_TOPOLOGY_VISUAL_KEYWORDS`: architecture, system design, pipeline, data flow,
diagram, flowchart, block diagram, system overview, component diagram, etc.

- `extract_topology_signals(descriptions)` → list of topology-relevant descriptions
- `augment_sections_with_visual_weight(sections, descriptions)` → prepends slide
  description to section content for topology-relevant slides
- `build_video_comprehension_summary(output)` → `(ComprehensionSummary, topology_signals)`

### 7.3 End-to-End Integration

Validates the full pipeline: video → comprehension → topology → classification →
feasibility. Tests mixed video+paper evaluation through the same downstream path.

## multimodal-rag-core Import Strategy

| Import | Source | Usage |
|--------|--------|-------|
| None | — | Mirror models only; no runtime dependency |

We define `SlideData` and `SegmentTranscriptData` locally. This keeps
multimodal-rag-core as an optional dependency — the adapter works without it.

## Test Coverage

18 tests across 3 test files, covering video adapter mapping, multi-modal
comprehension with topology signals, and end-to-end pipeline integration.
