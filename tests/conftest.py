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


# ── ComprehensionSummary fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_parameter_tuning_summary():
    """Pre-built ComprehensionSummary for parameter tuning paper."""
    from research_engineer.comprehension.schema import (
        ComprehensionSummary,
        MathCore,
        PaperClaim,
    )

    return ComprehensionSummary(
        title="Optimal RRF Weight Selection for Hybrid Retrieval",
        transformation_proposed=(
            "Adjust reciprocal rank fusion weight parameter k "
            "from default k=60 to optimal k=42"
        ),
        inputs_required=["BM25 retrieval scores", "dense retrieval scores"],
        outputs_produced=["re-ranked result list with adjusted RRF weights"],
        claims=[
            PaperClaim(
                claim_text=(
                    "k=42 improves MRR@10 by 2.3% over default k=60 "
                    "across 13 BEIR datasets"
                ),
                metric_name="MRR@10",
                metric_value=2.3,
                baseline_comparison=0.0,
                dataset="BEIR",
            ),
        ],
        limitations=[
            "Optimal k may vary by domain",
            "Evaluation limited to BEIR benchmark",
        ],
        mathematical_core=MathCore(
            formulation="RRF(d) = sum(1 / (k + rank_i(d))) for retriever i",
            complexity="O(n log n) for sorting n results",
            assumptions=["Scores from both retrievers are comparable in scale"],
        ),
        paper_terms=[
            "reciprocal rank fusion",
            "BM25",
            "dense retrieval",
            "hybrid retrieval",
            "MRR@10",
        ],
    )


@pytest.fixture
def sample_modular_swap_summary():
    """Pre-built ComprehensionSummary for modular swap paper (learned sparse)."""
    from research_engineer.comprehension.schema import (
        ComprehensionSummary,
        MathCore,
        PaperClaim,
    )

    return ComprehensionSummary(
        title="Learned Sparse Representations for Multi-Hop Retrieval",
        transformation_proposed=(
            "Replace BM25 sparse retrieval with learned sparse "
            "representations using SPLADE"
        ),
        inputs_required=[
            "query text",
            "pre-trained language model",
            "inverted index",
        ],
        outputs_produced=[
            "sparse term-weight vectors",
            "retrieval results via inverted index lookup",
        ],
        claims=[
            PaperClaim(
                claim_text=(
                    "Achieves +36.7% MRR@10 on multi-hop queries "
                    "compared to BM25 baseline"
                ),
                metric_name="MRR@10",
                metric_value=0.847,
                baseline_comparison=0.620,
                dataset="Natural Questions (multi-hop subset)",
            ),
        ],
        limitations=[
            "Evaluated only on English Wikipedia passages",
            "Requires trained sparse encoder model (~110M parameters)",
        ],
        mathematical_core=MathCore(
            formulation=(
                "Sparse term weights from pre-trained language model; "
                "per-sub-query retrieval with RRF aggregation"
            ),
            complexity=None,
            assumptions=[
                "Pre-trained language model available",
                "Inverted index infrastructure exists",
            ],
        ),
        paper_terms=[
            "SPLADE",
            "sparse retrieval",
            "learned sparse representations",
            "BM25",
            "inverted index",
            "multi-hop",
            "reciprocal rank fusion",
        ],
    )


@pytest.fixture
def sample_architectural_summary():
    """Pre-built ComprehensionSummary for architectural innovation paper."""
    from research_engineer.comprehension.schema import (
        ComprehensionSummary,
        MathCore,
        PaperClaim,
    )

    return ComprehensionSummary(
        title="Knowledge Graph Construction from Retrieved Passages",
        transformation_proposed=(
            "Introduce a new pipeline stage that constructs a knowledge graph "
            "from retrieved passages before answer generation"
        ),
        inputs_required=[
            "retrieved passages",
            "entity linking model",
            "relation extraction model",
        ],
        outputs_produced=[
            "knowledge graph",
            "graph-structured context for generator",
        ],
        claims=[
            PaperClaim(
                claim_text=(
                    "Knowledge graph intermediate representation improves "
                    "factual accuracy by 18.4% on complex multi-hop questions"
                ),
                metric_name="factual_accuracy",
                metric_value=18.4,
                dataset="complex multi-hop questions",
            ),
        ],
        limitations=[
            "Graph construction adds 340ms latency per query",
            "Requires entity linking model not currently in the pipeline",
        ],
        mathematical_core=MathCore(
            formulation=(
                "Entity-relation extraction followed by graph construction; "
                "graph-structured context fed to generator"
            ),
            complexity="O(n*m) where n=passages, m=entities per passage",
            assumptions=[
                "Entity linking model is available",
                "Relations are extractable from text",
            ],
        ),
        paper_terms=[
            "knowledge graph",
            "entity linking",
            "relation extraction",
            "graph construction",
            "intermediate representation",
            "answer generation",
        ],
    )


# ── Phase 2: Classifier fixtures ─────────────────────────────────────────────

@pytest.fixture
def tmp_artifact_registry(tmp_path: Path):
    """Empty ArtifactRegistry backed by a temporary directory."""
    from agent_factors.artifacts import ArtifactRegistry

    store_dir = tmp_path / "artifact_store"
    store_dir.mkdir()
    return ArtifactRegistry(store_dir=store_dir)


@pytest.fixture
def seeded_artifact_registry(tmp_artifact_registry):
    """ArtifactRegistry with the seed classification heuristic pre-loaded."""
    from research_engineer.classifier.seed_artifact import register_seed_artifact

    register_seed_artifact(tmp_artifact_registry)
    return tmp_artifact_registry


@pytest.fixture
def sample_topology_none():
    """TopologyChange with no topology change detected."""
    from research_engineer.comprehension.topology import (
        TopologyChange,
        TopologyChangeType,
    )

    return TopologyChange(
        change_type=TopologyChangeType.none,
        affected_stages=[],
        confidence=0.67,
        evidence=["no_topology keyword: 'parameter'"],
    )


@pytest.fixture
def sample_topology_component_swap():
    """TopologyChange for a component swap."""
    from research_engineer.comprehension.topology import (
        TopologyChange,
        TopologyChangeType,
    )

    return TopologyChange(
        change_type=TopologyChangeType.component_swap,
        affected_stages=["retrieval"],
        confidence=0.67,
        evidence=["component_swap keyword: 'replace'"],
    )


@pytest.fixture
def sample_topology_stage_addition():
    """TopologyChange for a stage addition."""
    from research_engineer.comprehension.topology import (
        TopologyChange,
        TopologyChangeType,
    )

    return TopologyChange(
        change_type=TopologyChangeType.stage_addition,
        affected_stages=["retrieval", "generation", "graph construction"],
        confidence=0.67,
        evidence=["stage_addition keyword: 'new pipeline stage'"],
    )


@pytest.fixture
def sample_pipeline_restructuring_summary():
    """Pre-built ComprehensionSummary for pipeline restructuring paper."""
    from research_engineer.comprehension.schema import (
        ComprehensionSummary,
        MathCore,
        PaperClaim,
    )

    return ComprehensionSummary(
        title="Restructured Retrieval Pipeline with Reordered Reranking",
        transformation_proposed=(
            "Restructure the retrieval pipeline to reorder the reranking "
            "stage before the generation stage, changing the data flow "
            "to improve answer quality"
        ),
        inputs_required=[
            "query text",
            "retrieval results",
            "reranking model",
        ],
        outputs_produced=[
            "reordered retrieval results",
            "improved generation context",
        ],
        claims=[
            PaperClaim(
                claim_text=(
                    "Reordering reranking before generation improves "
                    "answer accuracy by 12.1%"
                ),
                metric_name="answer_accuracy",
                metric_value=12.1,
                dataset="NQ-open",
            ),
        ],
        limitations=[
            "Adds additional latency from reranking step",
            "Requires reranking model not in current pipeline",
        ],
        mathematical_core=MathCore(
            formulation="Reranking scores feed directly into generation context",
            complexity="O(n log n) for reranking n passages",
            assumptions=["Reranking model is available"],
        ),
        paper_terms=[
            "reranking",
            "retrieval",
            "generation",
            "pipeline restructuring",
        ],
    )


# ── Phase 4: Translator fixtures ────────────────────────────────────────────

@pytest.fixture
def sample_classification_parameter_tuning(
    sample_parameter_tuning_summary,
    sample_topology_none,
    seeded_artifact_registry,
):
    """ClassificationResult for parameter tuning via classify()."""
    from research_engineer.classifier.heuristics import classify

    return classify(
        sample_parameter_tuning_summary,
        sample_topology_none,
        [],
        seeded_artifact_registry,
    )


@pytest.fixture
def sample_classification_modular_swap(
    sample_modular_swap_summary,
    sample_topology_component_swap,
    seeded_artifact_registry,
):
    """ClassificationResult for modular swap via classify()."""
    from research_engineer.classifier.heuristics import classify

    return classify(
        sample_modular_swap_summary,
        sample_topology_component_swap,
        [],
        seeded_artifact_registry,
    )


@pytest.fixture
def sample_classification_architectural(
    sample_architectural_summary,
    sample_topology_stage_addition,
    seeded_artifact_registry,
):
    """ClassificationResult for architectural innovation via classify()."""
    from research_engineer.classifier.heuristics import classify

    return classify(
        sample_architectural_summary,
        sample_topology_stage_addition,
        [],
        seeded_artifact_registry,
    )


@pytest.fixture
def sample_classification_pipeline_restructuring(
    sample_pipeline_restructuring_summary,
    sample_topology_flow_restructuring,
    seeded_artifact_registry,
):
    """ClassificationResult for pipeline restructuring via classify()."""
    from research_engineer.classifier.heuristics import classify

    return classify(
        sample_pipeline_restructuring_summary,
        sample_topology_flow_restructuring,
        [],
        seeded_artifact_registry,
    )


@pytest.fixture
def sample_topology_flow_restructuring():
    """TopologyChange with flow_restructuring change type."""
    from research_engineer.comprehension.topology import (
        TopologyChange,
        TopologyChangeType,
    )

    return TopologyChange(
        change_type=TopologyChangeType.flow_restructuring,
        affected_stages=["retrieval", "reranking", "generation"],
        confidence=0.67,
        evidence=["flow_restructuring keyword: 'restructure'"],
    )


@pytest.fixture
def sample_file_targeting_modular_swap(
    sample_modular_swap_summary,
    clearinghouse_manifests,
):
    """FileTargeting from identify_targets() for modular swap."""
    from research_engineer.classifier.types import InnovationType
    from research_engineer.translator.manifest_targeter import identify_targets

    return identify_targets(
        sample_modular_swap_summary,
        InnovationType.modular_swap,
        clearinghouse_manifests,
    )


@pytest.fixture
def sample_change_pattern_report(clearinghouse_ledger):
    """ChangePatternReport from mine_ledger()."""
    from research_engineer.translator.change_patterns import mine_ledger

    return mine_ledger(clearinghouse_ledger)


@pytest.fixture
def tmp_blueprint_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for blueprint output."""
    d = tmp_path / "blueprint_output"
    d.mkdir()
    return d


# ── Phase 5: Calibration fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_accuracy_records():
    """6 AccuracyRecords: 4 correct + 2 misclassified."""
    from research_engineer.calibration.tracker import AccuracyRecord
    from research_engineer.classifier.types import InnovationType

    records = []
    # 4 correct — one per innovation type
    for i, itype in enumerate(InnovationType):
        records.append(AccuracyRecord(
            paper_id=f"conftest-{i}",
            predicted_type=itype,
            ground_truth_type=itype,
            confidence=0.85,
        ))

    # 2 misclassifications
    records.append(AccuracyRecord(
        paper_id="conftest-miss-1",
        predicted_type=InnovationType.parameter_tuning,
        ground_truth_type=InnovationType.modular_swap,
        confidence=0.55,
    ))
    records.append(AccuracyRecord(
        paper_id="conftest-miss-2",
        predicted_type=InnovationType.pipeline_restructuring,
        ground_truth_type=InnovationType.architectural_innovation,
        confidence=0.50,
    ))

    return records


@pytest.fixture
def sample_accuracy_tracker(sample_accuracy_records, tmp_calibration_dir):
    """Pre-populated AccuracyTracker with JSONL persistence."""
    from research_engineer.calibration.tracker import AccuracyTracker

    store_path = tmp_calibration_dir / "accuracy_records.jsonl"
    tracker = AccuracyTracker(store_path=store_path)
    for record in sample_accuracy_records:
        tracker.add_record(record)
    return tracker


@pytest.fixture
def sample_calibration_input(sample_accuracy_tracker, seeded_artifact_registry):
    """Bundled CalibrationInput for report testing."""
    from research_engineer.calibration.report import CalibrationInput

    return CalibrationInput(
        tracker=sample_accuracy_tracker,
        registry=seeded_artifact_registry,
        repo_name="autonomous-research-engineer",
        current_maturity_level="foundational",
    )


# ── Phase 6: Integration fixtures ──────────────────────────────────────────

@pytest.fixture
def tmp_integration_dir(tmp_path: Path) -> Path:
    """Temporary directory for integration test data."""
    d = tmp_path / "integration"
    d.mkdir()
    return d


@pytest.fixture
def sample_source_document_arxiv():
    """Synthetic arXiv SourceDocument for testing the adapter."""
    from datetime import date, datetime, timezone

    from prior_art.schema.source_document import (
        Author,
        ContentBlock,
        SourceDocument,
        compute_content_hash,
    )
    from prior_art.schema.classifications import Classifications
    from prior_art.schema.quality import QualitySignals
    from prior_art.schema.references import References
    from prior_art.schema.source_metadata import ArxivMetadata

    blocks = [
        ContentBlock(
            block_id="arxiv:2401.12345_abstract_0",
            block_type="abstract",
            content=(
                "We propose replacing BM25 sparse retrieval with learned sparse "
                "representations using SPLADE. Our approach produces sparse term-weight "
                "vectors compatible with inverted index lookup, achieving +36.7% MRR@10 "
                "on multi-hop queries compared to BM25 baseline."
            ),
            section_label="Abstract",
            sequence=0,
        ),
        ContentBlock(
            block_id="arxiv:2401.12345_section_1",
            block_type="text",
            content=(
                "The technique uses a pre-trained language model to generate sparse "
                "term weights. Each query is decomposed into sub-queries, with "
                "per-sub-query retrieval and aggregation via reciprocal rank fusion."
            ),
            section_label="Method",
            sequence=1,
        ),
        ContentBlock(
            block_id="arxiv:2401.12345_section_2",
            block_type="text",
            content=(
                "On the multi-hop subset of Natural Questions, our method achieves "
                "MRR@10 of 0.847 compared to BM25 baseline of 0.620."
            ),
            section_label="Results",
            sequence=2,
        ),
        ContentBlock(
            block_id="arxiv:2401.12345_section_3",
            block_type="text",
            content=(
                "Evaluated only on English Wikipedia passages. Requires a trained "
                "sparse encoder model (~110M parameters)."
            ),
            section_label="Limitations",
            sequence=3,
        ),
    ]

    now = datetime.now(timezone.utc)

    return SourceDocument(
        document_id="arxiv:2401.12345",
        corpus="arxiv",
        document_type="preprint",
        title="Learned Sparse Representations for Multi-Hop Retrieval",
        canonical_url="https://arxiv.org/abs/2401.12345",
        language="en",
        publication_date=date(2024, 1, 15),
        authors=[Author(name="Alice Researcher", affiliations=["MIT"])],
        venue="arXiv",
        source_metadata=ArxivMetadata(
            arxiv_id="2401.12345",
            primary_category="cs.IR",
            all_categories=["cs.IR", "cs.CL"],
        ),
        quality=QualitySignals(
            citation_count=42,
            peer_reviewed=False,
            venue_tier="preprint",
            overall_quality_score=0.72,
        ),
        classifications=Classifications(
            tasks=["retrieval"],
            techniques=["sparse_retrieval"],
            modalities=["text"],
            keywords=["SPLADE", "learned sparse", "multi-hop"],
        ),
        references=References(),
        content_blocks=blocks,
        first_ingested=now,
        last_checked=now,
        last_content_hash=compute_content_hash(blocks),
    )


@pytest.fixture
def sample_source_document_patent():
    """Synthetic USPTO SourceDocument for testing patent adapter path."""
    from datetime import date, datetime, timezone

    from prior_art.schema.source_document import (
        Author,
        ContentBlock,
        SourceDocument,
        compute_content_hash,
    )
    from prior_art.schema.classifications import Classifications
    from prior_art.schema.quality import QualitySignals
    from prior_art.schema.references import References
    from prior_art.schema.source_metadata import USPTOMetadata

    blocks = [
        ContentBlock(
            block_id="uspto:US12345678_abstract_0",
            block_type="abstract",
            content=(
                "A method for optimizing reciprocal rank fusion weights in hybrid "
                "retrieval systems. The method adjusts the k parameter from default "
                "k=60 to an optimal value determined via grid search."
            ),
            section_label="Abstract",
            sequence=0,
        ),
        ContentBlock(
            block_id="uspto:US12345678_claim_0",
            block_type="claim",
            content=(
                "1. A computer-implemented method for optimizing hybrid retrieval "
                "quality by adjusting a fusion weight parameter k in a reciprocal "
                "rank fusion formula applied to BM25 and dense retrieval scores."
            ),
            section_label="Claims",
            sequence=1,
        ),
    ]

    now = datetime.now(timezone.utc)

    return SourceDocument(
        document_id="uspto:US12345678",
        corpus="uspto_grant",
        document_type="patent_grant",
        title="Optimal RRF Weight Selection for Hybrid Retrieval",
        canonical_url=None,
        language="en",
        publication_date=date(2024, 6, 1),
        authors=[Author(name="Bob Inventor")],
        venue=None,
        source_metadata=USPTOMetadata(
            application_number="US16/123456",
            filing_date=date(2023, 1, 15),
            grant_date=date(2024, 6, 1),
            patent_number="US12345678",
        ),
        quality=QualitySignals(
            citation_count=5,
            peer_reviewed=False,
            venue_tier="patent",
            overall_quality_score=0.55,
        ),
        classifications=Classifications(
            tasks=["retrieval"],
            techniques=["hybrid_retrieval"],
            modalities=["text"],
            keywords=["RRF", "BM25", "dense retrieval"],
        ),
        references=References(),
        content_blocks=blocks,
        first_ingested=now,
        last_checked=now,
        last_content_hash=compute_content_hash(blocks),
    )


@pytest.fixture
def sample_source_document_minimal():
    """Minimal SourceDocument with empty content_blocks for edge-case testing."""
    from datetime import datetime, timezone

    from prior_art.schema.source_document import (
        SourceDocument,
        compute_content_hash,
    )
    from prior_art.schema.classifications import Classifications
    from prior_art.schema.quality import QualitySignals
    from prior_art.schema.references import References
    from prior_art.schema.source_metadata import GenericMetadata

    now = datetime.now(timezone.utc)
    blocks: list = []

    return SourceDocument(
        document_id="other:minimal-001",
        corpus="other",
        document_type="technical_report",
        title="Minimal Document With No Content Blocks",
        language="en",
        source_metadata=GenericMetadata(),
        quality=QualitySignals(overall_quality_score=0.1),
        classifications=Classifications(),
        content_blocks=blocks,
        first_ingested=now,
        last_checked=now,
        last_content_hash=compute_content_hash(blocks),
    )


@pytest.fixture
def sample_source_documents_batch(
    sample_source_document_arxiv,
    sample_source_document_patent,
):
    """Batch of 3 SourceDocuments for batch pipeline testing."""
    from datetime import date, datetime, timezone

    from prior_art.schema.source_document import (
        Author,
        ContentBlock,
        SourceDocument,
        compute_content_hash,
    )
    from prior_art.schema.classifications import Classifications
    from prior_art.schema.quality import QualitySignals
    from prior_art.schema.references import References
    from prior_art.schema.source_metadata import ArxivMetadata

    blocks = [
        ContentBlock(
            block_id="arxiv:2402.67890_abstract_0",
            block_type="abstract",
            content=(
                "We propose a novel pipeline stage that constructs a knowledge graph "
                "from retrieved passages before answer generation. This introduces a "
                "new intermediate representation between retrieval and generation stages."
            ),
            section_label="Abstract",
            sequence=0,
        ),
        ContentBlock(
            block_id="arxiv:2402.67890_section_1",
            block_type="text",
            content=(
                "A graph construction module extracts entities and relations from "
                "retrieved passages, builds a knowledge graph, and feeds graph-structured "
                "context to the generator. This requires a new evaluation methodology."
            ),
            section_label="Method",
            sequence=1,
        ),
        ContentBlock(
            block_id="arxiv:2402.67890_section_2",
            block_type="text",
            content=(
                "The knowledge graph intermediate representation improves factual "
                "accuracy by 18.4% on complex multi-hop questions."
            ),
            section_label="Results",
            sequence=2,
        ),
        ContentBlock(
            block_id="arxiv:2402.67890_section_3",
            block_type="text",
            content=(
                "Graph construction adds 340ms latency per query. Requires "
                "entity linking model not currently in the pipeline."
            ),
            section_label="Limitations",
            sequence=3,
        ),
    ]

    now = datetime.now(timezone.utc)

    arch_doc = SourceDocument(
        document_id="arxiv:2402.67890",
        corpus="arxiv",
        document_type="preprint",
        title="Knowledge Graph Construction from Retrieved Passages",
        canonical_url="https://arxiv.org/abs/2402.67890",
        language="en",
        publication_date=date(2024, 2, 20),
        authors=[Author(name="Carol Scientist")],
        venue="arXiv",
        source_metadata=ArxivMetadata(
            arxiv_id="2402.67890",
            primary_category="cs.CL",
        ),
        quality=QualitySignals(
            citation_count=15,
            peer_reviewed=False,
            venue_tier="preprint",
            overall_quality_score=0.65,
        ),
        classifications=Classifications(
            tasks=["retrieval", "generation"],
            techniques=["graph_neural_network"],
            modalities=["text"],
            keywords=["knowledge graph", "entity linking", "graph construction"],
        ),
        references=References(),
        content_blocks=blocks,
        first_ingested=now,
        last_checked=now,
        last_content_hash=compute_content_hash(blocks),
    )

    return [sample_source_document_arxiv, sample_source_document_patent, arch_doc]


# -- Phase 7: Video Integration fixtures ──────────────────────────────────


@pytest.fixture
def sample_video_pipeline_output():
    """Synthetic VideoPipelineOutput with 4 slides covering all section types."""
    from research_engineer.integration.video_adapter import (
        SlideData,
        VideoPipelineOutput,
    )

    return VideoPipelineOutput(
        title="Learned Sparse Representations for Multi-Hop Retrieval",
        video_path="/tmp/test_talk.mp4",
        slide_transcripts=[
            SlideData(
                slide_number=1,
                description="Abstract and Overview",
                start_s=0.0,
                end_s=120.0,
                text=(
                    "We propose replacing BM25 sparse retrieval with learned sparse "
                    "representations using SPLADE. Our approach produces sparse term-weight "
                    "vectors compatible with inverted index lookup, achieving +36.7% MRR@10 "
                    "on multi-hop queries compared to BM25 baseline."
                ),
                word_count=30,
            ),
            SlideData(
                slide_number=2,
                description="Method: Sparse Term Weight Generation",
                start_s=120.0,
                end_s=300.0,
                text=(
                    "The technique uses a pre-trained language model to generate sparse "
                    "term weights. Each query is decomposed into sub-queries, with "
                    "per-sub-query retrieval and aggregation via reciprocal rank fusion."
                ),
                word_count=28,
            ),
            SlideData(
                slide_number=3,
                description="Evaluation Results",
                start_s=300.0,
                end_s=420.0,
                text=(
                    "On the multi-hop subset of Natural Questions, our method achieves "
                    "MRR@10 of 0.847 compared to BM25 baseline of 0.620."
                ),
                word_count=20,
            ),
            SlideData(
                slide_number=4,
                description="Limitations and Future Work",
                start_s=420.0,
                end_s=480.0,
                text=(
                    "Evaluated only on English Wikipedia passages. Requires a trained "
                    "sparse encoder model with approximately 110M parameters."
                ),
                word_count=16,
            ),
        ],
    )


@pytest.fixture
def sample_video_pipeline_output_with_architecture():
    """Synthetic VideoPipelineOutput with an architecture diagram slide."""
    from research_engineer.integration.video_adapter import (
        SlideData,
        VideoPipelineOutput,
    )

    return VideoPipelineOutput(
        title="Knowledge Graph Construction from Retrieved Passages",
        video_path="/tmp/test_arch_talk.mp4",
        slide_transcripts=[
            SlideData(
                slide_number=1,
                description="Abstract",
                start_s=0.0,
                end_s=60.0,
                text=(
                    "We propose a novel pipeline stage that constructs a knowledge graph "
                    "from retrieved passages before answer generation. This introduces a new "
                    "intermediate representation between retrieval and generation stages."
                ),
                word_count=28,
            ),
            SlideData(
                slide_number=2,
                description="System Architecture Diagram",
                start_s=60.0,
                end_s=180.0,
                text=(
                    "A graph construction module extracts entities and relations from "
                    "retrieved passages, builds a knowledge graph, and feeds graph-structured "
                    "context to the generator. This requires a new evaluation methodology."
                ),
                word_count=26,
            ),
            SlideData(
                slide_number=3,
                description="Evaluation Results",
                start_s=180.0,
                end_s=300.0,
                text=(
                    "The knowledge graph intermediate representation improves factual "
                    "accuracy by 18.4% on complex multi-hop questions."
                ),
                word_count=14,
            ),
            SlideData(
                slide_number=4,
                description="Limitations",
                start_s=300.0,
                end_s=360.0,
                text=(
                    "Graph construction adds 340ms latency per query. Requires "
                    "entity linking model not currently in the pipeline."
                ),
                word_count=14,
            ),
        ],
    )


@pytest.fixture
def sample_video_pipeline_output_empty():
    """VideoPipelineOutput with no slides or transcripts for edge-case testing."""
    from research_engineer.integration.video_adapter import VideoPipelineOutput

    return VideoPipelineOutput(
        title="Empty Video Pipeline Output",
        video_path="/tmp/test_empty.mp4",
    )


@pytest.fixture
def sample_video_pipeline_output_segments_only():
    """VideoPipelineOutput with segment transcripts but no slide sync."""
    from research_engineer.integration.video_adapter import (
        SegmentTranscriptData,
        VideoPipelineOutput,
    )

    return VideoPipelineOutput(
        title="Segment-Only Video",
        video_path="/tmp/test_segments.mp4",
        segment_transcripts=[
            SegmentTranscriptData(
                text=(
                    "We propose replacing BM25 sparse retrieval with learned sparse "
                    "representations. The technique achieves improved MRR@10."
                ),
                language="en",
                duration_s=60.0,
                word_count=16,
                segment_index=0,
            ),
            SegmentTranscriptData(
                text=(
                    "The method uses a pre-trained language model to generate "
                    "sparse term weights for each query."
                ),
                language="en",
                duration_s=60.0,
                word_count=14,
                segment_index=1,
            ),
        ],
    )
