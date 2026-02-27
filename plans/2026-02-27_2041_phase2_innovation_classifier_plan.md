# Phase 2: Innovation-Type Classifier with Artifact-Backed Heuristics — Implementation Plan

## Context

Phases 0-1 are complete (106 tests). Phase 2 builds the 4-type innovation classifier that consumes Phase 1's `ComprehensionSummary` + `TopologyChange` + `VocabularyMapping` and produces a `ClassificationResult`. Heuristic rules are stored as YAML in the agent-factors `ArtifactRegistry` (type `evaluation_rubric`), not hardcoded. All classification is rule-based — no LLM calls.

---

## Implementation Order

```
WU 2.1 (types.py)  ──→  WU 2.3 (seed_artifact.py)  ──→  conftest fixtures
                                                      ──→  WU 2.2 (heuristics.py)
                                                              ──→  WU 2.4 (confidence.py)
                                                                      ──→  WU 2.5 (evaluate_paper.py CLI)
                                                                      ──→  __init__.py update
```

---

## WU 2.1: Classification Types

**Create** `research_engineer/classifier/types.py`

| Model | Key Fields | Validators |
|-------|-----------|------------|
| `InnovationType(str, Enum)` | `parameter_tuning`, `modular_swap`, `pipeline_restructuring`, `architectural_innovation` | — |
| `ClassificationResult` | `innovation_type: InnovationType`, `confidence: float` (0-1), `rationale: str`, `topology_signal: str`, `manifest_evidence: list[str]`, `escalation_trigger: EscalationTrigger \| None` | rationale not empty, confidence in [0,1] |

- Imports `EscalationTrigger` from `agent_factors.g_layer.escalation` — never redefines it
- `topology_signal` is a string summary (e.g., "stage_addition with confidence 0.67")
- `manifest_evidence` is a list of description strings (e.g., "BM25 found in multimodal-rag-core")

**Create** `tests/test_classifier/test_types.py` — 8 tests:
- Enum has 4 values, values are strings
- ClassificationResult: minimal/full construction, JSON round-trip
- Rejects empty rationale, rejects confidence > 1.0
- escalation_trigger defaults to None

---

## WU 2.3: Seed Heuristic Artifact

**Create** `research_engineer/classifier/seed_artifact.py`

Constants:
- `CLASSIFIER_DOMAIN = "research_engineer_classification"`
- `SEED_ARTIFACT_NAME = "innovation_type_classification_heuristic"`
- `SEED_ARTIFACT_PROVENANCE = "comm-018"`

Functions:
- `get_seed_heuristic_content() -> str` — returns the YAML string
- `validate_heuristic_yaml(content: str) -> dict` — parses YAML, validates `rules` key with required fields
- `register_seed_artifact(registry: ArtifactRegistry) -> str` — registers if not exists, returns artifact_id

YAML content structure — 5 ordered rules from comm-018:

```yaml
rules:
  - rule_id: str
    description: str
    classification: str        # InnovationType value
    priority: int              # lower = higher priority
    signals:
      topology_change_type: str | list[str]
      transformation_keywords: list[str]
      manifest_only: bool      # (rule 1 only)
    weight: float              # confidence weight 0.0-1.0
```

| Rule | Classification | Key Signals |
|------|---------------|-------------|
| 1 (priority 1) | `parameter_tuning` | topology=none, keywords: "parameter", "tune", "adjust", "grid search" |
| 2 (priority 2) | `modular_swap` | topology=component_swap, keywords: "replace", "swap", "substitute" |
| 3 (priority 3) | `architectural_innovation` | topology=stage_addition/flow_restructuring, keywords: "new evaluation methodology", "novel", "knowledge graph"; has_new_evaluation=true |
| 4 (priority 4) | `pipeline_restructuring` | topology=stage_addition/stage_removal/flow_restructuring, keywords: "restructure", "new stage", "intermediate representation" |
| 5 (priority 5) | `pipeline_restructuring` | topology=stage_addition/stage_removal/flow_restructuring; fallback rule |

Key design: `architectural_innovation` (rule 3) is checked **before** `pipeline_restructuring` (rule 4) because it's more specific — it requires "new evaluation methodology" or multiple new infrastructure signals. This ensures the architectural fixture (knowledge graph with "new evaluation methodology") classifies correctly.

**Create** `tests/test_classifier/test_seed_artifact.py` — 7 tests:
- YAML parses, has `rules` key, has 5 rules
- All rules have required keys (rule_id, classification, priority, signals)
- All classification values are valid InnovationType values
- `register_seed_artifact` creates entry, is idempotent
- `get_content()` returns parseable YAML

---

## Conftest Fixtures for Phase 2

**Modify** `tests/conftest.py` — append 6 new fixtures:

| Fixture | Returns |
|---------|---------|
| `tmp_artifact_registry(tmp_path)` | Empty `ArtifactRegistry` backed by tmp_path |
| `seeded_artifact_registry(tmp_artifact_registry)` | Registry with seed heuristic pre-loaded |
| `sample_topology_none()` | `TopologyChange(change_type=none, confidence=0.67)` |
| `sample_topology_component_swap()` | `TopologyChange(change_type=component_swap, affected_stages=["retrieval"])` |
| `sample_topology_stage_addition()` | `TopologyChange(change_type=stage_addition, affected_stages=[...])` |
| `sample_pipeline_restructuring_summary()` | 4th ComprehensionSummary: "Restructure pipeline to reorder reranking" |

---

## WU 2.2: Heuristic Engine

**Create** `research_engineer/classifier/heuristics.py`

Functions:
- `load_heuristic_rules(registry: ArtifactRegistry) -> list[dict]` — queries registry for evaluation_rubric in classifier domain; auto-registers seed if none found
- `classify(summary, topology, manifest_evidence, registry) -> ClassificationResult` — primary entry point

Classification algorithm — **best-score wins** (not first-match):
1. Load rules from artifact registry
2. For each rule, compute `match_strength`:
   - `topology_match_score`: 1.0 if topology matches rule's `signals.topology_change_type`, 0.0 otherwise
   - `keyword_match_score`: `min(matched_keywords / 2.0, 1.0)` scanning `transformation_proposed` + abstract content
   - `match_strength = (topology_match_score + keyword_match_score) / 2.0`
3. Weighted score = `match_strength * rule.weight`
4. Best-scoring rule wins; ties broken by priority (lower number wins)
5. Confidence computed via WU 2.4's `compute_confidence()`
6. If confidence < 0.6, set `escalation_trigger = EscalationTrigger.confidence_below_threshold`

Expected results on fixtures:

| Fixture | Topology | Best Rule | Result |
|---------|----------|-----------|--------|
| parameter_tuning_summary | none | Rule 1 | `parameter_tuning` |
| modular_swap_summary | component_swap | Rule 2 | `modular_swap` |
| architectural_summary | stage_addition | Rule 3 | `architectural_innovation` |
| pipeline_restructuring_summary | flow_restructuring | Rule 4 | `pipeline_restructuring` |

**Create** `tests/test_classifier/test_heuristics.py` — 12 tests:
- `load_heuristic_rules` returns non-empty list, sorted by priority, auto-registers seed
- `classify` returns correct type for all 4 fixtures
- Confidence in [0,1], confidence > 0.6 on clear fixtures
- Rationale non-empty, topology_signal populated
- Low-confidence ambiguous input triggers escalation

---

## WU 2.4: Confidence Scoring

**Create** `research_engineer/classifier/confidence.py`

Constants: `HEURISTIC_WEIGHT = 0.5`, `TOPOLOGY_WEIGHT = 0.3`, `MANIFEST_WEIGHT = 0.2`

Functions:
- `compute_confidence(heuristic_match_strength, topology, innovation_type, manifest_evidence_count) -> float`
- `check_escalation(confidence, innovation_type) -> EscalationTrigger | None` — returns trigger if confidence < 0.6
- `escalate_to_task_classification(confidence, innovation_type) -> TaskClassification` — calls `classify_task_autonomy()`

Confidence formula:
```
topology_score = _topology_agreement_score(topology, innovation_type)
manifest_score = min(manifest_evidence_count / 2.0, 1.0)
confidence = 0.5 * heuristic + 0.3 * topology_score * topology.confidence + 0.2 * manifest_score
```

Topology agreement:

| Innovation Type | Agreeing Topology | Score |
|----------------|------------------|-------|
| parameter_tuning | none | 1.0 |
| modular_swap | component_swap | 1.0 |
| pipeline_restructuring | stage_addition/removal/flow_restructuring | 1.0 |
| architectural_innovation | stage_addition/flow_restructuring | 1.0 |
| Any mismatch | — | 0.3 |
| parameter_tuning | stage_addition | 0.0 (contradiction) |

**Create** `tests/test_classifier/test_confidence.py` — 10 tests:
- High confidence when all signals agree (> 0.85)
- Low confidence with weak heuristic (< 0.6)
- Always in [0,1]
- Manifest evidence boosts confidence, topology agreement boosts, contradiction lowers
- `check_escalation`: 0.3 → trigger, 0.9 → None
- `escalate_to_task_classification` returns TaskClassification

---

## WU 2.5: CLI Entry Point

**Create** `scripts/evaluate_paper.py`

```
python3 scripts/evaluate_paper.py --classify-only --input summary.json
python3 scripts/evaluate_paper.py --classify-only --input summary.json --artifact-store /tmp/store
```

CLI logic:
1. Read ComprehensionSummary JSON from `--input` file (or stdin with `-`)
2. Run `analyze_topology(summary)` to get TopologyChange
3. Init `ArtifactRegistry` at `--artifact-store` (default: `artifacts/store/`)
4. Ensure seed artifact via `register_seed_artifact(registry)`
5. Call `classify(summary, topology, [], registry)`
6. Print `result.model_dump_json(indent=2)` to stdout
7. Return exit code 0 on success, 1 on error

**Create** `tests/test_classifier/test_cli.py` — 7 tests:
- Script exists, importable, has `main()` function
- End-to-end on parameter_tuning, modular_swap, architectural fixtures
- Exit code 0 on success, non-zero on invalid JSON

---

## Final: Update `__init__.py`

**Modify** `research_engineer/classifier/__init__.py` — add public exports:
- `InnovationType`, `ClassificationResult`, `classify`, `compute_confidence`, `check_escalation`, `register_seed_artifact`

---

## File Summary

| Action | File | WU |
|--------|------|-----|
| Create | `research_engineer/classifier/types.py` | 2.1 |
| Create | `research_engineer/classifier/seed_artifact.py` | 2.3 |
| Create | `research_engineer/classifier/heuristics.py` | 2.2 |
| Create | `research_engineer/classifier/confidence.py` | 2.4 |
| Create | `scripts/evaluate_paper.py` | 2.5 |
| Modify | `tests/conftest.py` (append 6 fixtures) | all |
| Modify | `research_engineer/classifier/__init__.py` (add exports) | all |
| Create | `tests/test_classifier/test_types.py` | 2.1 |
| Create | `tests/test_classifier/test_seed_artifact.py` | 2.3 |
| Create | `tests/test_classifier/test_heuristics.py` | 2.2 |
| Create | `tests/test_classifier/test_confidence.py` | 2.4 |
| Create | `tests/test_classifier/test_cli.py` | 2.5 |

**Total new tests: ~44** (within blueprint estimate of 35-45)

---

## Verification

```bash
python3 -m pytest tests/test_classifier/ -v     # all ~44 new tests pass
python3 -m pytest tests/ -v                      # all ~150 tests pass (106 + 44)
python3 -c "from research_engineer.classifier import classify, InnovationType, ClassificationResult"
```
