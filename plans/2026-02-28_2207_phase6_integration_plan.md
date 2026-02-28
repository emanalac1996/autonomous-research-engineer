# Phase 6: Integration with prior-art-retrieval — Implementation Plan

## Context

Phases 0-5 are complete (316 tests). Phase 6 connects the autonomous-research-engineer pipeline to the prior-art-retrieval repo so papers ingested from real corpus sources (arXiv, USPTO, etc.) can be fed through the classification → feasibility → blueprint pipeline.

The prior-art-retrieval repo (v0.4.0-dev, manifest refreshed 2026-02-28) now has a full extraction pipeline: `ExtractionPipeline`, `PDFDownloader`, `ContentBuilder`, and `fetch_full_text()` on ArxivAdapter/USPTOAdapter.

**Key constraint:** `prior-art-retrieval` is not currently installed. First step is `pip install -e ../prior-art-retrieval` and updating `pyproject.toml`.

---

## Implementation Order

```
pyproject.toml + pip install
       │
       v
   WU 6.1: adapter.py (SourceDocument → ComprehensionSummary)
       │           \
       v            v
   WU 6.2: batch    WU 6.3: manifest
   _pipeline.py     _freshness.py
       │            /
       v           v
   WU 6.4: test_end_to_end.py (integration tests)
       │
       v
   conftest fixtures + __init__.py exports
```

---

## WU 6.1: Paper Ingestion Adapter

**Create** `research_engineer/integration/adapter.py`

**Design decision:** Direct structured conversion — ContentBlocks already have `block_type` and `section_label` which map to `PaperSection.section_type`. We reuse the parser's extraction functions (`extract_claims`, `extract_math_core`, `extract_paper_terms`, `extract_transformation`, `extract_limitations`, `extract_inputs_outputs`) on the assembled sections — these all take `list[PaperSection]`.

| Model | Key Fields |
|-------|-----------|
| `AdaptationResult` | `summary: ComprehensionSummary`, `source_document_id: str`, `corpus: str`, `quality_score: float`, `warnings: list[str]`, `extraction_failures: list[str]` |

| Function | Signature | Purpose |
|----------|-----------|---------|
| `content_block_to_section` | `(block: ContentBlock) → PaperSection \| None` | Map single block; None for figure-only blocks |
| `content_blocks_to_sections` | `(blocks: list[ContentBlock]) → list[PaperSection]` | Convert all, sorted by sequence |
| `adapt_source_document` | `(doc: SourceDocument) → AdaptationResult` | Full conversion pipeline |

**Mapping logic (case-insensitive on section_label):**
- `block_type="abstract"` → `SectionType.abstract`
- `block_type="text"` → refined by `section_label`: method/methods/methodology/approach → `.method`, results/experiments/evaluation → `.results`, limitations/discussion → `.limitations`, else `.other`
- `block_type="benchmark_result"` → `.results`
- `block_type="model_architecture"` / `"code"` → `.method`
- `block_type="claim"` → `.other` (patent claims)
- `block_type="table"` → `.results` (if content non-empty)
- `block_type="figure"` → `None` (skip)

**adapt_source_document pipeline:**
1. Convert `doc.content_blocks` → `list[PaperSection]`
2. Title from `doc.title`
3. Call parser extraction functions on assembled sections
4. Enrich `paper_terms` with `doc.classifications.keywords + techniques + tasks`
5. Build `ComprehensionSummary`; if `transformation_proposed` empty, fall back to first sentence of abstract or title
6. Collect warnings for missing/empty fields

**Imports from prior-art-retrieval:** `SourceDocument`, `ContentBlock`, `Classifications` (schema only)
**Imports from own parser:** `extract_claims`, `extract_math_core`, `extract_paper_terms`, `extract_transformation`, `extract_limitations`, `extract_inputs_outputs`

**Tests** `tests/test_integration/test_adapter.py` — 9 tests:
1. Abstract block → abstract section
2. Text block with "Method" label → method section
3. Text block without label → other section
4. Figure block → None (skipped)
5. Blocks ordered by sequence
6. Empty blocks → empty sections
7. Full arXiv SourceDocument → valid ComprehensionSummary with title, transformation, sections, claims
8. Empty content_blocks → minimal summary with title + warning
9. Classifications keywords enriched into paper_terms

---

## WU 6.2: Batch Evaluation Pipeline

**Create** `research_engineer/integration/batch_pipeline.py`

| Model | Key Fields |
|-------|-----------|
| `PaperEvaluationResult` | `document_id`, `title`, `corpus`, `adaptation_warnings: list[str]`, `innovation_type: str \| None`, `classification_confidence: float \| None`, `feasibility_status: str \| None`, `blueprint_path: str \| None`, `error: str \| None`, `timestamp` |
| `BatchEvaluationSummary` | `total_papers`, `successful`, `failed`, `by_innovation_type: dict`, `by_feasibility_status: dict`, `results: list[PaperEvaluationResult]`, `started_at`, `completed_at` |

| Function | Purpose |
|----------|---------|
| `evaluate_single_paper(doc, manifests_dir, artifact_store, ...)` | adapt → topology → classify → feasibility → [translate] |
| `evaluate_batch(documents, manifests_dir, artifact_store, ...)` | Iterate, aggregate, per-paper ledger logging |
| `_write_ledger_entry(result, ledger_path)` | Append JSONL entry |

**evaluate_single_paper pipeline:**
1. `adapt_source_document(doc)` → AdaptationResult
2. `analyze_topology(summary)` → TopologyChange
3. Initialize `ArtifactRegistry`, `register_seed_artifact()`
4. `classify(summary, topology, [], registry)` → ClassificationResult
5. `assess_feasibility(summary, classification, manifests_dir)` → FeasibilityResult
6. Catch exceptions → record in `error` field

**Tests** `tests/test_integration/test_batch_pipeline.py` — 8 tests:
1. Single paper → PaperEvaluationResult with non-None fields
2. Invalid document → result.error set
3. Valid document → has innovation_type and feasibility_status
4. 3 documents → summary.total_papers=3
5. 3 different papers → by_innovation_type populated
6. Ledger path → JSONL file has correct line count
7. [valid, invalid, valid] → successful=2, failed=1
8. _write_ledger_entry appends valid JSON line

---

## WU 6.3: Manifest Freshness Check

**Create** `research_engineer/integration/manifest_freshness.py`

| Model | Key Fields |
|-------|-----------|
| `ManifestFreshnessResult` | `repo_name`, `manifest_path`, `generated_at: datetime \| None`, `age_days: float`, `is_stale: bool`, `warning: str \| None` |
| `FreshnessReport` | `manifests_checked`, `stale_count`, `fresh_count`, `missing_timestamp_count`, `threshold_days`, `results: list`; computed `all_fresh: bool` |

| Function | Purpose |
|----------|---------|
| `check_manifest_freshness(yaml_path, threshold_days=7.0, reference_time=None)` | Check single manifest |
| `check_all_manifests_freshness(manifests_dir, threshold_days=7.0, reference_time=None)` | Check all YAML files in directory |

**Logic:** Load YAML, parse `generated_at` via `datetime.fromisoformat()` (Python 3.11+ handles `Z` suffix), compute age, compare to threshold.

**Tests** `tests/test_integration/test_manifest_freshness.py` — 5 tests:
1. Fresh manifest (1 day ago) → is_stale=False
2. Stale manifest (10 days ago) → is_stale=True, warning set
3. Missing generated_at → warning about missing timestamp
4. All fresh directory → stale_count=0, all_fresh=True
5. Mixed freshness → correct counts, all_fresh=False

---

## WU 6.4: End-to-End Integration Tests

**Create** `tests/test_integration/test_end_to_end.py` — 5 tests:
1. arXiv SourceDocument → full pipeline → ClassificationResult (uses real clearinghouse manifests)
2. USPTO SourceDocument → adapt → classify → ClassificationResult
3. Freshness check on real manifests + evaluate paper
4. No agent-factors import errors during pipeline execution
5. 3 SourceDocuments → evaluate_batch → BatchEvaluationSummary with 3 results

---

## Conftest Fixtures (append to `tests/conftest.py`)

| Fixture | Returns |
|---------|---------|
| `tmp_integration_dir(tmp_path)` | Temp directory for integration data |
| `sample_source_document_arxiv()` | Synthetic arXiv SourceDocument (learned sparse, 4 blocks: abstract + method + results + limitations) |
| `sample_source_document_patent()` | Synthetic USPTO SourceDocument (RRF weights, 2 blocks: abstract + claim) |
| `sample_source_document_minimal()` | Empty content_blocks (edge case) |
| `sample_source_documents_batch(...)` | List of 3 SourceDocuments |

---

## pyproject.toml Changes

Add `prior-art-retrieval` to optional deps:

```toml
[project.optional-dependencies]
graph = ["networkx>=3.0"]
integration = ["prior-art-retrieval"]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "prior-art-retrieval",
]
```

**Setup:** `pip install -e "../prior-art-retrieval" && pip install -e ".[dev]"`

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/integration/__init__.py` | all |
| Create | `research_engineer/integration/adapter.py` | 6.1 |
| Create | `research_engineer/integration/batch_pipeline.py` | 6.2 |
| Create | `research_engineer/integration/manifest_freshness.py` | 6.3 |
| Create | `tests/test_integration/test_adapter.py` | 6.1 |
| Create | `tests/test_integration/test_batch_pipeline.py` | 6.2 |
| Create | `tests/test_integration/test_manifest_freshness.py` | 6.3 |
| Create | `tests/test_integration/test_end_to_end.py` | 6.4 |
| Modify | `pyproject.toml` | setup |
| Modify | `tests/conftest.py` (append 5 fixtures) | all |

**Total new tests: 27** (within blueprint estimate of 25-30)
**Running total: 316 + 27 = ~343 tests**

---

## Verification

```bash
pip install -e "../prior-art-retrieval" && pip install -e ".[dev]"
python3 -m pytest tests/test_integration/ -v        # all ~27 new tests pass
python3 -m pytest tests/ -v                          # all ~343 tests pass
python3 -c "from research_engineer.integration import adapt_source_document, evaluate_batch, check_all_manifests_freshness"
```
