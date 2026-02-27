# autonomous-research-engineer

Paper-to-blueprint compiler with feasibility gate for the metis-platform ecosystem.

## Overview

The Autonomous Research Engineer ingests research papers, classifies innovation type against the
current codebase, assesses feasibility using manifest data and dependency analysis, and produces
ADR-005 WU-defined blueprints for CC agent execution.

## Architecture

Five-stage pipeline: Comprehension → Classification → Feasibility → Translation → Calibration.

Uses **classifier-compiler planning** with **decidable verification** (Stratum II architecture
from agent-factors).

## Setup

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

## Blueprint

See `../clearinghouse/plans/2026-02-27_1832_autonomous_research_engineer_blueprint.md` for the
full implementation blueprint (38 WUs, 8 phases).
