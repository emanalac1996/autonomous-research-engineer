# Phase 0 Implementation Plan: Repo Skeleton + g-Layer Bootstrap

**Date:** 2026-02-27 18:32
**Status:** Complete
**Blueprint ref:** `clearinghouse/plans/2026-02-27_1832_autonomous_research_engineer_blueprint.md` — Section 4

---

## Scope

Establish the autonomous-research-engineer repo with project structure, clearinghouse
integration, agent-factors integration, and foundation test suite. All 4 Working Units
from Phase 0 of the autonomous-research-engineer blueprint.

## Working Units

| WU | Description | Depends On | Acceptance Criteria |
|----|-------------|------------|---------------------|
| 0.1 | Scaffold repo: `autonomous-research-engineer/` with `research_engineer/` package (comprehension, classifier, feasibility, translator, calibration subpackages), `tests/`, `scripts/`, `pyproject.toml` (pydantic>=2.0, pyyaml>=6.0, agent-factors as dependency), CLAUDE.md, README.md | — | `pip install -e .` succeeds; `python -c "import research_engineer"` succeeds; `pytest tests/` runs with no errors |
| 0.2 | Clearinghouse integration: `scripts/check_clearinghouse.py` reads newsletter, filters ledger for `autonomous-research-engineer` in `affected_repos`, reads state summary; CLAUDE.md contains startup protocol per `cc_agent_orientation.md` | WU 0.1 | Integration script reads newsletter, ledger, and state without error; CLAUDE.md matches orientation conventions |
| 0.3 | agent-factors integration: verify `import agent_factors.g_layer`, `import agent_factors.catalog`, `import agent_factors.artifacts`, `import agent_factors.dag` all succeed; conftest.py fixtures for agent-factors paths and catalog loader | WU 0.1 | All agent-factors subpackage imports succeed; fixtures resolve paths correctly |
| 0.4 | Ledger registration entry via `scripts/ledger_lock.py`: register autonomous-research-engineer as pipeline repo with `meta_category: "pipeline"` | WU 0.2 | Ledger entry written; `regenerate_state.py` includes autonomous-research-engineer |

## Key Decisions

1. **Package name:** `research_engineer` (matching repo name `autonomous-research-engineer`)
2. **Build backend:** `setuptools.build_meta` (standard PEP 517)
3. **Python version:** >=3.11 (ecosystem convention)
4. **Dependencies:** pydantic>=2.0, pyyaml>=6.0, agent-factors (editable from `../agent-factors`)
5. **Clearinghouse integration:** `scripts/check_clearinghouse.py` with `--newsletter`, `--ledger`, `--state` flags
6. **Subpackages:** 5 stages mapping to pipeline (comprehension, classifier, feasibility, translator, calibration)
7. **Test fixtures:** 3 sample paper texts (parameter tuning, modular swap, architectural innovation) in conftest.py for Phase 1+ testing

## Results

- 55 tests passing (7 imports, 8 structure, 6 subpackages, 8 agent-factors integration, 7 clearinghouse connectivity, 10 fixtures, 3 script validation, 6 CLAUDE.md content)
- Ledger entry `ledger-2026-02-27-142` written
- Pushed to `https://github.com/emanalac1996/autonomous-research-engineer` on `main`
