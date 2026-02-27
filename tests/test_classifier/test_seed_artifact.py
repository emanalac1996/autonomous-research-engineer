"""Tests for seed heuristic artifact (WU 2.3)."""

import yaml
import pytest

from agent_factors.artifacts import ArtifactRegistry, ArtifactType

from research_engineer.classifier.seed_artifact import (
    CLASSIFIER_DOMAIN,
    SEED_ARTIFACT_NAME,
    get_seed_heuristic_content,
    register_seed_artifact,
    validate_heuristic_yaml,
)
from research_engineer.classifier.types import InnovationType


class TestGetSeedHeuristicContent:
    """Tests for the seed YAML content."""

    def test_returns_parseable_yaml(self):
        """get_seed_heuristic_content returns valid YAML."""
        content = get_seed_heuristic_content()
        data = yaml.safe_load(content)
        assert isinstance(data, dict)

    def test_has_rules_key(self):
        """Seed YAML has a 'rules' key."""
        data = yaml.safe_load(get_seed_heuristic_content())
        assert "rules" in data

    def test_has_five_rules(self):
        """Seed YAML contains exactly 5 rules."""
        data = yaml.safe_load(get_seed_heuristic_content())
        assert len(data["rules"]) == 5


class TestValidateHeuristicYaml:
    """Tests for YAML validation."""

    def test_valid_content_passes(self):
        """Seed content passes validation."""
        result = validate_heuristic_yaml(get_seed_heuristic_content())
        assert "rules" in result

    def test_all_rules_have_required_keys(self):
        """All rules have rule_id, classification, priority, signals."""
        data = validate_heuristic_yaml(get_seed_heuristic_content())
        required = {"rule_id", "classification", "priority", "signals"}
        for rule in data["rules"]:
            assert required.issubset(set(rule.keys())), f"Rule {rule.get('rule_id')} missing keys"

    def test_all_classifications_valid(self):
        """All rule classifications are valid InnovationType values."""
        data = validate_heuristic_yaml(get_seed_heuristic_content())
        valid_types = {t.value for t in InnovationType}
        for rule in data["rules"]:
            assert rule["classification"] in valid_types

    def test_rejects_missing_rules_key(self):
        """Rejects YAML without 'rules' key."""
        with pytest.raises(ValueError, match="rules"):
            validate_heuristic_yaml("other_key: []")

    def test_rejects_invalid_classification(self):
        """Rejects rules with invalid classification."""
        bad_yaml = "rules:\n  - rule_id: bad\n    classification: invalid_type\n    priority: 1\n    signals: {}"
        with pytest.raises(ValueError, match="invalid classification"):
            validate_heuristic_yaml(bad_yaml)


class TestRegisterSeedArtifact:
    """Tests for seed artifact registration."""

    def test_registers_artifact(self, tmp_path):
        """register_seed_artifact creates an entry in the registry."""
        store_dir = tmp_path / "store"
        store_dir.mkdir()
        registry = ArtifactRegistry(store_dir=store_dir)
        artifact_id = register_seed_artifact(registry)
        assert artifact_id
        entry = registry.get(artifact_id)
        assert entry is not None
        assert entry.name == SEED_ARTIFACT_NAME
        assert entry.domain == CLASSIFIER_DOMAIN
        assert entry.artifact_type == ArtifactType.evaluation_rubric

    def test_idempotent(self, tmp_path):
        """Calling register_seed_artifact twice returns the same artifact_id."""
        store_dir = tmp_path / "store"
        store_dir.mkdir()
        registry = ArtifactRegistry(store_dir=store_dir)
        id1 = register_seed_artifact(registry)
        id2 = register_seed_artifact(registry)
        assert id1 == id2
