# Phase 3: Feasibility Gate — Architecture

## Overview

The feasibility gate is Stage 3 of the paper-to-blueprint pipeline. It takes a
`ComprehensionSummary` (Stage 1 output) and `ClassificationResult` (Stage 2 output)
and produces a `FeasibilityResult` that determines whether the proposed innovation
is implementable against the live codebase state.

## Feasibility Statuses

| Status | Meaning | CLI Exit Code |
|--------|---------|---------------|
| `FEASIBLE` | All checks pass | 0 |
| `FEASIBLE_WITH_ADAPTATION` | Possible with modifications | 0 |
| `ESCALATE` | Needs human review | 1 |
| `NOT_FEASIBLE` | Cannot be implemented | 1 |

## Architecture

```
ComprehensionSummary ──→ _build_operations_list()
         │                        │
ClassificationResult             ↓
         │              check_operations(ops, manifests)
         │                        │
         │              ManifestCheckResult
         │                        │
         └────────────────┬───────┘
                          │
                  assess_feasibility()
                          │
            ┌─────────────┴──────────────┐
            │  load_all_manifests()      │
            │  build_dependency_graph()   │
            │  compute_blast_radius()     │
            │  assess_test_coverage()     │
            │          │                  │
            │  Per-innovation-type gate:  │
            │  ├─ parameter_tuning       │
            │  │   (manifest only)       │
            │  ├─ modular_swap           │
            │  │   (manifest + blast)    │
            │  ├─ pipeline_restructuring │
            │  │   (full analysis)       │
            │  └─ architectural_innovation│
            │      (full, strictest)     │
            └─────────────┬──────────────┘
                          │
                  FeasibilityResult
                  (status, rationale,
                   manifest_check, blast_radius,
                   coverage, escalation_trigger,
                   adaptation_notes)
```

## Per-Innovation-Type Gating

| Innovation Type | Stages Run | FEASIBLE | FEASIBLE_WITH_ADAPTATION | ESCALATE | NOT_FEASIBLE |
|---|---|---|---|---|---|
| parameter_tuning | Manifest only | coverage >= 0.5 | 0 < coverage < 0.5 | confidence < 0.6 | coverage == 0 |
| modular_swap | Manifest + blast radius | coverage >= 0.5 AND risk in {low, medium} | coverage > 0 AND risk != critical | confidence < 0.6 OR risk == critical | coverage == 0 |
| pipeline_restructuring | Full | coverage >= 0.5 AND risk in {low, medium} AND test_cov >= 0.5 | coverage > 0 AND risk != critical | confidence < 0.6 OR risk == critical | coverage == 0 |
| architectural_innovation | Full (strictest) | coverage >= 0.5 AND risk in {low, medium} AND test_cov >= 0.7 | coverage > 0 AND coverage >= 0.3 | unmatched > 50% OR confidence < 0.6 | coverage == 0 OR unmatched > 80% |

## Dependency Graph

NetworkX DiGraph built from clearinghouse YAML manifests:

- **Node types:** module, function, class
- **Node ID format:** `{repo_name}::{module_path}.{name}` (functions/classes), `{repo_name}::{module_path}` (modules)
- **Edge types:** `contains` (module→function), `method_of` (class→method), `imports` (sibling modules)
- **Queries:** downstream(), upstream(), shortest_path(), connected_component(), stats()

## Blast Radius Risk Classification

| Affected Count | Risk Level |
|---------------|------------|
| 0–2 | low |
| 3–10 | medium |
| 11–30 | high |
| >30 | critical |

Test nodes identified by "test" in module_path/node_id. Contract nodes by "contract".

## agent-factors Integration

| What | Import | Usage |
|------|--------|-------|
| `EscalationTrigger` | `agent_factors.g_layer.escalation` | ESCALATE status: confidence_below_threshold or novel_primitive |

## Module Layout

```
research_engineer/feasibility/
├── __init__.py           # Public exports
├── manifest_checker.py   # ManifestFunction, ManifestClass, RepositoryManifest, check_operations()
├── dependency_graph.py   # DependencyGraph (NetworkX), GraphNode, GraphStats
├── blast_radius.py       # RiskLevel, BlastRadiusReport, compute_blast_radius()
├── test_coverage.py      # CoverageAssessment, assess_test_coverage()
└── gate.py               # FeasibilityStatus, FeasibilityResult, assess_feasibility()

scripts/
├── check_feasibility.py  # CLI: --input --classification --manifests-dir
└── build_dep_graph.py    # CLI: --stats, --query downstream/upstream <node>
```

## Key Invariants

1. Gate logic is **deterministic** — same inputs always produce same output (no LLM calls)
2. Analysis depth is **per-innovation-type** — parameter_tuning runs fewest stages, architectural_innovation runs all
3. Feasibility statuses are **ordered** — FEASIBLE > FEASIBLE_WITH_ADAPTATION > ESCALATE > NOT_FEASIBLE
4. All escalation triggers use **agent-factors EscalationTrigger** values, never custom strings
5. `adaptation_notes` only populated for FEASIBLE_WITH_ADAPTATION status
