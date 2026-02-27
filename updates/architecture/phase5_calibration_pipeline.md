# Phase 5 Architecture: Calibration & Accuracy Tracking

## Overview

The calibration pipeline forms a closed feedback loop: classification predictions are
recorded against ground truth, accuracy metrics drive maturity gate decisions, and
misclassification patterns propose heuristic mutations.

```
AccuracyTracker (5.1)
    │
    ├──→ MaturityAssessor (5.2) ──→ ready / not_ready / insufficient_data
    │         uses: agent-factors check_maturity_eligibility + DEFAULT_GATES
    │
    ├──→ HeuristicEvolver (5.3) ──→ EvolutionProposal → EvolutionResult
    │         uses: ArtifactRegistry.update(), validate_heuristic_yaml()
    │
    └──→ ReportGenerator (5.4) ──→ CalibrationReport + markdown
              │
              └──→ CLI (5.5): scripts/calibration_report.py
```

## Module Details

### 5.1 AccuracyTracker (`tracker.py`)

Core data model for recording and analyzing classification accuracy.

**Models:**
- `AccuracyRecord` — single prediction vs ground truth, computed `is_correct`
- `ClassificationConfusionMatrix` — 4×4 matrix over InnovationType, computed `overall_accuracy`
- `PerTypeAccuracy` — per-type TP/FP/FN with computed precision, recall, F1
- `AccuracyReport` — aggregates confusion matrix + per-type + correlation

**AccuracyTracker class:**
- JSONL persistence: append on `add_record()`, bulk load on `__init__()`
- `confusion_matrix()` builds from accumulated records
- `confidence_accuracy_correlation()` uses point-biserial (stdlib math only)

### 5.2 MaturityAssessor (`maturity_assessor.py`)

Maps domain accuracy metrics to agent-factors maturity gate protocol.

**Mapping:**
| Domain metric | agent-factors parameter |
|---------------|----------------------|
| total_papers_evaluated | session_count |
| overall_accuracy | approval_rate |
| 1 − overall_accuracy | error_rate |
| artifact_count | artifact_count |

**Gate:** `DEFAULT_GATES["foundational_to_empirical"]`
- min_session_count = 5
- min_approval_rate = 0.80
- max_error_rate = 0.20

**Domain-specific:** worst_type_f1 ≥ 0.6 (no blind spots across innovation types)

**Outputs:** "ready", "not_ready" (with EscalationTrigger), "insufficient_data"

### 5.3 HeuristicEvolver (`heuristic_evolver.py`)

Analyzes misclassification patterns and proposes rule mutations.

**Pipeline:**
1. `analyze_misclassifications(tracker)` → groups errors by (predicted, actual) pair
2. `propose_mutations(patterns, registry)` → keyword additions, weight adjustments
3. `apply_evolution(proposal, registry, auto_apply=False)` → YAML mutation + validation

**Mutation types:** add_keyword, adjust_weight, add_rule, adjust_priority

**Safety:** defaults to `auto_apply=False`, always sets `requires_human_review=True`

### 5.4 ReportGenerator (`report.py`)

Orchestrates all calibration subsystems into a single report.

**CalibrationReport** contains: accuracy_report, maturity_assessment, evolution_proposal,
recommendation_summary.

**render_markdown()** produces sections: Accuracy Summary, Per-Type Accuracy, Confusion
Matrix, Maturity Assessment, Misclassification Patterns, Proposed Mutations, Recommendation.

### 5.5 CLI (`scripts/calibration_report.py`)

```
python3 scripts/calibration_report.py --records accuracy.jsonl [--json] [--apply-evolution]
```

Exit codes: 0 = success/ready, 1 = maturity not ready, 2 = error.

## agent-factors Integration Points

| Import | Source | Usage |
|--------|--------|-------|
| `check_maturity_eligibility` | `agent_factors.g_layer.maturity` | Gate decision |
| `DEFAULT_GATES` | `agent_factors.g_layer.maturity` | Threshold lookup |
| `EscalationTrigger` | `agent_factors.g_layer.escalation` | When maturity not met |
| `ArtifactRegistry` | `agent_factors.artifacts` | Heuristic storage + evolution |

## Test Coverage

35 tests across 5 test files, exercising all models, functions, persistence, and CLI.
