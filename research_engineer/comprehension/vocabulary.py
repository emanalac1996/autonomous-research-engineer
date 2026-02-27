"""Vocabulary mapping: map paper terms to metis-platform vocabulary.

Links paper terminology to clearinghouse Pattern Library pattern IDs
and repository manifest entries, enabling the classifier and feasibility
gate to connect paper concepts to existing codebase capabilities.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class PatternMatch(BaseModel):
    """A single pattern match from the Pattern Library."""

    model_config = ConfigDict()

    paper_term: str
    pattern_id: str
    score: float
    formal_class: str
    matched_phrases: list[str] = Field(default_factory=list)


class ManifestMatch(BaseModel):
    """A single manifest entry match."""

    model_config = ConfigDict()

    paper_term: str
    repo_name: str
    function_name: str | None = None
    class_name: str | None = None
    module_path: str = ""


class VocabularyMapping(BaseModel):
    """Complete vocabulary mapping result linking paper terms to platform concepts."""

    model_config = ConfigDict()

    paper_terms: list[str] = Field(default_factory=list)
    pattern_matches: list[PatternMatch] = Field(default_factory=list)
    manifest_matches: list[ManifestMatch] = Field(default_factory=list)
    unmapped_terms: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern Library matching (via clearinghouse match_problem API)
# ---------------------------------------------------------------------------


def match_terms_to_patterns(
    terms: list[str],
    clearinghouse_root: Path,
    top_n: int = 3,
    threshold: float = 0.05,
) -> list[PatternMatch]:
    """Match paper terms against the clearinghouse Pattern Library.

    Imports match_problem() from clearinghouse/scripts/match_problem.py
    and calls it with each term.

    Args:
        terms: List of paper terms extracted by the parser.
        clearinghouse_root: Path to the clearinghouse repo root.
        top_n: Maximum matches per term.
        threshold: Minimum score to include.

    Returns:
        List of PatternMatch objects.
    """
    # Scoped sys.path insertion to import match_problem
    ch_str = str(clearinghouse_root)
    added = ch_str not in sys.path
    if added:
        sys.path.insert(0, ch_str)
    try:
        from scripts.match_problem import match_problem  # type: ignore[import-untyped]
    finally:
        if added and ch_str in sys.path:
            sys.path.remove(ch_str)

    results: list[PatternMatch] = []
    for term in terms:
        matches = match_problem(
            query=term,
            top_n=top_n,
            threshold=threshold,
        )
        for m in matches:
            results.append(
                PatternMatch(
                    paper_term=term,
                    pattern_id=m.pattern_id,
                    score=m.score,
                    formal_class=m.formal_class,
                    matched_phrases=m.matched_phrases[:3],
                )
            )

    return results


# ---------------------------------------------------------------------------
# Manifest matching
# ---------------------------------------------------------------------------


def match_terms_to_manifests(
    terms: list[str],
    manifests_dir: Path,
) -> list[ManifestMatch]:
    """Match paper terms against repository manifest entries.

    Searches function names, class names, docstrings, and module paths
    in all manifest YAML files for term overlap.

    Args:
        terms: List of paper terms.
        manifests_dir: Path to clearinghouse/manifests/ directory.

    Returns:
        List of ManifestMatch objects.
    """
    results: list[ManifestMatch] = []

    if not manifests_dir.is_dir():
        return results

    for yaml_path in sorted(manifests_dir.glob("*.yaml")):
        with open(yaml_path) as f:
            manifest = yaml.safe_load(f)
        if not manifest:
            continue

        repo_name = manifest.get("repo_name", yaml_path.stem)

        for term in terms:
            term_lower = term.lower()

            # Search functions
            for func in manifest.get("functions", []):
                if _term_matches_entry(term_lower, func):
                    results.append(
                        ManifestMatch(
                            paper_term=term,
                            repo_name=repo_name,
                            function_name=func.get("name"),
                            module_path=func.get("module_path", ""),
                        )
                    )

            # Search classes
            for cls in manifest.get("classes", []):
                if _term_matches_class(term_lower, cls):
                    results.append(
                        ManifestMatch(
                            paper_term=term,
                            repo_name=repo_name,
                            class_name=cls.get("name"),
                            module_path=cls.get("module_path", ""),
                        )
                    )

    return results


def _term_matches_entry(term_lower: str, func: dict) -> bool:
    """Check if a term matches a function manifest entry."""
    searchable = " ".join(
        filter(
            None,
            [
                func.get("name", ""),
                func.get("docstring", ""),
                func.get("module_path", ""),
            ],
        )
    ).lower()
    return term_lower in searchable


def _term_matches_class(term_lower: str, cls: dict) -> bool:
    """Check if a term matches a class manifest entry."""
    searchable = " ".join(
        filter(
            None,
            [
                cls.get("name", ""),
                cls.get("docstring", ""),
                cls.get("module_path", ""),
            ],
        )
    ).lower()
    return term_lower in searchable


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_vocabulary_mapping(
    paper_terms: list[str],
    clearinghouse_root: Path,
) -> VocabularyMapping:
    """Build a complete vocabulary mapping from paper terms.

    This is the primary entry point for vocabulary mapping.

    Args:
        paper_terms: Terms extracted by the parser
            (from ComprehensionSummary.paper_terms).
        clearinghouse_root: Path to the clearinghouse repo root.

    Returns:
        VocabularyMapping with pattern matches, manifest matches,
        and unmapped terms.
    """
    manifests_dir = clearinghouse_root / "manifests"

    pattern_matches = match_terms_to_patterns(paper_terms, clearinghouse_root)
    manifest_matches = match_terms_to_manifests(paper_terms, manifests_dir)

    # Determine which terms had no matches at all
    matched_terms: set[str] = set()
    for pm in pattern_matches:
        matched_terms.add(pm.paper_term)
    for mm in manifest_matches:
        matched_terms.add(mm.paper_term)
    unmapped = [t for t in paper_terms if t not in matched_terms]

    return VocabularyMapping(
        paper_terms=paper_terms,
        pattern_matches=pattern_matches,
        manifest_matches=manifest_matches,
        unmapped_terms=unmapped,
    )
