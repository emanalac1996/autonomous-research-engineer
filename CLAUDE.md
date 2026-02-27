# autonomous-research-engineer

Paper-to-blueprint compiler with feasibility gate for the metis-platform ecosystem.
This agent ingests research papers, classifies innovation type, assesses feasibility against
live codebase state, and produces ADR-005 WU-defined blueprints.

The orientation document for all sibling repos is at `../clearinghouse/onboarding/cc_agent_orientation.md`.
That document tells agents how to read the ledger, use manifests, and write entries.
This CLAUDE.md is for agents working *inside* autonomous-research-engineer itself.

## What autonomous-research-engineer Contains

| Directory | Purpose | Editable? |
|-----------|---------|-----------|
| `research_engineer/comprehension/` | Stage 1: paper parsing, schema, topology change detection | CC-authored |
| `research_engineer/classifier/` | Stage 2: innovation-type classification with artifact-backed heuristics | CC-authored |
| `research_engineer/feasibility/` | Stage 3: feasibility gate, dependency graph, blast radius analysis | CC-authored |
| `research_engineer/translator/` | Stage 4: blueprint translation, WU decomposition, change patterns | CC-authored |
| `research_engineer/calibration/` | Stage 5: accuracy tracking, maturity gating, heuristic evolution | CC-authored |
| `scripts/` | CLI tools (evaluate_paper, check_feasibility, build_dep_graph, calibration_report) | CC-authored |
| `tests/` | pytest suite | CC-authored |

## Startup Protocol

At the start of every session, before doing anything else:

1. **Read the newsletter** — `../clearinghouse/coordination/newsletter/current.md`
2. **Read the ledger** — `../clearinghouse/coordination/ledger.jsonl`
   - Filter for entries where `autonomous-research-engineer` appears in `affected_repos`
3. **Read the state summary** — `../clearinghouse/coordination/state/current_state.yaml`
4. **Check for relevant manifests** — `../clearinghouse/manifests/`

## Environment

```bash
cd /Users/ericmiguelmanalac/Desktop/metis-platform/autonomous-research-engineer
pip install -e ".[dev]"
python -m pytest tests/
```

## Dependencies

- **pydantic>=2.0** — all Pydantic v2 models (comprehension schema, classification types, etc.)
- **pyyaml>=6.0** — YAML loading for heuristic artifacts and configuration
- **agent-factors** — governance infrastructure (g-layer, catalog, artifacts, DAG validation)
- **networkx>=3.0** (optional) — codebase dependency graph in feasibility gate

## Stratum II Architecture

This agent uses **classifier-compiler planning** with **decidable verification** — the simplest
of the three agent archetypes. The 4-type diagnostic tree is shallow and categorical.
Every stage output is verifiable against concrete criteria (schema compliance, manifest existence,
DAG acyclicity, calibration accuracy). No subjective quality judgments.

| Innovation Type | Planning Complexity | Verification |
|-----------------|--------------------| -------------|
| Parameter tuning | Manifest-only operations → 1-3 WUs | Decidable: config change + regression test |
| Modular swap | Single-component ablation → 3-5 WUs | Decidable: interface compatibility |
| Pipeline restructuring | Topology change → 5-12 WUs | Decidable: contract + blast radius check |
| Architectural innovation | New primitives → 8-20 WUs | Decidable: DAG acyclicity + gate checks |

## agent-factors Integration

This repo consumes agent-factors models — it never redefines them:

| What | Import | Purpose |
|------|--------|---------|
| g-layer protocol | `agent_factors.g_layer` | Maturity gating, escalation, honest refusal |
| Catalog patterns | `agent_factors.catalog` | classifier-compiler, decidable-verification lookups |
| Artifact registry | `agent_factors.artifacts` | Heuristic storage, versioning, hot-swap |
| DAG validation | `agent_factors.dag` | Blueprint WU DAG validation, critical path analysis |

## Consuming Clearinghouse Data

| What | Path | How |
|------|------|-----|
| Newsletter | `../clearinghouse/coordination/newsletter/current.md` | Read on startup |
| Ledger | `../clearinghouse/coordination/ledger.jsonl` | Read on startup, write at task boundaries |
| State | `../clearinghouse/coordination/state/current_state.yaml` | Read for orientation |
| Manifests | `../clearinghouse/manifests/` | Feasibility gate input (repo API surfaces) |
| Pattern Library | `../clearinghouse/algorithms/` | Vocabulary mapping (paper terms → patterns) |
| Schemas | `../clearinghouse/schemas/` | Reference for shared types |

## Conventions

- Python >=3.11
- Pydantic v2 for all models
- Ledger entries: always use `../clearinghouse/scripts/ledger_lock.py`, never direct file edit
- Blueprints: ADR-005 format with Working Units, stored in `../clearinghouse/plans/`
- Timestamped files: always query `date +%H%M` for the HHMM portion
- Logs: `updates/logs/MM-DD-YYYY/HHMM_description.md`
- Documentation ordering after implementation: session log → architecture doc → ledger entry → commit/push

## Blueprint

The implementation blueprint is at `../clearinghouse/plans/2026-02-27_1832_autonomous_research_engineer_blueprint.md`.
38 Working Units across 8 phases, 233-292 tests estimated.
