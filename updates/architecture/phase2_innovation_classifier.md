# Phase 2: Innovation-Type Classifier — Architecture

## Overview

The classifier is Stage 2 of the paper-to-blueprint pipeline. It takes a
`ComprehensionSummary` (Stage 1 output) and produces a `ClassificationResult`
that determines which of 4 innovation types the paper represents. This drives
all downstream planning complexity (WU count, verification strategy).

## Innovation Types

| Type | Planning Complexity | Verification |
|------|--------------------| -------------|
| `parameter_tuning` | 1-3 WUs | Config change + regression test |
| `modular_swap` | 3-5 WUs | Interface compatibility |
| `pipeline_restructuring` | 5-12 WUs | Contract + blast radius |
| `architectural_innovation` | 8-20 WUs | DAG acyclicity + gates |

## Architecture

```
ComprehensionSummary ──→ analyze_topology() ──→ TopologyChange
         │                                           │
         └──────────────────┬────────────────────────┘
                            │
                    classify(summary, topology,
                            manifest_evidence, registry)
                            │
                 ┌──────────┴──────────┐
                 │  load_heuristic_rules()
                 │  (from ArtifactRegistry)
                 │          │
                 │  For each rule:
                 │    topology_match_score
                 │    keyword_match_score
                 │    weighted_score = match * weight
                 │          │
                 │  Best-scoring rule wins
                 │  (ties: lower priority wins)
                 │          │
                 │  compute_confidence()
                 │  check_escalation()
                 └──────────┬──────────┘
                            │
                   ClassificationResult
                   (type, confidence, rationale,
                    topology_signal, manifest_evidence,
                    escalation_trigger)
```

## Heuristic Rules (Seed Artifact)

Rules stored as YAML in `ArtifactRegistry` (type: `evaluation_rubric`,
domain: `research_engineer_classification`). 5 rules ordered by priority:

| Priority | Rule ID | Classification | Key Signals |
|----------|---------|---------------|-------------|
| 1 | `rule_parameter_tuning` | parameter_tuning | topology=none, keywords: parameter/tune/adjust |
| 2 | `rule_modular_swap` | modular_swap | topology=component_swap, keywords: replace/swap |
| 3 | `rule_architectural_innovation` | architectural_innovation | topology=stage_addition, keywords: new evaluation/novel/knowledge graph |
| 4 | `rule_pipeline_restructuring` | pipeline_restructuring | topology=stage_addition/removal/flow, keywords: restructure/new stage |
| 5 | `rule_pipeline_restructuring_fallback` | pipeline_restructuring | topology change only, no keywords required |

## Confidence Scoring

```
confidence = 0.5 * heuristic_match_strength
           + 0.3 * topology_agreement * topology_confidence
           + 0.2 * manifest_score

topology_agreement:
  agreeing   → 1.0
  mismatch   → 0.3
  contradict → 0.0

manifest_score = min(evidence_count / 2.0, 1.0)
```

Escalation triggered when `confidence < 0.6` via `EscalationTrigger.confidence_below_threshold`.

## agent-factors Integration

| What | Import | Usage |
|------|--------|-------|
| `EscalationTrigger` | `agent_factors.g_layer.escalation` | Escalation flag on ClassificationResult |
| `ArtifactRegistry` | `agent_factors.artifacts` | Storage/retrieval of heuristic YAML rules |
| `ArtifactType.evaluation_rubric` | `agent_factors.artifacts` | Artifact type discriminator |

## Module Layout

```
research_engineer/classifier/
├── __init__.py          # Public exports
├── types.py             # InnovationType, ClassificationResult
├── seed_artifact.py     # Seed YAML, register_seed_artifact()
├── heuristics.py        # classify(), load_heuristic_rules()
└── confidence.py        # compute_confidence(), check_escalation()

scripts/
└── evaluate_paper.py    # CLI: --classify-only --input --artifact-store
```

## Key Invariants

1. Classification is **deterministic** — same inputs always produce same output (no LLM calls)
2. Rules are **hot-swappable** — update the artifact in the registry, classification changes
3. Confidence is **bounded** [0.0, 1.0] with **escalation at 0.6**
4. The seed artifact auto-registers on first use if no `evaluation_rubric` exists in the domain
