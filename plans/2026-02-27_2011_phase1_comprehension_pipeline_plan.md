# Phase 1: Paper Comprehension Pipeline — Implementation Plan

## Context

Phase 0 is complete (55 tests, repo scaffolded with all subpackages). Phase 1 builds the paper comprehension pipeline — the foundation that all downstream stages (classifier, feasibility gate, translator) consume. The five `research_engineer/comprehension/` modules (schema, parser, topology, vocabulary) plus test fixtures need to be implemented.

All modules are pure Python + Pydantic v2. No LLM calls. Parsing is regex/heuristic-based.

---

## Implementation Order

```
WU 1.1 (schema.py)  ──→  WU 1.4 (fixtures in conftest.py)  ──→  WU 1.2 (parser.py)
                                                              ──→  WU 1.3 (topology.py)  (parallel with 1.2)
                                                              ──→  WU 1.5 (vocabulary.py) (after 1.2)
                                                              ──→  __init__.py update (last)
```

---

## WU 1.1: Comprehension Schema

**Create** `research_engineer/comprehension/schema.py`

Pydantic v2 models:

| Model | Key Fields | Validators |
|-------|-----------|------------|
| `SectionType(str, Enum)` | `title`, `abstract`, `method`, `results`, `limitations`, `other` | — |
| `PaperSection` | `section_type: SectionType`, `heading: str`, `content: str` | content not empty |
| `PaperClaim` | `claim_text: str`, `metric_name: str \| None`, `metric_value: float \| None`, `baseline_comparison: float \| None`, `dataset: str \| None` | claim_text not empty, metric values finite |
| `MathCore` | `formulation: str \| None`, `complexity: str \| None`, `assumptions: list[str]` | — |
| `ComprehensionSummary` | `title: str`, `transformation_proposed: str`, `inputs_required: list[str]`, `outputs_produced: list[str]`, `claims: list[PaperClaim]`, `limitations: list[str]`, `mathematical_core: MathCore`, `sections: list[PaperSection]`, `paper_terms: list[str]` | transformation_proposed not empty |

Additional fields beyond blueprint spec:
- `title` — needed for logging/ledger identification
- `sections` — preserves raw extracted text for traceability (decidable verification: claims spot-checkable against source)
- `paper_terms` — extracted technical terms consumed by WU 1.5 vocabulary mapping

**Create** `tests/test_comprehension/test_schema.py` — 10 tests:
- Minimal construction (defaults work), full construction, JSON round-trip
- Rejects empty `transformation_proposed`, rejects empty `claim_text`
- Optional metrics on PaperClaim, MathCore defaults
- PaperSection valid/invalid

---

## WU 1.4: Test Fixtures

**Modify** `tests/conftest.py` — append 3 new fixtures after line 177:

| Fixture | Innovation Type | Source Text Fixture |
|---------|----------------|---------------------|
| `sample_parameter_tuning_summary()` | parameter_tuning | `sample_parameter_tuning_text` (RRF weight k=42) |
| `sample_modular_swap_summary()` | modular_swap | `sample_paper_text` (BM25→SPLADE) |
| `sample_architectural_summary()` | architectural_innovation | `sample_architectural_text` (knowledge graph stage) |

Each returns a `ComprehensionSummary` with realistic field values matching the existing text fixtures.

**Create** `tests/test_comprehension/test_fixtures.py` — 5 tests:
- Each fixture loads as valid ComprehensionSummary
- All three have distinct `transformation_proposed`
- All three have at least one claim with `metric_name`

---

## WU 1.2: Paper Parser

**Create** `research_engineer/comprehension/parser.py`

Primary entry point: `parse_paper(text: str) -> ComprehensionSummary`

Internal functions:

| Function | Strategy |
|----------|----------|
| `extract_sections(text)` | Regex on `^(Title\|Abstract\|Method\|Results\|Limitations)\s*[:.]?` (case-insensitive). Also matches synonyms: "Methods"/"Methodology"/"Approach" for method, "Experiments"/"Evaluation" for results, "Discussion" for limitations. Text between headings → `PaperSection`. |
| `extract_title(text)` | First `Title:` line content, or first non-blank line |
| `extract_claims(sections)` | Scan results + abstract for patterns: `achieves X of Y`, `+N% over`, `improves by N%`, `compared to baseline of Y`. Extract metric_name from known metric list (MRR@10, F1, accuracy, etc.), metric_value, baseline_comparison. |
| `extract_math_core(sections)` | Detect LaTeX (`$...$`, `\frac`, `\sum`), Big-O (`O(...)`), formulation markers ("Given:", "where:", "subject to:"). Extract surrounding text as formulation. Complexity from `O(...)` patterns. Assumptions from "assuming"/"assumes" sentences. |
| `extract_limitations(sections)` | Split limitations section on sentence boundaries, return as list. |
| `extract_paper_terms(sections)` | Match known technical terms (`_KNOWN_TERMS` set) against abstract+method text (case-insensitive substring). Also detect ALL-CAPS acronyms. |
| `extract_transformation(sections)` | Find sentences with "propose", "introduce", "replace", "swap", "adjust", "optimize" in abstract. Return the matching sentence. |
| `extract_inputs_outputs(sections)` | Scan method section for "requires"/"uses"/"takes" (inputs) and "produces"/"outputs"/"generates" (outputs). |

**Create** `tests/test_comprehension/test_parser.py` — 12 tests:
- `parse_paper` on all 3 text fixtures produces valid ComprehensionSummary
- Section count >= 4 for each paper
- Title extraction matches expected
- Claims extraction: MRR@10=0.847 from modular swap, 2.3% from parameter tuning
- Transformation mentions expected terms per paper
- Limitations non-empty, MathCore.formulation not None, paper_terms include domain terms

---

## WU 1.3: Topology Analyzer

**Create** `research_engineer/comprehension/topology.py`

Models:
- `TopologyChangeType(str, Enum)`: `none`, `component_swap`, `stage_addition`, `stage_removal`, `flow_restructuring`
- `TopologyChange(BaseModel)`: `change_type`, `affected_stages: list[str]`, `confidence: float` (0-1), `evidence: list[str]`

Primary entry point: `analyze_topology(summary: ComprehensionSummary) -> TopologyChange`

Detection strategy — keyword matching on `transformation_proposed` + abstract + method content:

| Priority | Change Type | Keywords |
|----------|-------------|----------|
| 1 | `stage_addition` | "new stage", "introduce", "intermediate representation", "new module", "novel pipeline" |
| 2 | `flow_restructuring` | "restructure", "reorder", "rearrange", "new data flow", "different routing" |
| 3 | `stage_removal` | "remove stage", "eliminate stage", "bypass" |
| 4 | `component_swap` | "replace", "swap", "substitute", "instead of", "drop-in replacement" |
| 5 | `none` | "no architectural changes", "parameter", "tune", "adjust", "grid search" |

Confidence = `min(matched_keyword_count / 3, 1.0)`. Affected stages extracted from `inputs_required`/`outputs_produced` matching known stage names (retrieval, generation, reranking, indexing, etc.).

**Create** `tests/test_comprehension/test_topology.py` — 10 tests:
- Parameter tuning fixture → `none`
- Modular swap fixture → `component_swap`
- Architectural fixture → `stage_addition`
- Synthetic "remove the reranking stage" → `stage_removal`
- Synthetic "restructure the pipeline flow" → `flow_restructuring`
- Evidence non-empty, confidence in [0,1], affected_stages populated for non-none
- JSON round-trip, model rejects confidence outside [0,1]

---

## WU 1.5: Vocabulary Mapping

**Create** `research_engineer/comprehension/vocabulary.py`

Models:
- `PatternMatch`: `paper_term`, `pattern_id`, `score`, `formal_class`, `matched_phrases: list[str]`
- `ManifestMatch`: `paper_term`, `repo_name`, `function_name: str | None`, `class_name: str | None`, `module_path: str`
- `VocabularyMapping`: `paper_terms: list[str]`, `pattern_matches: list[PatternMatch]`, `manifest_matches: list[ManifestMatch]`, `unmapped_terms: list[str]`

Primary entry point: `build_vocabulary_mapping(paper_terms: list[str], clearinghouse_root: Path) -> VocabularyMapping`

Internal functions:

| Function | Strategy |
|----------|----------|
| `load_patterns(algorithms_dir)` | Glob `patterns/**/*.yaml`, `yaml.safe_load`, filter by `pattern_id` key present |
| `load_domains(algorithms_dir)` | Glob `domains/*.yaml`, `yaml.safe_load`, filter by `domain` key present |
| `build_keyword_index(patterns)` | Extract tokens from `domain_signatures[].phrases` → `{keyword: [pattern_ids]}` |
| `match_terms_to_patterns(terms, algorithms_dir)` | Import `match_problem` from clearinghouse scripts (scoped `sys.path` insert) and call with pre-loaded data. For each term, call `match_problem(query=term, patterns=..., domains=..., keyword_index=..., top_n=3, threshold=0.05)`. Convert `MatchResult` → `PatternMatch`. |
| `match_terms_to_manifests(terms, manifests_dir)` | Load each `*.yaml` manifest. For each term, case-insensitive substring search in function `name`, `docstring`, class `name`, `module_path`. Matches → `ManifestMatch`. |

Design choice: import `match_problem()` directly with scoped sys.path rather than re-implementing scoring. The function already accepts pre-loaded `patterns`/`domains`/`keyword_index` params (confirmed at `match_problem.py:310-317`).

**Create** `tests/test_comprehension/test_vocabulary.py` — 8 tests:
- VocabularyMapping model valid + JSON round-trip
- "sparse retrieval" → at least one PatternMatch
- "BM25" → at least one ManifestMatch
- Fabricated term ("quantum_entanglement_retrieval") → in `unmapped_terms`
- Full mapping from modular swap fixture terms → non-empty results
- Parameter tuning terms → "reciprocal rank fusion" found in patterns
- All PatternMatch scores > 0.0

---

## Final: Update `__init__.py`

**Modify** `research_engineer/comprehension/__init__.py` — add public exports:

```python
from research_engineer.comprehension.schema import (
    ComprehensionSummary, MathCore, PaperClaim, PaperSection, SectionType,
)
from research_engineer.comprehension.parser import parse_paper
from research_engineer.comprehension.topology import (
    TopologyChange, TopologyChangeType, analyze_topology,
)
from research_engineer.comprehension.vocabulary import (
    VocabularyMapping, build_vocabulary_mapping,
)
```

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/comprehension/schema.py` | 1.1 |
| Create | `research_engineer/comprehension/parser.py` | 1.2 |
| Create | `research_engineer/comprehension/topology.py` | 1.3 |
| Create | `research_engineer/comprehension/vocabulary.py` | 1.5 |
| Modify | `tests/conftest.py` (append 3 fixtures) | 1.4 |
| Modify | `research_engineer/comprehension/__init__.py` (add exports) | all |
| Create | `tests/test_comprehension/test_schema.py` | 1.1 |
| Create | `tests/test_comprehension/test_parser.py` | 1.2 |
| Create | `tests/test_comprehension/test_topology.py` | 1.3 |
| Create | `tests/test_comprehension/test_fixtures.py` | 1.4 |
| Create | `tests/test_comprehension/test_vocabulary.py` | 1.5 |

**Total new tests: 45** (within blueprint estimate of 35-45)

---

## Verification

After implementation, run:
```bash
python3 -m pytest tests/test_comprehension/ -v    # all 45 new tests pass
python3 -m pytest tests/ -v                        # all 100 tests pass (55 existing + 45 new)
python3 -c "from research_engineer.comprehension import parse_paper, analyze_topology, build_vocabulary_mapping"  # public API importable
```
