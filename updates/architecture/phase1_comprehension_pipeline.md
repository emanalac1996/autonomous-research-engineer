# Phase 1 Architecture: Paper Comprehension Pipeline

**Date:** 2026-02-27
**Status:** Implemented
**Package:** `research_engineer.comprehension`

---

## Overview

The comprehension pipeline is Stage 1 of the autonomous research engineer.
It transforms plaintext research papers into structured `ComprehensionSummary`
objects that feed into the classifier (Stage 2), feasibility gate (Stage 3),
and translator (Stage 4).

```
plaintext paper
    │
    ▼
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  parser.py   │────▶│  topology.py     │     │  vocabulary.py      │
│  parse_paper │     │  analyze_topology│     │  build_vocabulary_  │
│              │     │                  │     │  mapping            │
└──────┬───────┘     └──────────────────┘     └─────────────────────┘
       │                                              │
       ▼                                              ▼
ComprehensionSummary                         VocabularyMapping
  .title                                       .pattern_matches
  .transformation_proposed                     .manifest_matches
  .claims[]                                    .unmapped_terms
  .sections[]
  .paper_terms[]
  .mathematical_core
  .limitations[]
```

## Data Models (schema.py)

All models are Pydantic v2 BaseModel.

### ComprehensionSummary

Primary output of Stage 1. Contains:
- `title` — paper title for identification
- `transformation_proposed` — core change the paper proposes (required, non-empty)
- `inputs_required` / `outputs_produced` — method I/O from method section
- `claims[]` — quantitative/qualitative claims with metrics
- `limitations[]` — extracted limitation statements
- `mathematical_core` — formulation, complexity, assumptions
- `sections[]` — raw extracted sections for traceability
- `paper_terms[]` — technical terms for vocabulary mapping

### Supporting Models

- `PaperSection` — typed section (SectionType enum + heading + content)
- `PaperClaim` — claim_text + optional metric_name, metric_value, baseline_comparison, dataset
- `MathCore` — formulation, complexity, assumptions

## Parser (parser.py)

Heuristic/regex-based extraction. No LLM calls.

### Section Extraction

Regex patterns match section headings at line start:
- Abstract, Method/Methods/Methodology/Approach, Results/Experiments/Evaluation, Limitations/Discussion
- Handles both standalone headings (`Abstract:`) and inline headings (`Abstract: We propose...`)
- Title extracted from `Title:` prefix or first non-blank line

### Claim Extraction

Scans results + abstract sections for quantitative patterns:
- `achieves X of VALUE` / `MRR@10 of VALUE`
- `improves by VALUE%` / `+VALUE%`
- Baseline via `compared to ... VALUE` / `baseline of VALUE`
- Dataset via `on/across DATASET benchmark/dataset`

### Term Extraction

Two-strategy approach:
1. Known multi-word terms matched via case-insensitive substring (e.g., "sparse retrieval", "knowledge graph")
2. Known acronyms matched case-sensitively (e.g., "BM25", "SPLADE", "FAISS")

## Topology Analyzer (topology.py)

Keyword-based detection of pipeline topology changes from ComprehensionSummary fields.

### Classification Priority

| Priority | TopologyChangeType | Trigger Keywords |
|----------|-------------------|------------------|
| 1 | stage_addition | "new stage", "introduce", "intermediate representation" |
| 2 | flow_restructuring | "restructure", "reorder", "new data flow" |
| 3 | stage_removal | "remove the", "eliminate", "bypass" |
| 4 | component_swap | "replace", "swap", "substitute" |
| 5 | none | "parameter", "tune", "adjust", "no architectural changes" |

### Output

`TopologyChange` with:
- `change_type` — one of 5 enum values
- `affected_stages` — matched against known stage names (retrieval, generation, reranking, etc.)
- `confidence` — `min(keyword_count / 3, 1.0)`
- `evidence` — list of matched keywords

## Vocabulary Mapping (vocabulary.py)

Maps paper terms to metis-platform concepts via two channels:

### Pattern Library Matching

Imports `match_problem()` from `clearinghouse/scripts/match_problem.py` with scoped
sys.path insertion. Calls it per-term with default threshold (0.05) and top_n (3).
Returns `PatternMatch` objects with pattern_id, score, formal_class.

### Manifest Matching

Loads all `clearinghouse/manifests/*.yaml` files. For each term, searches
function names, class names, docstrings, and module paths via case-insensitive
substring matching. Returns `ManifestMatch` objects with repo_name, function/class
name, module_path.

### Output

`VocabularyMapping` with:
- `pattern_matches[]` — terms linked to Pattern Library pattern IDs
- `manifest_matches[]` — terms linked to manifest function/class entries
- `unmapped_terms[]` — terms with no matches in either channel

## Downstream Consumers

| Consumer | What It Uses |
|----------|-------------|
| Stage 2 (Classifier) | `ComprehensionSummary.transformation_proposed`, `TopologyChange.change_type` |
| Stage 3 (Feasibility) | `VocabularyMapping.manifest_matches`, `ComprehensionSummary.inputs_required` |
| Stage 4 (Translator) | Full `ComprehensionSummary`, `VocabularyMapping`, `TopologyChange` |
