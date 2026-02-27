# System Architecture — 2026-02-27 18:32

## Overview

The autonomous-research-engineer is a paper-to-blueprint compiler with a feasibility gate.
It uses the simplest Stratum II architecture: classifier-compiler planning with decidable
verification. The system consumes agent-factors governance infrastructure and clearinghouse
coordination data.

## Current State: Phase 0 Complete (4 WUs)

- **Package:** `research_engineer` v0.1.0
- **Tests:** 55 passing
- **Subpackages:** comprehension, classifier, feasibility, translator, calibration
- **Dependencies:** pydantic>=2.0, pyyaml>=6.0, agent-factors

## Five-Stage Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    research_engineer package                          │
│                                                                      │
│  INPUT                                                               │
│    │                                                                 │
│    ▼                                                                 │
│  comprehension/        Stage 1: Paper → ComprehensionSummary         │
│    ├── schema.py       Pydantic models (PaperClaim, MathCore, etc.) │
│    ├── parser.py       Section extraction, notation ID               │
│    └── topology.py     Topology change detection                     │
│    │                                                                 │
│    ▼                                                                 │
│  classifier/           Stage 2: Summary → ClassificationResult       │
│    ├── types.py        InnovationType enum (4 types)                 │
│    ├── heuristics.py   Artifact-backed heuristic rules               │
│    └── confidence.py   Confidence scoring + escalation               │
│    │                                                                 │
│    ├──── if NOT_FEASIBLE ──► log_refusal() + exit                   │
│    ▼                                                                 │
│  feasibility/          Stage 3: Classification → FeasibilityResult   │
│    ├── manifest_checker.py   Manifest function matching              │
│    ├── dependency_graph.py   NetworkX codebase graph (NEW)           │
│    ├── blast_radius.py       Impact analysis (NEW)                   │
│    ├── test_coverage.py      Coverage gap assessment                 │
│    └── gate.py               Orchestrator (type-dependent depth)     │
│    │                                                                 │
│    ▼                                                                 │
│  translator/           Stage 4: Feasible → ADR-005 Blueprint         │
│    ├── manifest_targeter.py  File targeting from manifests           │
│    ├── change_patterns.py    Historical ledger mining (NEW)          │
│    ├── wu_decomposer.py      Method → WU DAG mapping                │
│    └── translator.py         Full pipeline orchestration             │
│    │                                                                 │
│    ▼                                                                 │
│  calibration/          Stage 5: Ongoing accuracy tracking            │
│    ├── tracker.py            Per-stage accuracy + reporting          │
│    ├── maturity_assessor.py  MaturityGate integration                │
│    └── heuristic_evolver.py  Self-evolving heuristics (NEW)          │
│                                                                      │
│  OUTPUT: ADR-005 WU-defined blueprint                                │
└──────────────────────────────────────────────────────────────────────┘
```

## Dependency Map

```
autonomous-research-engineer
    │
    ├── agent-factors (pip dependency)
    │   ├── g_layer/    → MaturityGate, escalation, log_refusal()
    │   ├── catalog/    → CatalogLoader (classifier-compiler, decidable-verification)
    │   ├── artifacts/  → ArtifactRegistry (heuristic storage, versioning)
    │   └── dag/        → Blueprint, WorkingUnit, validate_dag(), critical_path()
    │
    └── clearinghouse (sibling repo, read-only except ledger writes)
        ├── manifests/           → RepositoryManifest (feasibility gate input)
        ├── algorithms/          → Pattern Library (vocabulary mapping)
        ├── coordination/ledger  → Historical change patterns, ledger writes
        └── schemas/             → Shared Pydantic types
```

## Innovation Type × Gate Depth Matrix

```
┌─────────────────────────┬──────────┬───────────┬──────────────┬──────────┐
│ Innovation Type          │ Manifest │ Interface │ Blast Radius │ Full     │
│                          │ Check    │ Compat    │ + Contracts  │ Analysis │
├─────────────────────────┼──────────┼───────────┼──────────────┼──────────┤
│ parameter_tuning         │    ✓     │           │              │          │
│ modular_swap             │    ✓     │     ✓     │              │          │
│ pipeline_restructuring   │    ✓     │     ✓     │      ✓       │          │
│ architectural_innovation │    ✓     │     ✓     │      ✓       │    ✓     │
└─────────────────────────┴──────────┴───────────┴──────────────┴──────────┘
```

## Directory Structure

```
autonomous-research-engineer/
├── research_engineer/
│   ├── __init__.py              ✓ v0.1.0
│   ├── comprehension/__init__.py ✓
│   ├── classifier/__init__.py    ✓
│   ├── feasibility/__init__.py   ✓
│   ├── translator/__init__.py    ✓
│   └── calibration/__init__.py   ✓
├── scripts/
│   └── check_clearinghouse.py   ✓
├── tests/
│   ├── conftest.py              ✓ 14 fixtures
│   ├── test_foundation.py       ✓ 55 tests
│   ├── test_comprehension/      (Phase 1)
│   ├── test_classifier/         (Phase 2)
│   ├── test_feasibility/        (Phase 3)
│   ├── test_translator/         (Phase 4)
│   ├── test_calibration/        (Phase 5)
│   └── test_integration/        (Phase 7)
├── updates/
│   ├── architecture/            ✓
│   ├── logs/                    ✓
│   └── strategy/                ✓
├── plans/                       ✓
├── CLAUDE.md                    ✓
├── pyproject.toml               ✓
├── README.md                    ✓
└── .gitignore                   ✓
```

## Phase Roadmap

```
Phase 0 ✓ → Phase 1 → Phase 2 → Phase 3 ∥ Phase 4 → Phase 5 → Phase 6 → Phase 7
skeleton    comprehn   classifr   feasiblt    transltr   calibrtn   PAR integ  video
4 WUs       5 WUs      5 WUs      6 WUs       6 WUs      5 WUs      4 WUs     3 WUs
55 tests    35-45      35-45      40-50       40-50      35-40      25-30     15-20
```
