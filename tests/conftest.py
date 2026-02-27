"""Foundation fixtures for autonomous-research-engineer test suite."""

from pathlib import Path

import pytest


# ── Path fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def repo_root() -> Path:
    """Root of the autonomous-research-engineer repo."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def package_root(repo_root: Path) -> Path:
    """Root of the research_engineer Python package."""
    return repo_root / "research_engineer"


@pytest.fixture
def clearinghouse_root(repo_root: Path) -> Path:
    """Root of the clearinghouse repo (sibling directory)."""
    return repo_root.parent / "clearinghouse"


@pytest.fixture
def agent_factors_root(repo_root: Path) -> Path:
    """Root of the agent-factors repo (sibling directory)."""
    return repo_root.parent / "agent-factors"


@pytest.fixture
def clearinghouse_ledger(clearinghouse_root: Path) -> Path:
    """Path to the clearinghouse ledger."""
    return clearinghouse_root / "coordination" / "ledger.jsonl"


@pytest.fixture
def clearinghouse_newsletter(clearinghouse_root: Path) -> Path:
    """Path to the current clearinghouse newsletter."""
    return clearinghouse_root / "coordination" / "newsletter" / "current.md"


@pytest.fixture
def clearinghouse_state(clearinghouse_root: Path) -> Path:
    """Path to the clearinghouse state summary."""
    return clearinghouse_root / "coordination" / "state" / "current_state.yaml"


@pytest.fixture
def clearinghouse_schemas(clearinghouse_root: Path) -> Path:
    """Path to the clearinghouse schemas directory."""
    return clearinghouse_root / "schemas"


@pytest.fixture
def clearinghouse_manifests(clearinghouse_root: Path) -> Path:
    """Path to the clearinghouse manifests directory."""
    return clearinghouse_root / "manifests"


@pytest.fixture
def clearinghouse_algorithms(clearinghouse_root: Path) -> Path:
    """Path to the clearinghouse Pattern Library."""
    return clearinghouse_root / "algorithms"


# ── Temporary directory fixtures ─────────────────────────────────────────────

@pytest.fixture
def tmp_comprehension_dir(tmp_path: Path) -> Path:
    """Temporary directory for comprehension test data."""
    d = tmp_path / "comprehension"
    d.mkdir()
    return d


@pytest.fixture
def tmp_classifier_dir(tmp_path: Path) -> Path:
    """Temporary directory for classifier test data."""
    d = tmp_path / "classifier"
    d.mkdir()
    return d


@pytest.fixture
def tmp_feasibility_dir(tmp_path: Path) -> Path:
    """Temporary directory for feasibility gate test data."""
    d = tmp_path / "feasibility"
    d.mkdir()
    return d


@pytest.fixture
def tmp_translator_dir(tmp_path: Path) -> Path:
    """Temporary directory for translator output."""
    d = tmp_path / "translator"
    d.mkdir()
    return d


@pytest.fixture
def tmp_calibration_dir(tmp_path: Path) -> Path:
    """Temporary directory for calibration data."""
    d = tmp_path / "calibration"
    d.mkdir()
    return d


# ── Sample data fixtures ────────────────────────────────────────────────────

@pytest.fixture
def sample_paper_text() -> str:
    """Minimal synthetic paper text for testing comprehension pipeline."""
    return """\
Title: Learned Sparse Representations for Multi-Hop Retrieval

Abstract: We propose replacing BM25 sparse retrieval with learned sparse
representations using SPLADE. Our approach produces sparse term-weight vectors
compatible with inverted index lookup, achieving +36.7% MRR@10 on multi-hop
queries compared to BM25 baseline.

Method: The technique uses a pre-trained language model to generate sparse
term weights. Each query is decomposed into sub-queries, with per-sub-query
retrieval and aggregation via reciprocal rank fusion.

Results: On the multi-hop subset of Natural Questions, our method achieves
MRR@10 of 0.847 compared to BM25 baseline of 0.620.

Limitations: Evaluated only on English Wikipedia passages. Requires a trained
sparse encoder model (~110M parameters).
"""


@pytest.fixture
def sample_parameter_tuning_text() -> str:
    """Synthetic paper text representing a parameter tuning innovation."""
    return """\
Title: Optimal RRF Weight Selection for Hybrid Retrieval

Abstract: We investigate the effect of reciprocal rank fusion weight parameter
k on hybrid BM25+dense retrieval quality. Through grid search over k in [1,100],
we find k=42 yields optimal MRR@10 on BEIR benchmark.

Method: Standard RRF formula with varying k parameter applied to existing
BM25 and dense retrieval scores. No architectural changes required.

Results: k=42 improves MRR@10 by 2.3% over default k=60 across 13 BEIR datasets.

Limitations: Optimal k may vary by domain. Evaluation limited to BEIR benchmark.
"""


@pytest.fixture
def sample_architectural_text() -> str:
    """Synthetic paper text representing an architectural innovation."""
    return """\
Title: Knowledge Graph Construction from Retrieved Passages

Abstract: We propose a novel pipeline stage that constructs a knowledge graph
from retrieved passages before answer generation. This introduces a new
intermediate representation between retrieval and generation stages.

Method: A graph construction module extracts entities and relations from
retrieved passages, builds a knowledge graph, and feeds graph-structured
context to the generator. This requires a new evaluation methodology for
graph quality assessment.

Results: The knowledge graph intermediate representation improves factual
accuracy by 18.4% on complex multi-hop questions.

Limitations: Graph construction adds 340ms latency per query. Requires
entity linking model not currently in the pipeline.
"""
