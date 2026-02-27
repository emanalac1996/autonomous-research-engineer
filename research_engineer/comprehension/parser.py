"""Paper parser: extract structured ComprehensionSummary from plaintext.

Heuristic-based extraction — no LLM calls. Handles section splitting,
mathematical notation detection, claim extraction, and term identification.
PDF parsing deferred to Phase 6 (prior-art-retrieval integration).
"""

from __future__ import annotations

import re

from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    MathCore,
    PaperClaim,
    PaperSection,
    SectionType,
)

# ---------------------------------------------------------------------------
# Section heading patterns (case-insensitive)
# ---------------------------------------------------------------------------

_HEADING_MAP: list[tuple[SectionType, re.Pattern[str]]] = [
    (
        SectionType.abstract,
        re.compile(
            r"^(?:Abstract)\s*[:.]?\s*", re.IGNORECASE | re.MULTILINE
        ),
    ),
    (
        SectionType.method,
        re.compile(
            r"^(?:Method|Methods|Methodology|Approach)\s*[:.]?\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionType.results,
        re.compile(
            r"^(?:Results|Experiments|Evaluation)\s*[:.]?\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        SectionType.limitations,
        re.compile(
            r"^(?:Limitations|Discussion)\s*[:.]?\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
]

# ---------------------------------------------------------------------------
# Known metric names (lowercased for matching)
# ---------------------------------------------------------------------------

_METRIC_NAMES: list[str] = [
    "MRR@10",
    "MRR@100",
    "MRR",
    "F1",
    "accuracy",
    "factual_accuracy",
    "factual accuracy",
    "precision",
    "recall",
    "NDCG",
    "NDCG@10",
    "BLEU",
    "ROUGE",
    "latency",
    "throughput",
]

# ---------------------------------------------------------------------------
# Known technical terms for extraction
# ---------------------------------------------------------------------------

_KNOWN_TERMS: set[str] = {
    "reciprocal rank fusion",
    "sparse retrieval",
    "dense retrieval",
    "hybrid retrieval",
    "learned sparse",
    "learned sparse representations",
    "inverted index",
    "knowledge graph",
    "entity linking",
    "relation extraction",
    "query decomposition",
    "multi-hop",
    "beam search",
    "cross-encoder",
    "reranking",
    "embedding model",
    "answer generation",
    "context window",
    "query routing",
    "graph construction",
    "intermediate representation",
    "pipeline stage",
    "evaluation methodology",
    "graph quality",
}

_KNOWN_ACRONYMS: set[str] = {
    "BM25",
    "SPLADE",
    "FAISS",
    "RRF",
    "BERT",
    "NDCG",
    "TF-IDF",
}


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


def extract_sections(text: str) -> list[PaperSection]:
    """Split plaintext into typed sections based on heading patterns."""
    # Find all heading matches with their positions
    headings: list[tuple[int, int, SectionType, str]] = []
    for section_type, pattern in _HEADING_MAP:
        for m in pattern.finditer(text):
            headings.append((m.start(), m.end(), section_type, m.group(0).strip()))

    # Sort by position in text
    headings.sort(key=lambda h: h[0])

    sections: list[PaperSection] = []

    # Handle Title: prefix on first line
    title_match = re.match(r"^Title\s*[:.]?\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        title_content = title_match.group(1).strip()
        if title_content:
            sections.append(
                PaperSection(
                    section_type=SectionType.title,
                    heading="Title",
                    content=title_content,
                )
            )

    # Extract content between headings
    for i, (start, end, section_type, heading_text) in enumerate(headings):
        if i + 1 < len(headings):
            next_start = headings[i + 1][0]
            content = text[end:next_start].strip()
        else:
            content = text[end:].strip()

        if content:
            sections.append(
                PaperSection(
                    section_type=section_type,
                    heading=heading_text.rstrip(":. "),
                    content=content,
                )
            )

    return sections


def extract_title(text: str) -> str:
    """Extract the paper title from the first line or Title: heading."""
    title_match = re.match(r"^Title\s*[:.]?\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    # Fall back to first non-blank line
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------


def extract_claims(sections: list[PaperSection]) -> list[PaperClaim]:
    """Extract quantitative claims from results and abstract sections."""
    claims: list[PaperClaim] = []
    target_types = {SectionType.results, SectionType.abstract}
    target_text = " ".join(
        s.content for s in sections if s.section_type in target_types
    )
    if not target_text:
        return claims

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", target_text)

    for sentence in sentences:
        metric_name = _find_metric_name(sentence)
        metric_value = _extract_metric_value(sentence)
        baseline = _extract_baseline(sentence)

        if metric_value is not None or metric_name is not None:
            claims.append(
                PaperClaim(
                    claim_text=sentence.strip(),
                    metric_name=metric_name,
                    metric_value=metric_value,
                    baseline_comparison=baseline,
                    dataset=_extract_dataset(sentence),
                )
            )

    return claims


def _find_metric_name(text: str) -> str | None:
    """Find a known metric name in text."""
    for metric in _METRIC_NAMES:
        if metric.lower() in text.lower():
            return metric
    return None


def _extract_metric_value(text: str) -> float | None:
    """Extract the primary metric value from a claim sentence."""
    # Pattern: "achieves/yields X of VALUE" or "MRR@10 of VALUE"
    m = re.search(
        r"(?:achieves?|yields?|produces?)\s+[\w@]+\s+(?:of\s+)?([\d.]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        return _safe_float(m.group(1))

    # Pattern: "of VALUE" right after metric name
    m = re.search(r"(?:MRR|F1|accuracy|NDCG)[@\w]*\s+(?:of\s+)([\d.]+)", text, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))

    # Pattern: "improves ... by VALUE%"
    m = re.search(r"improves?\s+.*?by\s+([\d.]+)\s*%", text, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))

    # Pattern: "+VALUE%" at start of metric claim
    m = re.search(r"\+([\d.]+)\s*%", text)
    if m:
        return _safe_float(m.group(1))

    # Pattern: "VALUE% improvement/increase"
    m = re.search(r"([\d.]+)\s*%\s*(?:improvement|increase|on)", text, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))

    return None


def _extract_baseline(text: str) -> float | None:
    """Extract baseline comparison value from a claim sentence."""
    m = re.search(
        r"(?:baseline|compared\s+to|default|over\s+default)\s+.*?([\d.]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        return _safe_float(m.group(1))
    return None


def _extract_dataset(text: str) -> str | None:
    """Extract dataset name from a claim sentence."""
    # Common dataset patterns
    m = re.search(
        r"(?:on|across|from)\s+(?:the\s+)?(?:(\d+)\s+)?"
        r"([\w\s-]+?)(?:\s+(?:dataset|benchmark|corpus|subset|questions))",
        text,
        re.IGNORECASE,
    )
    if m:
        count = m.group(1)
        name = m.group(2).strip()
        if count:
            return f"{name} ({count} datasets)" if "dataset" in text.lower() else name
        return name
    return None


def _safe_float(s: str) -> float | None:
    """Convert string to float, return None on failure."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Math core extraction
# ---------------------------------------------------------------------------


def extract_math_core(sections: list[PaperSection]) -> MathCore:
    """Extract mathematical formulation from method section."""
    method_text = " ".join(
        s.content for s in sections if s.section_type == SectionType.method
    )
    if not method_text:
        return MathCore()

    formulation = _extract_formulation(method_text)
    complexity = _extract_complexity(method_text)
    assumptions = _extract_assumptions(method_text)

    return MathCore(
        formulation=formulation,
        complexity=complexity,
        assumptions=assumptions,
    )


def _extract_formulation(text: str) -> str | None:
    """Extract mathematical formulation from text."""
    # LaTeX inline math
    m = re.search(r"\$([^$]+)\$", text)
    if m:
        return m.group(0)

    # "Given:" or "where:" formulation blocks
    m = re.search(
        r"(?:Given|where|subject to)\s*:\s*(.+?)(?:\.|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(0).strip()

    # Sentences describing the technique/formula
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if re.search(r"(?:formula|equation|function|compute|calculates?)", sentence, re.IGNORECASE):
            return sentence.strip()

    # Fall back: first sentence of method as a high-level formulation
    if sentences:
        return sentences[0].strip()

    return None


def _extract_complexity(text: str) -> str | None:
    """Extract computational complexity from text."""
    m = re.search(r"O\([^)]+\)", text)
    if m:
        return m.group(0)
    return None


def _extract_assumptions(text: str) -> list[str]:
    """Extract assumptions from text."""
    assumptions: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if re.search(r"(?:assum|requir|depend|need)", sentence, re.IGNORECASE):
            assumptions.append(sentence.strip())
    return assumptions


# ---------------------------------------------------------------------------
# Limitations extraction
# ---------------------------------------------------------------------------


def extract_limitations(sections: list[PaperSection]) -> list[str]:
    """Extract limitation statements from the limitations section."""
    lim_text = " ".join(
        s.content for s in sections if s.section_type == SectionType.limitations
    )
    if not lim_text:
        return []

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", lim_text)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Term extraction
# ---------------------------------------------------------------------------


def extract_paper_terms(sections: list[PaperSection]) -> list[str]:
    """Extract technical terms from abstract and method sections."""
    target_types = {SectionType.abstract, SectionType.method, SectionType.title}
    target_text = " ".join(
        s.content for s in sections if s.section_type in target_types
    )
    if not target_text:
        return []

    text_lower = target_text.lower()
    found: list[str] = []

    # Match known multi-word and single-word terms
    for term in _KNOWN_TERMS:
        if term.lower() in text_lower:
            found.append(term)

    # Match known acronyms (case-sensitive)
    for acronym in _KNOWN_ACRONYMS:
        if acronym in target_text:
            found.append(acronym)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for term in found:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            result.append(term)

    return result


# ---------------------------------------------------------------------------
# Transformation extraction
# ---------------------------------------------------------------------------


def extract_transformation(sections: list[PaperSection]) -> str:
    """Extract the core transformation proposed from abstract/method."""
    abstract_text = " ".join(
        s.content for s in sections if s.section_type == SectionType.abstract
    )
    if not abstract_text:
        # Fall back to method section
        abstract_text = " ".join(
            s.content for s in sections if s.section_type == SectionType.method
        )
    if not abstract_text:
        # Fall back to any section
        abstract_text = " ".join(s.content for s in sections)

    sentences = re.split(r"(?<=[.!?])\s+", abstract_text)

    # Look for sentences with proposal/transformation verbs
    proposal_pattern = re.compile(
        r"(?:propos|introduc|replac|swap|adjust|optimiz|investigat)",
        re.IGNORECASE,
    )
    for sentence in sentences:
        if proposal_pattern.search(sentence):
            return sentence.strip()

    # Fall back to first sentence
    if sentences:
        return sentences[0].strip()

    return abstract_text.strip()


# ---------------------------------------------------------------------------
# Input/output extraction
# ---------------------------------------------------------------------------


def extract_inputs_outputs(
    sections: list[PaperSection],
) -> tuple[list[str], list[str]]:
    """Extract required inputs and produced outputs from method section."""
    method_text = " ".join(
        s.content for s in sections if s.section_type == SectionType.method
    )
    if not method_text:
        return [], []

    inputs: list[str] = []
    outputs: list[str] = []

    sentences = re.split(r"(?<=[.!?])\s+", method_text)
    for sentence in sentences:
        lower = sentence.lower()
        if re.search(r"(?:requires?|uses?|takes?|needs?|given)\b", lower):
            inputs.append(sentence.strip())
        if re.search(r"(?:produces?|outputs?|generates?|yields?|returns?)\b", lower):
            outputs.append(sentence.strip())

    return inputs, outputs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def parse_paper(text: str) -> ComprehensionSummary:
    """Parse plaintext paper into a ComprehensionSummary.

    This is the primary entry point for Stage 1 comprehension.

    Args:
        text: Full plaintext of the paper (Title + Abstract + Method +
              Results + Limitations).

    Returns:
        ComprehensionSummary with all extracted fields populated.
    """
    sections = extract_sections(text)
    title = extract_title(text)
    claims = extract_claims(sections)
    math_core = extract_math_core(sections)
    limitations = extract_limitations(sections)
    paper_terms = extract_paper_terms(sections)
    transformation = extract_transformation(sections)
    inputs_required, outputs_produced = extract_inputs_outputs(sections)

    return ComprehensionSummary(
        title=title,
        transformation_proposed=transformation,
        inputs_required=inputs_required,
        outputs_produced=outputs_produced,
        claims=claims,
        limitations=limitations,
        mathematical_core=math_core,
        sections=sections,
        paper_terms=paper_terms,
    )
