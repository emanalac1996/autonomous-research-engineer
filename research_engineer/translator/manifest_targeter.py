"""Manifest targeter: identify file targets from clearinghouse manifests.

Scans manifest YAML files (API surface maps) to find files relevant to a paper's
proposed transformation, and generates file creation targets based on innovation type.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from research_engineer.classifier.types import InnovationType
from research_engineer.comprehension.schema import ComprehensionSummary


class FileTarget(BaseModel):
    """Single file target identified from manifest analysis."""

    source_file: str
    repo_name: str
    reason: str


class FileTargeting(BaseModel):
    """Complete file targeting result from manifest analysis."""

    files_created: list[FileTarget] = Field(default_factory=list)
    files_modified: list[FileTarget] = Field(default_factory=list)
    target_repos: list[str] = Field(default_factory=list)


def _load_manifests(manifests_dir: Path) -> list[dict]:
    """Load all YAML manifests from a directory."""
    manifests: list[dict] = []
    if not manifests_dir.exists() or not manifests_dir.is_dir():
        return manifests
    for yaml_path in sorted(manifests_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                manifests.append(data)
        except Exception:
            continue
    return manifests


def _match_terms(
    search_terms: list[str],
    name: str,
    docstring: str | None,
    module_path: str | None,
) -> str | None:
    """Check if any search term matches name, docstring, or module_path (case-insensitive).

    Returns the matching term, or None.
    """
    searchable = " ".join(
        s.lower() for s in [name, docstring or "", module_path or ""] if s
    )
    for term in search_terms:
        if term.lower() in searchable:
            return term
    return None


def _scan_manifest_entries(
    manifest: dict,
    search_terms: list[str],
    repo_name: str,
) -> list[FileTarget]:
    """Scan functions and classes in a manifest for term matches."""
    targets: list[FileTarget] = []
    seen_files: set[str] = set()

    for entry in manifest.get("functions", []):
        source_file = entry.get("source_file", "")
        if not source_file or source_file in seen_files:
            continue
        match = _match_terms(
            search_terms,
            entry.get("name", ""),
            entry.get("docstring"),
            entry.get("module_path"),
        )
        if match:
            targets.append(
                FileTarget(
                    source_file=source_file,
                    repo_name=repo_name,
                    reason=f"function matches term '{match}'",
                )
            )
            seen_files.add(source_file)

    for entry in manifest.get("classes", []):
        source_file = entry.get("source_file", "")
        if not source_file or source_file in seen_files:
            continue
        match = _match_terms(
            search_terms,
            entry.get("name", ""),
            entry.get("docstring"),
            entry.get("module_path"),
        )
        if match:
            targets.append(
                FileTarget(
                    source_file=source_file,
                    repo_name=repo_name,
                    reason=f"class matches term '{match}'",
                )
            )
            seen_files.add(source_file)

    return targets


def _generate_created_files(
    innovation_type: InnovationType,
    summary: ComprehensionSummary,
    target_repos: list[str],
) -> list[FileTarget]:
    """Generate files_created based on innovation type."""
    repo = target_repos[0] if target_repos else "target_repo"
    title_slug = summary.title.lower().replace(" ", "_")[:40] if summary.title else "new_module"

    if innovation_type == InnovationType.parameter_tuning:
        return []

    if innovation_type == InnovationType.modular_swap:
        return [
            FileTarget(
                source_file=f"src/{title_slug}_component.py",
                repo_name=repo,
                reason="new replacement component module",
            ),
        ]

    if innovation_type == InnovationType.pipeline_restructuring:
        return [
            FileTarget(
                source_file=f"src/{title_slug}_stage.py",
                repo_name=repo,
                reason="new pipeline stage module",
            ),
            FileTarget(
                source_file=f"tests/test_{title_slug}_stage.py",
                repo_name=repo,
                reason="test for new pipeline stage",
            ),
        ]

    # architectural_innovation
    return [
        FileTarget(
            source_file=f"src/{title_slug}_primitive.py",
            repo_name=repo,
            reason="new primitive module",
        ),
        FileTarget(
            source_file=f"src/{title_slug}_integration.py",
            repo_name=repo,
            reason="integration layer for new primitive",
        ),
        FileTarget(
            source_file=f"tests/test_{title_slug}_primitive.py",
            repo_name=repo,
            reason="test for new primitive",
        ),
    ]


def identify_targets(
    summary: ComprehensionSummary,
    classification_type: InnovationType,
    manifests_dir: Path | None = None,
) -> FileTargeting:
    """Identify file targets from manifests and innovation type.

    Args:
        summary: Paper comprehension output.
        classification_type: Classified innovation type.
        manifests_dir: Path to directory containing YAML manifests.

    Returns:
        FileTargeting with files_modified, files_created, and target_repos.
    """
    files_modified: list[FileTarget] = []
    repo_names: set[str] = set()

    # Build search terms from summary
    search_terms = list(summary.paper_terms)
    search_terms.extend(summary.inputs_required)
    search_terms.extend(summary.outputs_produced)

    # Scan manifests for matching files
    if manifests_dir is not None:
        manifests = _load_manifests(manifests_dir)
        for manifest in manifests:
            repo_name = manifest.get("repo_name", "unknown")
            targets = _scan_manifest_entries(manifest, search_terms, repo_name)
            files_modified.extend(targets)
            if targets:
                repo_names.add(repo_name)

    target_repos = sorted(repo_names)

    # Generate files_created based on innovation type
    files_created = _generate_created_files(
        classification_type, summary, target_repos
    )

    return FileTargeting(
        files_created=files_created,
        files_modified=files_modified,
        target_repos=target_repos,
    )
