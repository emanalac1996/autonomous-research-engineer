# Phase 6 Architecture: Integration with prior-art-retrieval

## Overview

Phase 6 bridges the prior-art-retrieval corpus (7 source adapters, 500+ tests)
with the autonomous-research-engineer pipeline. Papers ingested from arXiv, USPTO,
HuggingFace, Kaggle, leaderboards, GitHub, and ChinaXiv can now be automatically
evaluated for innovation type, feasibility, and blueprint generation.

```
prior-art-retrieval                 autonomous-research-engineer
┌─────────────────┐               ┌──────────────────────────┐
│ ArxivAdapter     │               │                          │
│ USPTOAdapter     │──→ Source ──→ │ adapter.py (6.1)         │
│ HuggingFace...   │   Document   │   ContentBlock → Section │
│ (7 adapters)     │               │   → ComprehensionSummary │
└─────────────────┘               │                          │
                                   │ batch_pipeline.py (6.2)  │
                                   │   evaluate_single_paper  │
                                   │   evaluate_batch          │
                                   │   → ledger logging       │
                                   │                          │
                                   │ manifest_freshness (6.3) │
                                   │   staleness detection    │
                                   └──────────────────────────┘
```

## Module Details

### 6.1 Paper Ingestion Adapter (`adapter.py`)

Converts `SourceDocument` (prior-art-retrieval) → `ComprehensionSummary` (our Stage 1 output).

**Strategy: Direct structured conversion.**

ContentBlock.block_type + section_label maps to PaperSection.section_type:

| block_type | section_label | → SectionType |
|-----------|--------------|---------------|
| abstract | * | abstract |
| text | Method/Methods/Methodology | method |
| text | Results/Experiments/Evaluation | results |
| text | Limitations/Discussion | limitations |
| text | (other/none) | other |
| benchmark_result | * | results |
| model_architecture | * | method |
| code | * | method |
| claim | * | other |
| table | * | results |
| figure | * | (skipped) |

After section assembly, reuses parser extraction functions:
- `extract_claims(sections)` — metric extraction from results/abstract
- `extract_math_core(sections)` — formulation/complexity from method
- `extract_paper_terms(sections)` — term matching + classification enrichment
- `extract_transformation(sections)` — proposal verb detection
- `extract_limitations(sections)` — sentence splitting
- `extract_inputs_outputs(sections)` — requirement/output detection

### 6.2 Batch Evaluation Pipeline (`batch_pipeline.py`)

Orchestrates N papers through the full pipeline:

```
SourceDocument
    → adapt_source_document() → ComprehensionSummary
    → analyze_topology() → TopologyChange
    → classify() → ClassificationResult
    → assess_feasibility() → FeasibilityResult
    → [translate() → Blueprint] (optional)
```

Per-paper results aggregated into `BatchEvaluationSummary` with:
- by_innovation_type / by_feasibility_status counts
- Per-paper JSONL ledger entries

Error isolation: exceptions caught per-paper, recorded in `error` field, batch continues.

### 6.3 Manifest Freshness Check (`manifest_freshness.py`)

Pre-flight check before feasibility assessment. Loads `generated_at` from
manifest YAML, computes age, warns if > 7 days (configurable).

Handles edge cases: missing `generated_at`, unparseable timestamps, timezone-naive strings.

## prior-art-retrieval Import Points

| Import | Source | Usage |
|--------|--------|-------|
| `SourceDocument` | `prior_art.schema.source_document` | Input model |
| `ContentBlock` | `prior_art.schema.source_document` | Block conversion |
| `Classifications` | `prior_art.schema.classifications` | Term enrichment |
| `QualitySignals` | `prior_art.schema.quality` | Quality passthrough |

We do NOT import adapters, CorpusManager, or ExtractionPipeline — those are
upstream concerns. We receive already-extracted SourceDocuments.

## Test Coverage

27 tests across 4 test files, covering adapter mapping, batch orchestration,
freshness checking, and end-to-end pipeline integration with real manifests.
