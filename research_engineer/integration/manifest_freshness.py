"""Manifest freshness check: detect stale manifests before feasibility assessment.

Loads the generated_at timestamp from manifest YAML files and warns if
older than a configurable threshold (default 7 days).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, computed_field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_STALENESS_THRESHOLD_DAYS: float = 7.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ManifestFreshnessResult(BaseModel):
    """Result of checking manifest freshness for a single manifest."""

    model_config = ConfigDict()

    repo_name: str
    manifest_path: str
    generated_at: datetime | None = None
    age_days: float = 0.0
    is_stale: bool = False
    warning: str | None = None


class FreshnessReport(BaseModel):
    """Aggregate freshness report for all manifests in a directory."""

    model_config = ConfigDict()

    manifests_checked: int = 0
    stale_count: int = 0
    fresh_count: int = 0
    missing_timestamp_count: int = 0
    threshold_days: float = DEFAULT_STALENESS_THRESHOLD_DAYS
    results: list[ManifestFreshnessResult] = Field(default_factory=list)

    @computed_field
    @property
    def all_fresh(self) -> bool:
        """True if no manifests are stale and none are missing timestamps."""
        return self.stale_count == 0 and self.missing_timestamp_count == 0


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def _parse_generated_at(raw: str) -> datetime | None:
    """Parse the generated_at field from manifest YAML.

    Handles ISO 8601 strings with and without timezone.
    Python 3.11+ fromisoformat handles 'Z' suffix.
    """
    if not raw:
        return None
    try:
        raw_str = str(raw).strip()
        # Handle 'Z' suffix for Python < 3.11 compatibility
        if raw_str.endswith("Z"):
            raw_str = raw_str[:-1] + "+00:00"
        return datetime.fromisoformat(raw_str)
    except (ValueError, TypeError):
        return None


def check_manifest_freshness(
    yaml_path: Path,
    threshold_days: float = DEFAULT_STALENESS_THRESHOLD_DAYS,
    reference_time: datetime | None = None,
) -> ManifestFreshnessResult:
    """Check a single manifest YAML file for staleness.

    Args:
        yaml_path: Path to the manifest YAML file.
        threshold_days: Maximum age in days before considered stale.
        reference_time: Time to compare against (default: now UTC).

    Returns:
        ManifestFreshnessResult with staleness assessment.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    # Load YAML
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    repo_name = data.get("repo_name", yaml_path.stem)
    generated_at_raw = data.get("generated_at")

    if generated_at_raw is None:
        return ManifestFreshnessResult(
            repo_name=repo_name,
            manifest_path=str(yaml_path),
            warning=f"Manifest {repo_name} has no generated_at timestamp",
        )

    generated_at = _parse_generated_at(str(generated_at_raw))

    if generated_at is None:
        return ManifestFreshnessResult(
            repo_name=repo_name,
            manifest_path=str(yaml_path),
            warning=f"Could not parse generated_at: {generated_at_raw}",
        )

    # Ensure timezone-aware comparison
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    age = reference_time - generated_at
    age_days = age.total_seconds() / 86400.0
    is_stale = age_days > threshold_days

    warning = None
    if is_stale:
        warning = (
            f"Manifest {repo_name} is {age_days:.1f} days old "
            f"(threshold: {threshold_days} days)"
        )

    return ManifestFreshnessResult(
        repo_name=repo_name,
        manifest_path=str(yaml_path),
        generated_at=generated_at,
        age_days=age_days,
        is_stale=is_stale,
        warning=warning,
    )


def check_all_manifests_freshness(
    manifests_dir: Path,
    threshold_days: float = DEFAULT_STALENESS_THRESHOLD_DAYS,
    reference_time: datetime | None = None,
) -> FreshnessReport:
    """Check all manifest YAML files in a directory for staleness.

    Args:
        manifests_dir: Directory containing manifest YAML files.
        threshold_days: Maximum age in days before considered stale.
        reference_time: Time to compare against (default: now UTC).

    Returns:
        FreshnessReport with per-manifest results and aggregate counts.
    """
    results: list[ManifestFreshnessResult] = []
    stale_count = 0
    fresh_count = 0
    missing_timestamp_count = 0

    yaml_files = sorted(manifests_dir.glob("*.yaml"))

    for yaml_path in yaml_files:
        result = check_manifest_freshness(yaml_path, threshold_days, reference_time)
        results.append(result)

        if result.generated_at is None:
            missing_timestamp_count += 1
        elif result.is_stale:
            stale_count += 1
        else:
            fresh_count += 1

    return FreshnessReport(
        manifests_checked=len(results),
        stale_count=stale_count,
        fresh_count=fresh_count,
        missing_timestamp_count=missing_timestamp_count,
        threshold_days=threshold_days,
        results=results,
    )
