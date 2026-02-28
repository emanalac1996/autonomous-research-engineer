# Full System Architecture — 2026-02-28

## Overview

The autonomous-research-engineer is a **paper-to-blueprint compiler** with a feasibility
gate. It ingests research papers (text, structured documents, or video presentations),
classifies the innovation type, assesses feasibility against live codebase state, and
produces ADR-005 WU-defined blueprints.

It uses the simplest **Stratum II architecture**: classifier-compiler planning with
decidable verification. Every stage output is verifiable against concrete criteria
(schema compliance, manifest existence, DAG acyclicity, calibration accuracy).

## Current State: Phases 0–7 Complete

| Metric | Value |
|--------|-------|
| Package | `research_engineer` v0.1.0 |
| Tests | **361 passing** |
| Source modules | 27 (+ 6 `__init__.py`) |
| Test files | 36 |
| Public exports | 94 symbols across 6 subpackages |
| CLI scripts | 5 |
| Conftest fixtures | 47 |
| Dependencies | pydantic>=2.0, pyyaml>=6.0, agent-factors, prior-art-retrieval (opt), multimodal-rag-core (opt), networkx>=3.0 (opt) |

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          research_engineer package                                │
│                                                                                  │
│  INPUTS                                                                          │
│    │                                                                             │
│    ├─── Plaintext paper ──────────────────────────────┐                          │
│    ├─── SourceDocument (prior-art-retrieval) ─────────┤                          │
│    └─── VideoPipelineOutput (multimodal-rag-core) ────┤                          │
│                                                        │                          │
│    ┌───────────────────────────────────────────────────┘                          │
│    │                                                                             │
│    ▼                                                                             │
│  comprehension/          Stage 1: Input → ComprehensionSummary                   │
│    ├── schema.py         PaperSection, PaperClaim, MathCore, ComprehensionSummary│
│    ├── parser.py         Section extraction, claim/math/term/transformation      │
│    ├── topology.py       TopologyChange detection (5 change types)               │
│    └── vocabulary.py     Paper term → codebase pattern vocabulary mapping        │
│    │                                                                             │
│    ▼                                                                             │
│  classifier/             Stage 2: Summary → ClassificationResult                 │
│    ├── types.py          InnovationType enum (4 types) + ClassificationResult    │
│    ├── heuristics.py     Artifact-backed keyword rules (YAML, hot-swappable)     │
│    ├── confidence.py     Multi-signal confidence scoring + escalation triggers   │
│    └── seed_artifact.py  Default heuristic YAML registration                    │
│    │                                                                             │
│    ▼                                                                             │
│  feasibility/            Stage 3: Classification → FeasibilityResult             │
│    ├── manifest_checker.py   Function-level manifest matching                    │
│    ├── dependency_graph.py   NetworkX codebase dependency graph                  │
│    ├── blast_radius.py       Transitive impact analysis per innovation type      │
│    ├── test_coverage.py      Test coverage gap assessment                        │
│    └── gate.py               Orchestrator (gate depth varies by innovation type) │
│    │                                                                             │
│    ├──── if NOT_FEASIBLE ──► log_refusal() + exit                               │
│    ▼                                                                             │
│  translator/             Stage 4: Feasible → ADR-005 Blueprint                   │
│    ├── manifest_targeter.py  File targeting from manifest function signatures    │
│    ├── change_patterns.py    Historical ledger mining for change patterns        │
│    ├── wu_decomposer.py      Innovation type → WU DAG decomposition             │
│    ├── translator.py         Full translation pipeline orchestration             │
│    └── serializer.py         ADR-005 Markdown + YAML serialization              │
│    │                                                                             │
│    ▼                                                                             │
│  calibration/            Stage 5: Ongoing accuracy tracking + self-improvement   │
│    ├── tracker.py            Per-stage accuracy with JSONL persistence           │
│    ├── maturity_assessor.py  MaturityGate integration + promotion eligibility    │
│    ├── heuristic_evolver.py  Misclassification → mutation → YAML hot-swap       │
│    └── report.py             JSON + Markdown calibration reports                 │
│    │                                                                             │
│    ▼                                                                             │
│  integration/            Stage 6+7: Upstream source adapters                     │
│    ├── adapter.py            SourceDocument → ComprehensionSummary (Phase 6)     │
│    ├── batch_pipeline.py     N papers → evaluate → aggregate + JSONL ledger      │
│    ├── manifest_freshness.py Manifest age checking + staleness warnings          │
│    ├── video_adapter.py      VideoPipelineOutput → ComprehensionSummary (Phase 7)│
│    └── video_comprehension.py  Topology signals from visual slides              │
│                                                                                  │
│  OUTPUT: ADR-005 WU-defined blueprint                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Three Input Paths

```
Plaintext               SourceDocument            VideoPipelineOutput
(parser.py)             (prior-art-retrieval)     (multimodal-rag-core)
    │                        │                          │
    │  extract_sections()    │  adapt_source_document() │  adapt_video_pipeline_output()
    │  extract_claims()      │  content_block →         │  slide description keyword →
    │  extract_math_core()   │    PaperSection mapping  │    SectionType mapping
    │                        │  enrich_paper_terms()    │  segment fallback path
    │                        │                          │  extract_topology_signals()
    │                        │                          │  augment_sections_with_visual_weight()
    │                        │                          │
    └────────────┬───────────┴──────────────────────────┘
                 │
                 ▼
         ComprehensionSummary
         (unified intermediate representation)
                 │
                 ▼
         analyze_topology() → TopologyChange
                 │
                 ▼
         classify() → ClassificationResult
                 │
                 ▼
         assess_feasibility() → FeasibilityResult
                 │
                 ▼
         translate() → ADR-005 Blueprint
```

## Innovation Type × Gate Depth Matrix

| Innovation Type | Manifest Check | Interface Compat | Blast Radius | Full Analysis | WU Count |
|-----------------|:-:|:-:|:-:|:-:|---------|
| parameter_tuning | **x** | | | | 1–3 |
| modular_swap | **x** | **x** | | | 3–5 |
| pipeline_restructuring | **x** | **x** | **x** | | 5–12 |
| architectural_innovation | **x** | **x** | **x** | **x** | 8–20 |

## Topology Change Detection

`analyze_topology()` classifies papers into 5 change types via keyword matching
on transformation_proposed + abstract/method sections:

| TopologyChangeType | Meaning | Keyword Examples |
|--------------------|---------|-----------------|
| `none` | No structural change | parameter, tuning, hyperparameter |
| `component_swap` | Replace existing component | replace, swap, substitute |
| `stage_addition` | Add new pipeline stage | new stage, intermediate representation |
| `stage_removal` | Remove pipeline stage | remove, eliminate, bypass |
| `flow_restructuring` | Change data flow | restructure, reorder, new data flow |

Video pipeline integration (Phase 7) adds visual topology signals — architecture
diagram slides are detected and their descriptions enrich section content for
the topology analyzer.

## Dependency Map

```
autonomous-research-engineer
    │
    ├── agent-factors (required pip dependency)
    │   ├── g_layer/    → MaturityGate, escalation, log_refusal()
    │   ├── catalog/    → CatalogLoader (classifier-compiler, decidable-verification)
    │   ├── artifacts/  → ArtifactRegistry (heuristic YAML storage, versioning, hot-swap)
    │   └── dag/        → Blueprint, WorkingUnit, validate_dag(), critical_path()
    │
    ├── prior-art-retrieval (optional, integration extra)
    │   └── SourceDocument, ContentBlock, Classifications, QualitySignals
    │       → Paper ingestion from arXiv, USPTO, generic sources
    │
    ├── multimodal-rag-core (optional, video extra)
    │   └── SlideTranscript, SegmentTranscript, UniqueSlide (mirrored, not imported)
    │       → Conference talk video ingestion
    │
    └── clearinghouse (sibling repo, read-only except ledger writes)
        ├── manifests/           → Repository API surface manifests (feasibility input)
        ├── algorithms/          → Pattern Library (paper term → codebase pattern)
        ├── coordination/ledger  → Historical change patterns + ledger writes
        ├── coordination/newsletter → Ecosystem status
        ├── coordination/state   → Current repository states
        └── schemas/             → Shared Pydantic types
```

## Subpackage Export Summary

| Subpackage | Modules | Public Symbols | Key Exports |
|------------|---------|----------------|-------------|
| comprehension | 4 | 11 | ComprehensionSummary, parse_paper, analyze_topology |
| classifier | 4 | 8 | classify, InnovationType, ClassificationResult |
| feasibility | 5 | 18 | assess_feasibility, build_dependency_graph, compute_blast_radius |
| translator | 5 | 13 | translate, decompose, serialize_blueprint |
| calibration | 4 | 16 | AccuracyTracker, assess_maturity, apply_evolution, generate_report |
| integration | 5 | 24 | adapt_source_document, evaluate_batch, adapt_video_pipeline_output, build_video_comprehension_summary |
| **Total** | **27** | **94** | |

## CLI Scripts

| Script | Purpose |
|--------|---------|
| `scripts/evaluate_paper.py` | Evaluate a single paper through full pipeline |
| `scripts/check_feasibility.py` | Run feasibility gate on a paper |
| `scripts/build_dep_graph.py` | Build and visualize codebase dependency graph |
| `scripts/calibration_report.py` | Generate calibration accuracy report (JSON/Markdown) |
| `scripts/check_clearinghouse.py` | Verify clearinghouse data integrity |

## Test Architecture

| Phase | Test Directory | Tests | What's Tested |
|-------|---------------|-------|---------------|
| 0 | `test_foundation.py` | 55 | Package structure, imports, CLI scripts, models |
| 1 | `test_comprehension/` | 45 | Schema validation, parser extraction, topology detection, vocabulary |
| 2 | `test_classifier/` | 42 | Type classification, heuristic YAML, confidence scoring, CLI |
| 3 | `test_feasibility/` | 64 | Manifest matching, dependency graph, blast radius, gate logic, CLI |
| 4 | `test_translator/` | 60 | File targeting, change patterns, WU decomposition, serialization, CLI |
| 5 | `test_calibration/` | 35 | Accuracy tracking, maturity assessment, heuristic evolution, reports |
| 6 | `test_integration/` | 27 | SourceDocument adapter, batch pipeline, manifest freshness, end-to-end |
| 7 | `test_integration/` | 18 | Video adapter, visual topology signals, video end-to-end |
| | **Total** | **361** | |

47 conftest fixtures organized by phase, providing synthetic papers, classifications,
topologies, source documents, video pipeline outputs, and temporary directories.

## Directory Structure

```
autonomous-research-engineer/
├── research_engineer/
│   ├── __init__.py                 v0.1.0
│   ├── comprehension/              Stage 1: 4 modules, 11 exports
│   │   ├── schema.py               PaperSection, ComprehensionSummary, MathCore, PaperClaim
│   │   ├── parser.py               extract_sections, extract_claims, extract_math_core, ...
│   │   ├── topology.py             analyze_topology, TopologyChange, TopologyChangeType
│   │   └── vocabulary.py           VocabularyMapping, build_vocabulary_mapping
│   ├── classifier/                 Stage 2: 4 modules, 8 exports
│   │   ├── types.py                InnovationType (4 types), ClassificationResult
│   │   ├── heuristics.py           classify() — artifact-backed keyword rules
│   │   ├── confidence.py           compute_confidence(), check_escalation()
│   │   └── seed_artifact.py        register_seed_artifact()
│   ├── feasibility/                Stage 3: 5 modules, 18 exports
│   │   ├── manifest_checker.py     load_manifest(), check_operations()
│   │   ├── dependency_graph.py     build_dependency_graph() — NetworkX
│   │   ├── blast_radius.py         compute_blast_radius() — transitive impact
│   │   ├── test_coverage.py        assess_test_coverage()
│   │   └── gate.py                 assess_feasibility() — type-dependent depth
│   ├── translator/                 Stage 4: 5 modules, 13 exports
│   │   ├── manifest_targeter.py    identify_targets() — file targeting
│   │   ├── change_patterns.py      mine_ledger() — historical patterns
│   │   ├── wu_decomposer.py        decompose() — innovation type → WU DAG
│   │   ├── translator.py           translate() — full pipeline orchestration
│   │   └── serializer.py           serialize_blueprint(), write_blueprint()
│   ├── calibration/                Stage 5: 4 modules, 16 exports
│   │   ├── tracker.py              AccuracyTracker — JSONL persistence
│   │   ├── maturity_assessor.py    assess_maturity() — MaturityGate
│   │   ├── heuristic_evolver.py    analyze_misclassifications(), apply_evolution()
│   │   └── report.py               generate_report(), render_markdown()
│   └── integration/                Stage 6+7: 5 modules, 24 exports
│       ├── adapter.py              adapt_source_document() — SourceDocument path
│       ├── batch_pipeline.py       evaluate_batch() — N papers + JSONL ledger
│       ├── manifest_freshness.py   check_manifest_freshness() — staleness warnings
│       ├── video_adapter.py        adapt_video_pipeline_output() — video path
│       └── video_comprehension.py  build_video_comprehension_summary() + topology signals
├── scripts/                        5 CLI tools
├── tests/                          36 test files, 47 fixtures, 361 tests
│   ├── conftest.py
│   ├── test_foundation.py
│   ├── test_comprehension/         6 files
│   ├── test_classifier/            6 files
│   ├── test_feasibility/           7 files
│   ├── test_translator/            7 files
│   ├── test_calibration/           6 files
│   └── test_integration/           8 files
├── plans/                          Phase implementation plans
├── updates/
│   ├── architecture/               Per-phase + system architecture docs
│   ├── logs/                       Session logs by date
│   └── strategy/                   Strategic planning docs
├── CLAUDE.md                       Agent instructions
├── pyproject.toml                  Package config + optional deps
└── README.md
```

## Phase Build History

| Phase | Commit | Date | WUs | New Tests | Cumulative | Focus |
|-------|--------|------|-----|-----------|------------|-------|
| 0 | `c0044fa` | 2026-02-27 | 4 | 55 | 55 | Package skeleton + foundation |
| 1 | `c0044fa` | 2026-02-27 | 5 | 102 | 157 | Comprehension pipeline |
| 2 | `c0044fa` | 2026-02-27 | 5 | — | 157 | Innovation classifier |
| 3 | `2cf1e0e` | 2026-02-27 | 6 | 64 | 243* | Feasibility gate + dep graph |
| 4 | `9a3cb5c` | 2026-02-27 | 6 | 60 | 281 | Blueprint translator |
| 5 | `18f7cc6` | 2026-02-27 | 5 | 35 | 316 | Calibration + accuracy |
| 6 | `a643c30` | 2026-02-28 | 4 | 27 | 343 | prior-art-retrieval integration |
| 7 | `9e63276` | 2026-02-28 | 3 | 18 | 361 | multimodal-rag-core video pipeline |

*Phase 3 test count includes some Phase 2 tests that were added in the same build session.

## Key Design Principles

1. **Decidable verification** — Every stage output is verifiable against concrete criteria:
   schema compliance, manifest existence, DAG acyclicity, calibration accuracy.

2. **Mirror models over hard imports** — Integration adapters define local Pydantic models
   matching upstream types (SlideData, SegmentTranscriptData) rather than importing directly.
   This keeps upstream repos as optional dependencies.

3. **Unified intermediate representation** — All three input paths (plaintext, SourceDocument,
   VideoPipelineOutput) converge to `ComprehensionSummary`, ensuring a single downstream
   pipeline for classification → feasibility → translation.

4. **Innovation-type-dependent depth** — Feasibility analysis depth scales with innovation
   complexity: parameter tuning gets a manifest check, architectural innovation gets full
   blast radius + DAG analysis.

5. **Artifact-backed heuristics** — Classification rules are stored as versioned YAML
   artifacts via agent-factors ArtifactRegistry, enabling hot-swap and self-evolution
   through the calibration pipeline.

6. **Parser function reuse** — The same extraction functions (extract_claims, extract_math_core,
   etc.) are called by all three input adapters, ensuring consistent comprehension quality
   regardless of source.
