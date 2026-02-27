# Phase 4: Blueprint Translator with Historical Change Patterns — Implementation Plan

## Context

Phases 0-2 are complete (157 tests). Phase 4 builds the blueprint translator that consumes Phase 1's `ComprehensionSummary` + Phase 2's `ClassificationResult` and produces ADR-005 WU-defined blueprints using agent-factors DAG models. Phase 4 runs in parallel with Phase 3 (they share Phase 2 output but do not depend on each other). All modules are pure Python + Pydantic v2. No LLM calls. Blueprint generation is rule-based per innovation type.

Key imports from agent-factors: `Blueprint`, `Phase`, `WorkingUnit`, `DeferredItem`, `BlueprintMetadata`, `BlueprintStatus`, `WUStatus`, `validate_dag`, `DAGValidationReport`, `parse_blueprint`. Optional (requires networkx): `critical_path`, `parallel_groups`, `phase_summary`.

---

## Implementation Order

```
WU 4.1 (manifest_targeter.py)  ──→  WU 4.2 (change_patterns.py)  ──→  conftest fixtures
                                                                   ──→  WU 4.3 (wu_decomposer.py)
                                                                           ──→  WU 4.4 (translator.py)
                                                                                   ──→  WU 4.5 (serializer.py)
                                                                                           ──→  WU 4.6 (evaluate_paper.py CLI update)
                                                                                           ──→  __init__.py update
```

---

## WU 4.1: Manifest Targeter

**Create** `research_engineer/translator/manifest_targeter.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `FileTarget` (BaseModel) | `source_file: str`, `repo_name: str`, `reason: str` | Single file target |
| `FileTargeting` (BaseModel) | `files_created: list[FileTarget]`, `files_modified: list[FileTarget]`, `target_repos: list[str]` | Complete targeting result |
| `identify_targets(summary, classification, manifests_dir) -> FileTargeting` | — | Primary entry point |

Algorithm:
1. Load all YAML manifests from `manifests_dir`
2. Scan `functions[].source_file` and `classes[].source_file` for matches against `summary.paper_terms + inputs_required + outputs_produced` (case-insensitive substring against name, docstring, module_path)
3. Matched `source_file` entries → `files_modified`
4. Innovation-type-specific `files_created`:
   - `parameter_tuning`: empty (config changes only)
   - `modular_swap`: new component module
   - `pipeline_restructuring`: new stage module(s)
   - `architectural_innovation`: new primitive modules + test files
5. Deduplicate by `source_file`; `target_repos` = unique repo names

Expected results:

| Fixture | files_modified (count) | files_created (count) |
|---------|----------------------|---------------------|
| parameter_tuning | ≥ 1 | 0 |
| modular_swap | ≥ 1 | ≥ 1 |
| architectural | ≥ 1 | ≥ 2 |

**Create** `tests/test_translator/test_manifest_targeter.py` — 9 tests:
- `FileTarget` construction and JSON round-trip
- `FileTargeting` validates non-empty (at least one target)
- `identify_targets` returns `FileTargeting` for parameter_tuning against real manifests
- `identify_targets` returns non-empty `files_modified` for modular_swap
- `identify_targets` returns non-empty `files_created` for architectural
- `target_repos` populated from manifest repo names
- Handles missing manifests directory gracefully
- Handles empty manifests directory gracefully
- All `source_file` entries are non-empty strings

---

## WU 4.2: Historical Change Pattern Analyzer

**Create** `research_engineer/translator/change_patterns.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `ChangePatternStats` (BaseModel) | `avg_wu_count: float`, `avg_test_ratio: float`, `sample_count: int`, `common_phase_count: int` | Stats for one group |
| `ChangePatternReport` (BaseModel) | `by_meta_category: dict[str, ChangePatternStats]`, `by_innovation_type: dict[str, ChangePatternStats]`, `total_entries: int`, `entries_with_blueprint_ref: int` | Aggregate report |
| `mine_ledger(ledger_path) -> ChangePatternReport` | — | Primary entry point |
| `DEFAULT_PATTERN_STATS` (constant dict) | — | Fallback stats per innovation type |

Algorithm:
1. Read JSONL, filter entries with `blueprint_ref` or `test_count`
2. Group by `meta_category` and infer innovation type from keywords
3. Compute `avg_wu_count`, `avg_test_ratio`, `common_phase_count` per group
4. If < 3 entries with blueprint_ref, merge with `DEFAULT_PATTERN_STATS`

Default stats:

| Innovation Type | avg_wu_count | avg_test_ratio |
|-----------------|-------------|---------------|
| parameter_tuning | 2.0 | 4.0 |
| modular_swap | 4.0 | 3.5 |
| pipeline_restructuring | 8.0 | 3.0 |
| architectural_innovation | 14.0 | 2.5 |

**Create** `tests/test_translator/test_change_patterns.py` — 9 tests:
- `ChangePatternStats` construction and JSON round-trip
- `ChangePatternReport` construction with empty dicts
- `mine_ledger` on real ledger returns `total_entries > 0`
- `mine_ledger` finds entries with `blueprint_ref`
- `mine_ledger` produces non-zero `entries_with_blueprint_ref`
- `mine_ledger` computes `avg_test_ratio > 0` for at least one group
- `mine_ledger` on empty file returns report with defaults
- `_infer_innovation_type` returns None for unrecognizable entries
- `DEFAULT_PATTERN_STATS` has all 4 innovation types

---

## Conftest Fixtures for Phase 4

**Modify** `tests/conftest.py` — append 8 new fixtures:

| Fixture | Returns |
|---------|---------|
| `sample_classification_parameter_tuning(...)` | `ClassificationResult` via `classify()` on parameter_tuning fixtures |
| `sample_classification_modular_swap(...)` | `ClassificationResult` via `classify()` on modular_swap fixtures |
| `sample_classification_architectural(...)` | `ClassificationResult` via `classify()` on architectural fixtures |
| `sample_classification_pipeline_restructuring(...)` | `ClassificationResult` with flow_restructuring topology |
| `sample_file_targeting_modular_swap(...)` | `FileTargeting` from `identify_targets()` for modular swap |
| `sample_change_pattern_report(clearinghouse_ledger)` | `ChangePatternReport` from `mine_ledger()` |
| `tmp_blueprint_output_dir(tmp_path)` | Temporary directory for blueprint output |
| `sample_topology_flow_restructuring()` | `TopologyChange(change_type=flow_restructuring)` |

---

## WU 4.3: WU Decomposer

**Create** `research_engineer/translator/wu_decomposer.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `DecompositionConfig` (BaseModel) | `wu_count_ranges: dict[str, tuple[int, int]]`, `default_effort: str`, `test_ratio: float` | Configurable parameters |
| `DEFAULT_WU_RANGES` (constant) | `{"parameter_tuning": (1, 3), "modular_swap": (3, 5), "pipeline_restructuring": (5, 12), "architectural_innovation": (8, 20)}` | — |
| `decompose(summary, classification, file_targeting, change_patterns, phase_id, config) -> list[WorkingUnit]` | — | Primary entry point |
| `validate_decomposition(wus, innovation_type) -> bool` | — | WU count in range + DAG valid |

Decomposition templates:

**parameter_tuning (1-3 WUs):**
- {phase}.1: Identify config parameter
- {phase}.2: Apply change and validate
- {phase}.3 (optional): Regression test for parameter boundary

**modular_swap (3-5 WUs):**
- {phase}.1: Study interface contract
- {phase}.2: Implement replacement component
- {phase}.3: Create adapter if interface mismatch (optional)
- {phase}.4: Integration test
- {phase}.5: Regression test

**pipeline_restructuring (5-12 WUs):**
- {phase}.1: Analyze current topology
- {phase}.2: Design new topology
- {phase}.3-N: One WU per new/modified stage (capped at 6)
- {phase}.(N+1): Update contracts
- {phase}.(N+2): Integration test
- {phase}.(N+3): Regression test

**architectural_innovation (8-20 WUs):**
- {phase}.1: Define new primitive interfaces
- {phase}.2: Scaffold new module structure
- {phase}.3-M: One WU per new primitive (capped at 8)
- {phase}.(M+1): Build integration layer
- {phase}.(M+2): Pipeline integration
- {phase}.(M+3): Test framework
- {phase}.(M+4): End-to-end validation
- {phase}.(M+5): Documentation and acceptance

Each WU uses `agent_factors.dag.schema.WorkingUnit` model. `validate_decomposition` wraps `validate_dag()`.

**Create** `tests/test_translator/test_wu_decomposer.py` — 12 tests:
- `DecompositionConfig` construction and defaults
- `decompose` returns 1-3 WUs for parameter_tuning
- `decompose` returns 3-5 WUs for modular_swap
- `decompose` returns 5-12 WUs for pipeline_restructuring
- `decompose` returns 8-20 WUs for architectural_innovation
- All WU IDs match valid format
- All decompositions pass `validate_dag()` (acyclic, complete, reachable)
- First WU has empty `depends_on`, last WU reachable from first
- `files_created`/`files_modified` populated on at least one WU
- `acceptance_criteria` non-empty on all WUs
- `_adjust_wu_count` with historical data nudges count
- `validate_decomposition` returns False for circular dependency

---

## WU 4.4: Blueprint Translator (Orchestrator)

**Create** `research_engineer/translator/translator.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `TranslationInput` (BaseModel) | `summary: ComprehensionSummary`, `classification: ClassificationResult`, `manifests_dir: Path \| None`, `ledger_path: Path \| None`, `blueprint_name: str \| None`, `meta_category: str \| None`, `date: str \| None` | Bundled input |
| `TranslationResult` (BaseModel) | `blueprint: Blueprint`, `validation_report: DAGValidationReport`, `file_targeting: FileTargeting`, `change_patterns: ChangePatternReport`, `test_estimate_low: int`, `test_estimate_high: int` | Complete output |
| `translate(input: TranslationInput) -> TranslationResult` | — | Primary orchestrator |

Algorithm:
1. `identify_targets()` → FileTargeting (or empty if no manifests_dir)
2. `mine_ledger()` → ChangePatternReport (or defaults)
3. `decompose()` → list[WorkingUnit]
4. Build `Phase` with WUs and goal
5. Build `BlueprintMetadata` (status=planned, date, meta_category)
6. Build `DeferredItem` list (RE-D{N} for limitations implying infra deps)
7. Assemble `Blueprint`
8. `validate_dag(blueprint)` → DAGValidationReport
9. Compute test estimates: `(len(wus) * ratio_low, len(wus) * ratio_high)`
10. Return `TranslationResult`

Deferred item rules:
- `pipeline_restructuring`/`architectural_innovation` with multi-repo targeting → RE-D{N}
- Each limitation with "model", "requires", "not currently" → deferred item
- IDs: `RE-D{N}` incrementing from 1

**Create** `tests/test_translator/test_translator.py` — 10 tests:
- `TranslationInput` construction minimal
- `TranslationResult` has all required fields
- `translate` produces valid Blueprint for parameter_tuning (with manifests_dir)
- `translate` produces valid Blueprint for modular_swap
- `translate` produces valid Blueprint for architectural (with ledger)
- `translate` produces valid Blueprint for pipeline_restructuring
- All blueprints pass `validate_dag()` (overall_passed=True)
- Blueprint `name` non-empty, contains innovation type indicator
- Blueprint `metadata.status` is `BlueprintStatus.planned`
- Test estimates: positive integers, low ≤ high

---

## WU 4.5: Blueprint Serialization

**Create** `research_engineer/translator/serializer.py`

| Function | Signature | Notes |
|----------|-----------|-------|
| `serialize_blueprint(result) -> str` | `result: TranslationResult` | Render ADR-005 Tier 1 markdown |
| `write_blueprint(result, output_dir) -> Path` | — | Write to `{date}_{name}_blueprint.md` |

Output format (ADR-005 Tier 1):
```markdown
# {blueprint.name}

**Date:** {metadata.date}
**Status:** {metadata.status.value}
**Meta-category:** {metadata.meta_category}

---

## 1. Phase {phase.id}: {phase.goal}

**Goal:** {phase.goal}

| Working Unit | Description | Depends On | Acceptance Criteria |
|---|---|---|---|
| Working Unit {wu.id} | {wu.description} | {depends} | {wu.acceptance_criteria} |

**Output:** {phase.output}
**Test estimate:** {test_low}-{test_high} tests

## Deferred Items

| ID | Item | Extension point | Trigger |
|---|---|---|---|
| {item.id} | {item.item} | {item.extension_point} | {item.trigger} |
```

Round-trip: output must be parseable by `agent_factors.dag.parser.parse_blueprint()` and pass `validate_dag()`.

**Create** `tests/test_translator/test_serializer.py` — 8 tests:
- `serialize_blueprint` returns non-empty string starting with "# "
- Output contains "**Date:**" and "**Status:**"
- Output contains WU table with "| Working Unit |" header
- Output contains "Working Unit {id}" for each WU
- Depends-on: "---" for empty, "Working Unit X.Y" for single
- Round-trip: serialize → parse_blueprint → validate_dag passes (parameter_tuning)
- Round-trip: serialize → parse_blueprint → validate_dag passes (architectural)
- `write_blueprint` creates file at expected path

---

## WU 4.6: CLI Entry Point

**Modify** `scripts/evaluate_paper.py` — add `--translate` pipeline:

```
python3 scripts/evaluate_paper.py --translate --input summary.json --output-dir plans/
python3 scripts/evaluate_paper.py --translate --input summary.json --manifests-dir ... --ledger ...
```

New flags: `--translate`, `--output-dir`, `--manifests-dir`, `--ledger`

When `--translate`:
1. Read summary, analyze topology, classify (existing)
2. Build `TranslationInput`
3. `translate()` → `TranslationResult`
4. `write_blueprint()` → output file
5. Print JSON with blueprint_path, wu_count, validation_passed
6. Exit 0 on success, 1 on error

`--classify-only` behavior preserved (backwards compatible).

**Create** `tests/test_translator/test_cli.py` — 7 tests:
- Script exists, importable, has `main()`
- `--translate` flag accepted
- End-to-end: parameter_tuning → blueprint file created
- End-to-end: modular_swap → valid blueprint
- Written file contains ADR-005 markers
- Exit code 0 on success with `--translate`
- `--classify-only` still works (regression)

---

## Final: Update `__init__.py`

**Modify** `research_engineer/translator/__init__.py` — public exports:
- `ChangePatternReport`, `ChangePatternStats`, `mine_ledger`
- `FileTarget`, `FileTargeting`, `identify_targets`
- `serialize_blueprint`, `write_blueprint`
- `TranslationInput`, `TranslationResult`, `translate`
- `DecompositionConfig`, `decompose`, `validate_decomposition`

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/translator/manifest_targeter.py` | 4.1 |
| Create | `research_engineer/translator/change_patterns.py` | 4.2 |
| Create | `research_engineer/translator/wu_decomposer.py` | 4.3 |
| Create | `research_engineer/translator/translator.py` | 4.4 |
| Create | `research_engineer/translator/serializer.py` | 4.5 |
| Modify | `scripts/evaluate_paper.py` (add --translate) | 4.6 |
| Modify | `tests/conftest.py` (append 8 fixtures) | all |
| Modify | `research_engineer/translator/__init__.py` (add exports) | all |
| Create | `tests/test_translator/test_manifest_targeter.py` | 4.1 |
| Create | `tests/test_translator/test_change_patterns.py` | 4.2 |
| Create | `tests/test_translator/test_wu_decomposer.py` | 4.3 |
| Create | `tests/test_translator/test_translator.py` | 4.4 |
| Create | `tests/test_translator/test_serializer.py` | 4.5 |
| Create | `tests/test_translator/test_cli.py` | 4.6 |

**Total new tests: ~55** (within blueprint estimate of 40-50, slightly above)
**Running total after Phase 4: 157 + 55 = ~212 tests**

---

## Verification

```bash
python3 -m pytest tests/test_translator/ -v        # all ~55 new tests pass
python3 -m pytest tests/ -v                         # all ~212 tests pass (157 + 55)
python3 -c "from research_engineer.translator import translate, decompose, serialize_blueprint, FileTargeting, ChangePatternReport"
python3 scripts/evaluate_paper.py --classify-only --input /dev/null 2>&1 | head -1   # regression
```
