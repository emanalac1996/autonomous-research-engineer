"""Tests for manifest freshness check (WU 6.3)."""

from datetime import datetime, timedelta, timezone

import yaml

from research_engineer.integration.manifest_freshness import (
    FreshnessReport,
    ManifestFreshnessResult,
    check_all_manifests_freshness,
    check_manifest_freshness,
)


def _write_manifest(path, generated_at=None, repo_name="test-repo"):
    """Helper to write a minimal manifest YAML for testing."""
    data = {"repo_name": repo_name, "version": "0.1.0"}
    if generated_at is not None:
        data["generated_at"] = generated_at
    path.write_text(yaml.dump(data))


class TestCheckManifestFreshness:
    """Tests for check_manifest_freshness()."""

    def test_fresh_manifest_not_stale(self, tmp_path):
        """Manifest generated 1 day ago is not stale."""
        now = datetime.now(timezone.utc)
        one_day_ago = (now - timedelta(days=1)).isoformat()

        manifest = tmp_path / "fresh.yaml"
        _write_manifest(manifest, generated_at=one_day_ago, repo_name="fresh-repo")

        result = check_manifest_freshness(manifest, reference_time=now)

        assert isinstance(result, ManifestFreshnessResult)
        assert result.repo_name == "fresh-repo"
        assert result.is_stale is False
        assert result.warning is None
        assert result.age_days < 2.0

    def test_stale_manifest_detected(self, tmp_path):
        """Manifest generated 10 days ago is stale."""
        now = datetime.now(timezone.utc)
        ten_days_ago = (now - timedelta(days=10)).isoformat()

        manifest = tmp_path / "stale.yaml"
        _write_manifest(manifest, generated_at=ten_days_ago, repo_name="stale-repo")

        result = check_manifest_freshness(manifest, reference_time=now)

        assert result.is_stale is True
        assert result.warning is not None
        assert "stale-repo" in result.warning
        assert result.age_days > 9.0

    def test_missing_generated_at(self, tmp_path):
        """Manifest without generated_at gets a warning."""
        manifest = tmp_path / "no_timestamp.yaml"
        _write_manifest(manifest, generated_at=None, repo_name="missing-ts-repo")

        result = check_manifest_freshness(manifest)

        assert result.generated_at is None
        assert result.warning is not None
        assert "no generated_at" in result.warning


class TestCheckAllManifestsFreshness:
    """Tests for check_all_manifests_freshness()."""

    def test_all_fresh(self, tmp_path):
        """Directory with 2 fresh manifests returns all_fresh=True."""
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).isoformat()

        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        _write_manifest(manifests_dir / "a.yaml", generated_at=recent, repo_name="a")
        _write_manifest(manifests_dir / "b.yaml", generated_at=recent, repo_name="b")

        report = check_all_manifests_freshness(manifests_dir, reference_time=now)

        assert isinstance(report, FreshnessReport)
        assert report.manifests_checked == 2
        assert report.stale_count == 0
        assert report.fresh_count == 2
        assert report.all_fresh is True

    def test_mixed_freshness(self, tmp_path):
        """1 fresh + 1 stale manifest gives correct counts."""
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).isoformat()
        old = (now - timedelta(days=14)).isoformat()

        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        _write_manifest(manifests_dir / "fresh.yaml", generated_at=recent, repo_name="fresh")
        _write_manifest(manifests_dir / "stale.yaml", generated_at=old, repo_name="stale")

        report = check_all_manifests_freshness(manifests_dir, reference_time=now)

        assert report.manifests_checked == 2
        assert report.stale_count == 1
        assert report.fresh_count == 1
        assert report.all_fresh is False
