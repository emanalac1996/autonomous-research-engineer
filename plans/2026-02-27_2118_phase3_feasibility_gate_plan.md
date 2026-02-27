# Phase 3: Feasibility Gate with Codebase Dependency Graph — Implementation Plan

## Context

Phases 0-2 are complete (157 tests). Phase 3 builds the feasibility gate that takes Phase 1's `ComprehensionSummary` + Phase 2's `ClassificationResult` and assesses implementability against live codebase state. Phase 3 runs in parallel with Phase 4 (they share Phase 2 output but do not depend on each other). The gate performs manifest checking, dependency graph construction, blast radius analysis, and test coverage assessment, producing a `FeasibilityResult` with one of 4 statuses: `FEASIBLE`, `FEASIBLE_WITH_ADAPTATION`, `ESCALATE`, `NOT_FEASIBLE`. NetworkX (optional dependency, `[graph]` extra) is used for the codebase dependency graph.

---

## Implementation Order

```
WU 3.1 (manifest_checker.py)  ──→  WU 3.2 (dependency_graph.py)
                                        ──→  WU 3.3 (blast_radius.py)
                                                  ──→  WU 3.4 (test_coverage.py)
                                                            ──→  WU 3.5 (gate.py)
                                                                      ──→  WU 3.6 (CLI scripts)
                                                                      ──→  __init__.py update
```

---

## WU 3.1: Manifest Checker

**Create** `research_engineer/feasibility/manifest_checker.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `ManifestFunction` (BaseModel) | `name: str`, `module_path: str`, `parameters: list[dict]`, `return_type: str \| None`, `docstring: str \| None`, `source_file: str`, `line_number: int \| None` | Single function entry from manifest YAML |
| `ManifestClass` (BaseModel) | `name: str`, `module_path: str`, `bases: list[str]`, `methods: list[ManifestFunction]`, `docstring: str \| None`, `source_file: str` | Single class entry from manifest YAML |
| `RepositoryManifest` (BaseModel) | `repo_name: str`, `version: str`, `functions: list[ManifestFunction]`, `classes: list[ManifestClass]`, `module_tree: dict[str, list[str]]` | Full parsed manifest |
| `OperationMatch` (BaseModel) | `operation: str`, `repo_name: str`, `function_name: str \| None`, `class_name: str \| None`, `module_path: str`, `match_type: str` | `match_type`: `"exact_function"`, `"exact_class"`, `"docstring"`, `"module_path"` |
| `ManifestCheckResult` (BaseModel) | `matched_operations: list[OperationMatch]`, `unmatched_operations: list[str]`, `manifests_loaded: list[str]`, `coverage_ratio: float` | `coverage_ratio = len(matched) / max(len(matched)+len(unmatched), 1)` |
| `load_manifest(yaml_path: Path) -> RepositoryManifest` | — | Parse single manifest YAML |
| `load_all_manifests(manifests_dir: Path) -> list[RepositoryManifest]` | — | Glob `*.yaml`, load all, sorted by repo_name |
| `check_operations(operations: list[str], manifests: list[RepositoryManifest]) -> ManifestCheckResult` | — | Match operations against manifests: exact function name, exact class name, docstring substring, module_path substring. Case-insensitive. |

- Matching is case-insensitive. Operations come from `ComprehensionSummary.inputs_required + outputs_produced + paper_terms`.
- `ManifestFunction.parameters` is `list[dict]` to handle heterogeneous YAML entries.
- `coverage_ratio` has a `@field_validator` clamping to [0, 1].

**Create** `tests/test_feasibility/test_manifest_checker.py` — 10 tests:
- `RepositoryManifest` constructs from minimal data
- `RepositoryManifest` JSON round-trip
- `ManifestCheckResult` constructs with matched/unmatched
- `ManifestCheckResult.coverage_ratio` computed correctly (2/3 = 0.667)
- `load_manifest()` loads synthetic YAML from tmp_path
- `load_all_manifests()` returns empty list for missing dir
- `load_all_manifests()` loads real clearinghouse manifests (3 files)
- `check_operations()` matches "BM25" against multimodal-rag-core manifest
- `check_operations()` puts fabricated term in `unmatched_operations`
- `check_operations()` with empty operations returns empty matched and 0.0 ratio

---

## WU 3.2: Codebase Dependency Graph

**Create** `research_engineer/feasibility/dependency_graph.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `GraphNode` (BaseModel) | `node_id: str`, `node_type: str`, `repo_name: str`, `module_path: str`, `source_file: str \| None` | `node_type`: `"function"` or `"class"`. `node_id`: `"{repo_name}::{module_path}.{name}"` |
| `GraphEdge` (BaseModel) | `source: str`, `target: str`, `edge_type: str` | `edge_type`: `"contains"`, `"method_of"`, `"imports"` |
| `GraphStats` (BaseModel) | `node_count: int`, `edge_count: int`, `connected_components: int`, `is_dag: bool` | Summary statistics |
| `DependencyGraph` (class) | `graph: nx.DiGraph`, `nodes: dict[str, GraphNode]` | Wrapper with query methods |
| `DependencyGraph.build_from_manifests(manifests) -> DependencyGraph` | classmethod | Builds graph: module→function "contains", class→method "method_of", module→module "imports" (sibling modules share edges) |
| `DependencyGraph.downstream(node_id) -> set[str]` | — | `nx.descendants()` |
| `DependencyGraph.upstream(node_id) -> set[str]` | — | `nx.ancestors()` |
| `DependencyGraph.shortest_path(source, target) -> list[str] \| None` | — | `nx.shortest_path()` or None |
| `DependencyGraph.connected_component(node_id) -> set[str]` | — | `nx.node_connected_component()` on undirected view |
| `DependencyGraph.stats() -> GraphStats` | — | Node/edge count, components, is_dag |
| `build_dependency_graph(manifests_dir: Path) -> DependencyGraph` | — | Convenience: load_all_manifests then build_from_manifests |

- NetworkX import guarded: `try: import networkx except ImportError: raise ...`
- Node IDs: `"{repo_name}::{module_path}.{name}"` for functions/classes, `"{repo_name}::{module_path}"` for modules.
- Edge heuristic: sibling modules (same parent package) get bidirectional "imports" edges.
- Built purely from manifest data (no live filesystem access).

**Create** `tests/test_feasibility/test_dependency_graph.py` — 10 tests:
- `GraphNode` constructs with required fields
- `GraphStats` constructs and reports correct values
- `DependencyGraph()` creates empty graph (0 nodes, 0 edges)
- `build_from_manifests()` builds graph from synthetic manifest (4+ nodes)
- `build_from_manifests()` builds graph from real clearinghouse manifests (node_count > 50)
- `downstream()` on module node returns contained functions
- `upstream()` on function node returns containing module
- `shortest_path()` returns path between connected nodes, None for disconnected
- `connected_component()` returns nodes in same component
- `stats()` returns correct GraphStats

---

## WU 3.3: Blast Radius Analyzer

**Create** `research_engineer/feasibility/blast_radius.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `RiskLevel` (str, Enum) | `low`, `medium`, `high`, `critical` | Risk level from blast radius size |
| `BlastRadiusReport` (BaseModel) | `target_nodes: list[str]`, `affected_functions: list[str]`, `affected_tests: list[str]`, `affected_contracts: list[str]`, `total_affected: int` (computed_field), `risk_level: RiskLevel` | Full blast radius output |
| `compute_blast_radius(target_nodes, graph) -> BlastRadiusReport` | — | Union of `downstream()` for each target. Partition into functions/tests/contracts. |
| `_classify_risk(total_affected) -> RiskLevel` | — | `0-2: low`, `3-10: medium`, `11-30: high`, `>30: critical` |

- Test identification: node_id or module_path contains "test" (case-insensitive).
- Contract identification: node_id or module_path contains "contract".
- Unknown target node IDs are silently skipped.
- `total_affected` is a Pydantic `@computed_field`.

**Create** `tests/test_feasibility/test_blast_radius.py` — 8 tests:
- `RiskLevel` enum has 4 values
- `BlastRadiusReport` constructs, total_affected computed correctly
- `BlastRadiusReport` JSON round-trip
- `compute_blast_radius()` on leaf node: empty affected, risk=low
- `compute_blast_radius()` on hub node: non-empty affected_functions
- `compute_blast_radius()` identifies test nodes via "test" in node_id
- `compute_blast_radius()` identifies contract nodes via "contract" in node_id
- `_classify_risk()` correct for boundary values (0, 3, 11, 31)

---

## WU 3.4: Test Coverage Assessor

**Create** `research_engineer/feasibility/test_coverage.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `CoverageAssessment` (BaseModel) | `covered_functions: list[str]`, `uncovered_functions: list[str]`, `coverage_ratio: float`, `additional_tests_needed: int` | `coverage_ratio = len(covered) / max(len(covered)+len(uncovered), 1)`. `additional_tests_needed = len(uncovered)`. |
| `assess_test_coverage(affected_functions, graph) -> CoverageAssessment` | — | For each function, check if upstream/downstream contains test nodes. |

- "Test node" = node_id or module_path contains "test".
- Empty `affected_functions` → coverage_ratio=1.0, additional_tests_needed=0.
- `coverage_ratio` has `@field_validator` clamping to [0, 1].

**Create** `tests/test_feasibility/test_test_coverage.py` — 7 tests:
- `CoverageAssessment` constructs with all fields
- `CoverageAssessment` JSON round-trip
- `coverage_ratio` computed correctly (2 covered, 1 uncovered = 0.667)
- `assess_test_coverage()` returns 1.0 for functions with test neighbors
- `assess_test_coverage()` identifies uncovered functions
- `assess_test_coverage()` on empty list returns ratio 1.0, additional=0
- `additional_tests_needed` equals length of uncovered_functions

---

## WU 3.5: Feasibility Gate Orchestrator

**Create** `research_engineer/feasibility/gate.py`

| Model / Function | Key Fields / Signature | Notes |
|---|---|---|
| `FeasibilityStatus` (str, Enum) | `FEASIBLE`, `FEASIBLE_WITH_ADAPTATION`, `ESCALATE`, `NOT_FEASIBLE` | 4 gate outcomes |
| `FeasibilityResult` (BaseModel) | `status: FeasibilityStatus`, `innovation_type: InnovationType`, `manifest_check: ManifestCheckResult`, `blast_radius: BlastRadiusReport \| None`, `coverage: CoverageAssessment \| None`, `rationale: str`, `escalation_trigger: EscalationTrigger \| None`, `adaptation_notes: list[str]` | Validator: rationale not empty |
| `assess_feasibility(summary, classification, manifests_dir) -> FeasibilityResult` | — | Main orchestrator per innovation type |

Gating logic:

| Innovation Type | Stages Run | FEASIBLE | FEASIBLE_WITH_ADAPTATION | ESCALATE | NOT_FEASIBLE |
|---|---|---|---|---|---|
| parameter_tuning | Manifest only | coverage ≥ 0.5 | coverage > 0, < 0.5 | confidence < 0.6 | coverage == 0.0 |
| modular_swap | Manifest + blast radius | coverage ≥ 0.5 AND risk ∈ {low, medium} | coverage > 0 AND risk ≠ critical | confidence < 0.6 OR risk == critical | coverage == 0.0 |
| pipeline_restructuring | Full | coverage ≥ 0.5 AND risk ∈ {low, medium} AND test_cov ≥ 0.5 | coverage > 0 AND risk ≠ critical | confidence < 0.6 OR risk == critical | coverage == 0.0 |
| architectural_innovation | Full (strictest) | coverage ≥ 0.5 AND risk ∈ {low, medium} AND test_cov ≥ 0.7 | coverage > 0 AND coverage ≥ 0.3 | unmatched > 50% OR confidence < 0.6 | coverage == 0.0 OR unmatched > 80% |

- ESCALATE sets `escalation_trigger` to `confidence_below_threshold` or `novel_primitive`.
- `adaptation_notes` populated for FEASIBLE_WITH_ADAPTATION.
- Internal helpers: `_build_operations_list(summary)`, `_gate_parameter_tuning(...)`, `_gate_modular_swap(...)`, `_gate_pipeline_restructuring(...)`, `_gate_architectural_innovation(...)`.

**Create** `tests/test_feasibility/test_gate.py` — 12 tests:
- `FeasibilityStatus` enum has 4 values
- `FeasibilityResult` constructs minimal (parameter_tuning: blast_radius=None)
- `FeasibilityResult` constructs full (pipeline_restructuring: all populated)
- `FeasibilityResult` rejects empty rationale
- `FeasibilityResult` JSON round-trip
- `assess_feasibility()` returns FEASIBLE for parameter_tuning against real manifests
- `assess_feasibility()` returns FEASIBLE or FEASIBLE_WITH_ADAPTATION for modular_swap
- `assess_feasibility()` returns result with blast_radius for pipeline_restructuring
- `assess_feasibility()` returns result with coverage for architectural_innovation
- `assess_feasibility()` returns ESCALATE when confidence < 0.6
- `assess_feasibility()` returns NOT_FEASIBLE when no operations match
- `assess_feasibility()` returns ESCALATE with novel_primitive when >50% unmatched for architectural

---

## WU 3.6: CLI Entry Points

**Create** `scripts/check_feasibility.py`

```
python3 scripts/check_feasibility.py --input summary.json --classification classification.json
python3 scripts/check_feasibility.py --input summary.json --classification classification.json --manifests-dir /path/to/manifests
```

- `main(argv: list[str] | None = None) -> int`
- Exit code 0 on FEASIBLE/FEASIBLE_WITH_ADAPTATION, 1 on ESCALATE/NOT_FEASIBLE, 2 on error

**Create** `scripts/build_dep_graph.py`

```
python3 scripts/build_dep_graph.py --stats
python3 scripts/build_dep_graph.py --query downstream <node_id>
python3 scripts/build_dep_graph.py --manifests-dir /path/to/manifests
```

- `main(argv: list[str] | None = None) -> int`
- Default: build graph, print stats summary
- Exit code 0 on success, 1 on error

**Create** `tests/test_feasibility/test_cli.py` — 7 tests:
- `scripts/check_feasibility.py` and `scripts/build_dep_graph.py` exist
- Both importable with `main()` function
- `check_feasibility` end-to-end: parameter_tuning summary + classification -> exit 0
- `check_feasibility` exit code 2 on invalid JSON
- `build_dep_graph --stats` returns exit code 0
- `build_dep_graph` default returns exit code 0

---

## Conftest Fixtures

**Modify** `tests/conftest.py` — append 8 new fixtures:

| Fixture | Returns |
|---------|---------|
| `sample_classification_parameter_tuning(...)` | `ClassificationResult` via `classify()` on parameter_tuning fixtures |
| `sample_classification_modular_swap(...)` | `ClassificationResult` via `classify()` on modular_swap fixtures |
| `sample_classification_pipeline_restructuring(...)` | `ClassificationResult` via `classify()` with flow_restructuring topology |
| `sample_classification_architectural(...)` | `ClassificationResult` via `classify()` on architectural fixtures |
| `synthetic_manifest_yaml(tmp_path)` | Path to synthetic YAML (5 functions, 2 classes incl test/contract nodes) |
| `synthetic_manifests_dir(tmp_path, synthetic_manifest_yaml)` | Path to dir containing synthetic manifest |
| `synthetic_dependency_graph(synthetic_manifests_dir)` | `DependencyGraph` built from synthetic data |
| `real_dependency_graph(clearinghouse_manifests)` | `DependencyGraph` from real manifests (skips if unavailable) |

---

## Expected Results on Existing Fixtures

| Fixture | Innovation Type | Expected Status |
|---------|----------------|----------------|
| parameter_tuning_summary | parameter_tuning | FEASIBLE or FEASIBLE_WITH_ADAPTATION |
| modular_swap_summary | modular_swap | FEASIBLE_WITH_ADAPTATION |
| pipeline_restructuring_summary | pipeline_restructuring | FEASIBLE_WITH_ADAPTATION |
| architectural_summary | architectural_innovation | ESCALATE (novel primitives) |

---

## Final: Update `__init__.py`

**Modify** `research_engineer/feasibility/__init__.py` — public exports:
- `BlastRadiusReport`, `RiskLevel`, `compute_blast_radius`
- `DependencyGraph`, `GraphNode`, `GraphStats`, `build_dependency_graph`
- `FeasibilityResult`, `FeasibilityStatus`, `assess_feasibility`
- `ManifestCheckResult`, `RepositoryManifest`, `check_operations`, `load_all_manifests`, `load_manifest`
- `CoverageAssessment`, `assess_test_coverage`

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/feasibility/manifest_checker.py` | 3.1 |
| Create | `research_engineer/feasibility/dependency_graph.py` | 3.2 |
| Create | `research_engineer/feasibility/blast_radius.py` | 3.3 |
| Create | `research_engineer/feasibility/test_coverage.py` | 3.4 |
| Create | `research_engineer/feasibility/gate.py` | 3.5 |
| Create | `scripts/check_feasibility.py` | 3.6 |
| Create | `scripts/build_dep_graph.py` | 3.6 |
| Modify | `tests/conftest.py` (append 8 fixtures) | all |
| Modify | `research_engineer/feasibility/__init__.py` (add exports) | all |
| Create | `tests/test_feasibility/test_manifest_checker.py` | 3.1 |
| Create | `tests/test_feasibility/test_dependency_graph.py` | 3.2 |
| Create | `tests/test_feasibility/test_blast_radius.py` | 3.3 |
| Create | `tests/test_feasibility/test_test_coverage.py` | 3.4 |
| Create | `tests/test_feasibility/test_gate.py` | 3.5 |
| Create | `tests/test_feasibility/test_cli.py` | 3.6 |

**Total new tests: ~54** (within blueprint estimate of 40-50, slightly above)
**Running total after Phase 3: 157 + 54 = ~211 tests**

---

## Verification

```bash
python3 -m pytest tests/test_feasibility/ -v     # all ~54 new tests pass
python3 -m pytest tests/ -v                       # all ~211 tests pass (157 + 54)
python3 -c "from research_engineer.feasibility import assess_feasibility, FeasibilityStatus, DependencyGraph, ManifestCheckResult"
python3 scripts/build_dep_graph.py --stats
```
