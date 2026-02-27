# Phase 5: Calibration & Accuracy Tracking — Implementation Plan

## Context

Phases 0-4 are complete (243 tests). Phase 5 builds the calibration pipeline that records classification accuracy against ground truth, evaluates maturity gate eligibility, evolves classification heuristics from misclassification patterns, and generates structured reports. All computation is deterministic — no LLM calls.

---

## Implementation Order

```
WU 5.1 (tracker.py)  ──→  WU 5.2 (maturity_assessor.py)
                      ──→  WU 5.3 (heuristic_evolver.py)
                                    ──→  WU 5.4 (report.py)
                                              ──→  WU 5.5 (calibration_report.py CLI)
                                              ──→  conftest fixtures + __init__.py
```

---

## WU 5.1: Accuracy Tracker

**Create** `research_engineer/calibration/tracker.py`

| Model | Key Fields |
|-------|-----------|
| `AccuracyRecord` | `paper_id: str`, `predicted_type: InnovationType`, `ground_truth_type: InnovationType`, `confidence: float` (0-1), `rationale: str`, `timestamp: datetime`; computed `is_correct: bool` |
| `ClassificationConfusionMatrix` | `matrix: dict[str, dict[str, int]]`, `labels: list[str]`, `total_records: int`, `correct_count: int`; computed `overall_accuracy: float` |
| `PerTypeAccuracy` | `innovation_type: InnovationType`, `true_positives: int`, `false_positives: int`, `false_negatives: int`, `total_actual: int`; computed `precision`, `recall`, `f1_score` |
| `AccuracyReport` | `confusion_matrix`, `per_type: list[PerTypeAccuracy]`, `overall_accuracy`, `total_records`, `confidence_accuracy_correlation` |

Class `AccuracyTracker`:
- `__init__(store_path: Path | None)` — load existing JSONL records on init
- `add_record(record)` — append to in-memory list + JSONL file
- `records()` → list[AccuracyRecord]
- `confusion_matrix()` → 4×4 ClassificationConfusionMatrix
- `per_type_accuracy()` → list[PerTypeAccuracy]
- `report()` → AccuracyReport
- `misclassifications()` → list of incorrect AccuracyRecords
- `confidence_accuracy_correlation()` → float (point-biserial, stdlib only — no numpy)

Persistence: JSONL via `model_dump_json()` per line, loaded on init with `model_validate_json()`.

**Tests** `tests/test_calibration/test_tracker.py` — 8 tests:
1. AccuracyRecord creation + computed `is_correct`
2. AccuracyRecord JSON round-trip
3. add_record then records() retrieval
4. Confusion matrix counts correct for sample data (4 correct, 2 wrong)
5. Per-type precision/recall/F1
6. Overall accuracy = 4/6 ≈ 0.667
7. misclassifications() returns only 2 wrong records
8. JSONL persistence survives tracker re-init from same file

---

## WU 5.2: Maturity Assessor

**Create** `research_engineer/calibration/maturity_assessor.py`

| Model | Key Fields |
|-------|-----------|
| `CalibrationEvidence` | `total_papers_evaluated: int`, `overall_accuracy: float`, `per_type_f1_scores: dict[str, float]`, `has_calibration_set: bool`, `artifact_count: int`, `worst_type_f1: float`, `confidence_accuracy_correlation: float` |
| `MaturityAssessment` | `repo: str`, `current_level: str`, `target_level: str`, `recommendation: str` ("ready"/"not_ready"/"insufficient_data"), `evidence: CalibrationEvidence`, `unmet_requirements: list[str]`, `escalation_trigger: EscalationTrigger | None` |

Function `assess_maturity(tracker, registry, repo_name, current_level) -> MaturityAssessment`:
1. Extract `AccuracyReport` from tracker
2. Count artifacts via `registry.count_by_type()`
3. Build `CalibrationEvidence`
4. Call `check_maturity_eligibility()` from `agent_factors.g_layer.maturity` with:
   - `session_count` = total_papers_evaluated
   - `approval_rate` = overall_accuracy
   - `error_rate` = 1 - overall_accuracy
   - `gate` = `DEFAULT_GATES["foundational_to_empirical"]` (min_session_count=5, min_approval_rate=0.80, max_error_rate=0.20)
   - `artifact_count` = sum of count_by_type values
5. Domain-specific check: worst_type_f1 ≥ 0.6 (no blind spots per innovation type)
6. Return "insufficient_data" if < 5 records; "not_ready" with escalation_trigger if thresholds not met

**agent-factors imports**: `check_maturity_eligibility`, `DEFAULT_GATES` from `agent_factors.g_layer.maturity`; `ArtifactRegistry` from `agent_factors.artifacts`; `EscalationTrigger` from `agent_factors.g_layer.escalation`

**Tests** `tests/test_calibration/test_maturity_assessor.py` — 8 tests:
1. CalibrationEvidence creation
2. MaturityAssessment JSON round-trip
3. "insufficient_data" with < 5 records
4. "not_ready" when overall_accuracy < 0.80
5. "not_ready" when worst_type_f1 < 0.6, sets maturity_insufficient escalation
6. "ready" with sufficient accuracy data (all correct, enough records)
7. unmet_requirements populated correctly for failing checks
8. artifact_count correctly reflects registry contents

---

## WU 5.3: Heuristic Evolver

**Create** `research_engineer/calibration/heuristic_evolver.py`

| Model | Key Fields |
|-------|-----------|
| `MisclassificationPattern` | `predicted_type`, `actual_type`, `count: int`, `fraction_of_total_errors: float`, `example_paper_ids: list[str]`, `avg_confidence: float` |
| `RuleMutation` | `mutation_type: str` ("add_keyword"/"adjust_weight"/"add_rule"/"adjust_priority"), `target_rule_id: str | None`, `description: str`, `parameter: str`, `old_value: str | None`, `new_value: str`; validator rejects invalid mutation_type |
| `EvolutionProposal` | `patterns: list[MisclassificationPattern]`, `mutations: list[RuleMutation]`, `expected_accuracy_improvement: float`, `requires_human_review: bool = True`, `rationale: str` |
| `EvolutionResult` | `proposal: EvolutionProposal`, `applied: bool`, `new_artifact_version: int | None`, `artifact_id: str | None` |

Functions:
- `analyze_misclassifications(tracker)` → list[MisclassificationPattern] — groups by (predicted, actual) pair
- `propose_mutations(patterns, registry)` → EvolutionProposal — add keywords for missed types, adjust weights for low-confidence errors
- `apply_evolution(proposal, registry, auto_apply=False)` → EvolutionResult — loads YAML, applies mutations, validates via `validate_heuristic_yaml()`, writes new version via `registry.update(artifact_id, content, author="calibration-evolver")`

Mutation types: `add_keyword` appends to signals.transformation_keywords; `adjust_weight` updates weight; `adjust_priority` updates priority; `add_rule` appends new rule dict.

**Internal imports**: `validate_heuristic_yaml`, `CLASSIFIER_DOMAIN` from `research_engineer.classifier.seed_artifact`; `ArtifactRegistry`, `ArtifactType` from `agent_factors.artifacts`

**Tests** `tests/test_calibration/test_heuristic_evolver.py` — 10 tests:
1. MisclassificationPattern creation
2. RuleMutation rejects invalid mutation_type
3. EvolutionProposal JSON round-trip
4. analyze_misclassifications groups correctly (2 patterns from sample data)
5. analyze with no misclassifications → empty list
6. propose_mutations includes add_keyword for param→swap pattern
7. propose_mutations includes weight adjustment for low-confidence errors
8. apply_evolution default → applied=False
9. apply_evolution auto_apply=True → new artifact version in registry
10. Applied YAML passes validate_heuristic_yaml

---

## WU 5.4: Calibration Report Generator

**Create** `research_engineer/calibration/report.py`

| Model | Key Fields |
|-------|-----------|
| `CalibrationInput` | `tracker: AccuracyTracker`, `registry: ArtifactRegistry`, `repo_name: str`, `current_maturity_level: str`; `ConfigDict(arbitrary_types_allowed=True)` |
| `CalibrationReport` | `repo_name`, `timestamp`, `accuracy_report: AccuracyReport`, `maturity_assessment: MaturityAssessment`, `evolution_proposal: EvolutionProposal | None`, `total_papers: int`, `overall_accuracy: float`, `recommendation_summary: str` |
| `CalibrationReportMarkdown` | `content: str`, `report: CalibrationReport` |

Functions:
- `generate_report(input)` → CalibrationReport — orchestrates tracker.report() + assess_maturity() + analyze/propose if misclassifications exist
- `render_markdown(report)` → CalibrationReportMarkdown — sections: Accuracy Summary, Confusion Matrix, Maturity Assessment, Misclassification Patterns, Proposed Mutations, Recommendation

**Tests** `tests/test_calibration/test_report.py` — 5 tests:
1. generate_report returns CalibrationReport with all fields
2. report.accuracy_report matches tracker.report()
3. report has maturity_assessment populated
4. render_markdown contains expected section headers
5. render_markdown contains accuracy percentage

---

## WU 5.5: CLI Entry Point

**Create** `scripts/calibration_report.py`

```
python3 scripts/calibration_report.py --records accuracy.jsonl
python3 scripts/calibration_report.py --records accuracy.jsonl --json
python3 scripts/calibration_report.py --records accuracy.jsonl --apply-evolution
```

Flags: `--records` (required), `--artifact-store` (default artifacts/store/), `--repo`, `--maturity-level`, `--output`, `--json`, `--apply-evolution`

Exit codes: 0 success/ready, 1 maturity not ready, 2 error.

**Tests** `tests/test_calibration/test_cli.py` — 4 tests:
1. Script file exists
2. Importable with callable main()
3. --json produces valid JSON with expected keys
4. Default output contains expected markdown headers

---

## Conftest Fixtures (append to `tests/conftest.py`)

| Fixture | Returns |
|---------|---------|
| `sample_accuracy_records()` | 6 AccuracyRecords: 4 correct + 2 misclassified (param→swap, pipeline→architectural) |
| `sample_accuracy_tracker(sample_accuracy_records, tmp_calibration_dir)` | Pre-populated AccuracyTracker with JSONL persistence |
| `sample_calibration_input(sample_accuracy_tracker, seeded_artifact_registry)` | Bundled CalibrationInput for report testing |

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/calibration/tracker.py` | 5.1 |
| Create | `research_engineer/calibration/maturity_assessor.py` | 5.2 |
| Create | `research_engineer/calibration/heuristic_evolver.py` | 5.3 |
| Create | `research_engineer/calibration/report.py` | 5.4 |
| Create | `scripts/calibration_report.py` | 5.5 |
| Modify | `research_engineer/calibration/__init__.py` | all |
| Modify | `tests/conftest.py` (append 3 fixtures) | all |
| Create | `tests/test_calibration/test_tracker.py` | 5.1 |
| Create | `tests/test_calibration/test_maturity_assessor.py` | 5.2 |
| Create | `tests/test_calibration/test_heuristic_evolver.py` | 5.3 |
| Create | `tests/test_calibration/test_report.py` | 5.4 |
| Create | `tests/test_calibration/test_cli.py` | 5.5 |

**Total new tests: 35** (within blueprint estimate of 35-40)
**Running total: 243 + 35 = ~278 tests**

---

## Verification

```bash
python3 -m pytest tests/test_calibration/ -v     # all ~35 new tests pass
python3 -m pytest tests/ -v                       # all ~278 tests pass
python3 -c "from research_engineer.calibration import AccuracyTracker, assess_maturity, propose_mutations, generate_report"
python3 scripts/calibration_report.py --help
```
