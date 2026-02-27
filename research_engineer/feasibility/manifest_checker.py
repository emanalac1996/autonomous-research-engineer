"""Manifest checker: load repository manifests and check paper operations.

Loads clearinghouse YAML manifests into structured models, then checks
whether a paper's required operations map to existing manifest entries
(function names, class names, docstrings, module paths).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManifestFunction(BaseModel):
    """A single function entry from a manifest YAML."""

    model_config = ConfigDict()

    name: str
    module_path: str = ""
    parameters: list[dict] = Field(default_factory=list)
    return_type: str | None = None
    return_description: str | None = None
    docstring: str | None = None
    decorators: list[str] = Field(default_factory=list)
    source_file: str = ""
    line_number: int | None = None


class ManifestClass(BaseModel):
    """A single class entry from a manifest YAML."""

    model_config = ConfigDict()

    name: str
    module_path: str = ""
    bases: list[str] = Field(default_factory=list)
    methods: list[ManifestFunction] = Field(default_factory=list)
    class_attributes: list[dict] = Field(default_factory=list)
    docstring: str | None = None
    source_file: str = ""
    line_number: int | None = None


class RepositoryManifest(BaseModel):
    """Full parsed manifest for a single repository."""

    model_config = ConfigDict()

    repo_name: str
    version: str = ""
    functions: list[ManifestFunction] = Field(default_factory=list)
    classes: list[ManifestClass] = Field(default_factory=list)
    module_tree: dict[str, list[str]] = Field(default_factory=dict)


class OperationMatch(BaseModel):
    """A single matched operation from manifest checking."""

    model_config = ConfigDict()

    operation: str
    repo_name: str
    function_name: str | None = None
    class_name: str | None = None
    module_path: str = ""
    match_type: str = ""  # exact_function, exact_class, docstring, module_path


class ManifestCheckResult(BaseModel):
    """Result of checking paper operations against repository manifests."""

    model_config = ConfigDict()

    matched_operations: list[OperationMatch] = Field(default_factory=list)
    unmatched_operations: list[str] = Field(default_factory=list)
    manifests_loaded: list[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0

    @field_validator("coverage_ratio")
    @classmethod
    def clamp_coverage(cls, v: float) -> float:
        return max(0.0, min(v, 1.0))


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest(yaml_path: Path) -> RepositoryManifest:
    """Parse a single manifest YAML file into a RepositoryManifest.

    Args:
        yaml_path: Path to a manifest YAML file.

    Returns:
        Parsed RepositoryManifest.
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return RepositoryManifest(repo_name=yaml_path.stem)

    # Parse functions
    functions = []
    for func_data in data.get("functions", []) or []:
        if isinstance(func_data, dict):
            functions.append(ManifestFunction(**func_data))

    # Parse classes
    classes = []
    for cls_data in data.get("classes", []) or []:
        if isinstance(cls_data, dict):
            # Parse nested methods
            methods_raw = cls_data.get("methods", []) or []
            methods = []
            for m in methods_raw:
                if isinstance(m, dict):
                    methods.append(ManifestFunction(**m))
            cls_data_copy = {**cls_data, "methods": methods}
            classes.append(ManifestClass(**cls_data_copy))

    return RepositoryManifest(
        repo_name=data.get("repo_name", yaml_path.stem),
        version=data.get("version", ""),
        functions=functions,
        classes=classes,
        module_tree=data.get("module_tree", {}),
    )


def load_all_manifests(manifests_dir: Path) -> list[RepositoryManifest]:
    """Load all manifest YAML files from a directory.

    Args:
        manifests_dir: Path to directory containing manifest YAML files.

    Returns:
        List of RepositoryManifest objects sorted by repo_name.
    """
    if not manifests_dir.is_dir():
        return []

    manifests = []
    for yaml_path in sorted(manifests_dir.glob("*.yaml")):
        manifests.append(load_manifest(yaml_path))

    return sorted(manifests, key=lambda m: m.repo_name)


# ---------------------------------------------------------------------------
# Operation checking
# ---------------------------------------------------------------------------


def _match_operation_in_manifest(
    operation: str, manifest: RepositoryManifest
) -> OperationMatch | None:
    """Try to match a single operation against a manifest. First match wins."""
    op_lower = operation.lower()

    # 1. Exact function name match
    for func in manifest.functions:
        if op_lower in func.name.lower():
            return OperationMatch(
                operation=operation,
                repo_name=manifest.repo_name,
                function_name=func.name,
                module_path=func.module_path,
                match_type="exact_function",
            )

    # 2. Exact class name match
    for cls in manifest.classes:
        if op_lower in cls.name.lower():
            return OperationMatch(
                operation=operation,
                repo_name=manifest.repo_name,
                class_name=cls.name,
                module_path=cls.module_path,
                match_type="exact_class",
            )

    # 3. Docstring substring match
    for func in manifest.functions:
        if func.docstring and op_lower in func.docstring.lower():
            return OperationMatch(
                operation=operation,
                repo_name=manifest.repo_name,
                function_name=func.name,
                module_path=func.module_path,
                match_type="docstring",
            )
    for cls in manifest.classes:
        if cls.docstring and op_lower in cls.docstring.lower():
            return OperationMatch(
                operation=operation,
                repo_name=manifest.repo_name,
                class_name=cls.name,
                module_path=cls.module_path,
                match_type="docstring",
            )

    # 4. Module path substring match
    for func in manifest.functions:
        if op_lower in func.module_path.lower():
            return OperationMatch(
                operation=operation,
                repo_name=manifest.repo_name,
                function_name=func.name,
                module_path=func.module_path,
                match_type="module_path",
            )

    return None


def check_operations(
    operations: list[str],
    manifests: list[RepositoryManifest],
) -> ManifestCheckResult:
    """Check paper operations against loaded manifests.

    Args:
        operations: List of operation strings to check.
        manifests: List of loaded RepositoryManifest objects.

    Returns:
        ManifestCheckResult with matched/unmatched operations and coverage.
    """
    matched: list[OperationMatch] = []
    unmatched: list[str] = []
    manifests_loaded = [m.repo_name for m in manifests]

    for op in operations:
        found = False
        for manifest in manifests:
            match = _match_operation_in_manifest(op, manifest)
            if match:
                matched.append(match)
                found = True
                break
        if not found:
            unmatched.append(op)

    total = len(matched) + len(unmatched)
    coverage = len(matched) / max(total, 1)

    return ManifestCheckResult(
        matched_operations=matched,
        unmatched_operations=unmatched,
        manifests_loaded=manifests_loaded,
        coverage_ratio=coverage,
    )
