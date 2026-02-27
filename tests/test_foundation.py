"""Foundation tests for autonomous-research-engineer (Phase 0).

Tests cover: package imports, repo structure, subpackage layout,
agent-factors integration, clearinghouse connectivity, fixture validation.
"""

from pathlib import Path


# ── Import tests ─────────────────────────────────────────────────────────────

class TestImports:
    """Verify all package imports work."""

    def test_import_research_engineer(self):
        import research_engineer
        assert hasattr(research_engineer, "__version__")

    def test_version_string(self):
        import research_engineer
        assert research_engineer.__version__ == "0.1.0"

    def test_import_comprehension(self):
        import research_engineer.comprehension

    def test_import_classifier(self):
        import research_engineer.classifier

    def test_import_feasibility(self):
        import research_engineer.feasibility

    def test_import_translator(self):
        import research_engineer.translator

    def test_import_calibration(self):
        import research_engineer.calibration


# ── Repo structure tests ────────────────────────────────────────────────────

class TestRepoStructure:
    """Verify expected repo structure exists."""

    def test_claude_md_exists(self, repo_root: Path):
        assert (repo_root / "CLAUDE.md").is_file()

    def test_readme_exists(self, repo_root: Path):
        assert (repo_root / "README.md").is_file()

    def test_pyproject_exists(self, repo_root: Path):
        assert (repo_root / "pyproject.toml").is_file()

    def test_gitignore_exists(self, repo_root: Path):
        assert (repo_root / ".gitignore").is_file()

    def test_scripts_dir_exists(self, repo_root: Path):
        assert (repo_root / "scripts").is_dir()

    def test_tests_dir_exists(self, repo_root: Path):
        assert (repo_root / "tests").is_dir()

    def test_updates_dir_exists(self, repo_root: Path):
        assert (repo_root / "updates").is_dir()
        assert (repo_root / "updates" / "logs").is_dir()
        assert (repo_root / "updates" / "architecture").is_dir()
        assert (repo_root / "updates" / "strategy").is_dir()

    def test_plans_dir_exists(self, repo_root: Path):
        assert (repo_root / "plans").is_dir()


# ── Subpackage structure tests ──────────────────────────────────────────────

class TestSubpackages:
    """Verify all subpackage directories contain __init__.py."""

    def test_comprehension_init(self, package_root: Path):
        assert (package_root / "comprehension" / "__init__.py").is_file()

    def test_classifier_init(self, package_root: Path):
        assert (package_root / "classifier" / "__init__.py").is_file()

    def test_feasibility_init(self, package_root: Path):
        assert (package_root / "feasibility" / "__init__.py").is_file()

    def test_translator_init(self, package_root: Path):
        assert (package_root / "translator" / "__init__.py").is_file()

    def test_calibration_init(self, package_root: Path):
        assert (package_root / "calibration" / "__init__.py").is_file()

    def test_test_subdirs_exist(self, repo_root: Path):
        test_dirs = [
            "test_comprehension", "test_classifier", "test_feasibility",
            "test_translator", "test_calibration", "test_integration",
        ]
        for d in test_dirs:
            assert (repo_root / "tests" / d).is_dir(), f"Missing test dir: {d}"


# ── agent-factors integration tests ─────────────────────────────────────────

class TestAgentFactorsIntegration:
    """Verify agent-factors is importable and key subpackages work."""

    def test_import_g_layer(self):
        import agent_factors.g_layer

    def test_import_catalog(self):
        import agent_factors.catalog

    def test_import_artifacts(self):
        import agent_factors.artifacts

    def test_import_dag(self):
        import agent_factors.dag

    def test_import_approvals(self):
        import agent_factors.approvals

    def test_import_ecc(self):
        import agent_factors.ecc

    def test_agent_factors_root_exists(self, agent_factors_root: Path):
        assert agent_factors_root.is_dir(), (
            f"agent-factors repo not found at {agent_factors_root}"
        )

    def test_agent_factors_package_exists(self, agent_factors_root: Path):
        assert (agent_factors_root / "agent_factors" / "__init__.py").is_file()


# ── Clearinghouse connectivity tests ────────────────────────────────────────

class TestClearinghouseConnectivity:
    """Verify clearinghouse paths resolve correctly."""

    def test_clearinghouse_exists(self, clearinghouse_root: Path):
        assert clearinghouse_root.is_dir()

    def test_ledger_exists(self, clearinghouse_ledger: Path):
        assert clearinghouse_ledger.is_file()

    def test_newsletter_exists(self, clearinghouse_newsletter: Path):
        assert clearinghouse_newsletter.is_file()

    def test_state_exists(self, clearinghouse_state: Path):
        assert clearinghouse_state.is_file()

    def test_schemas_dir_exists(self, clearinghouse_schemas: Path):
        assert clearinghouse_schemas.is_dir()

    def test_manifests_dir_exists(self, clearinghouse_manifests: Path):
        assert clearinghouse_manifests.is_dir()

    def test_algorithms_dir_exists(self, clearinghouse_algorithms: Path):
        assert clearinghouse_algorithms.is_dir()


# ── Fixture validation tests ────────────────────────────────────────────────

class TestFixtures:
    """Verify test fixtures produce valid data."""

    def test_repo_root_is_absolute(self, repo_root: Path):
        assert repo_root.is_absolute()

    def test_package_root_under_repo(self, repo_root: Path, package_root: Path):
        assert package_root.parent == repo_root

    def test_tmp_comprehension_dir(self, tmp_comprehension_dir: Path):
        assert tmp_comprehension_dir.is_dir()
        assert tmp_comprehension_dir.name == "comprehension"

    def test_tmp_classifier_dir(self, tmp_classifier_dir: Path):
        assert tmp_classifier_dir.is_dir()
        assert tmp_classifier_dir.name == "classifier"

    def test_tmp_feasibility_dir(self, tmp_feasibility_dir: Path):
        assert tmp_feasibility_dir.is_dir()
        assert tmp_feasibility_dir.name == "feasibility"

    def test_tmp_translator_dir(self, tmp_translator_dir: Path):
        assert tmp_translator_dir.is_dir()
        assert tmp_translator_dir.name == "translator"

    def test_tmp_calibration_dir(self, tmp_calibration_dir: Path):
        assert tmp_calibration_dir.is_dir()
        assert tmp_calibration_dir.name == "calibration"

    def test_sample_paper_text_nonempty(self, sample_paper_text: str):
        assert len(sample_paper_text) > 100
        assert "Abstract" in sample_paper_text
        assert "Method" in sample_paper_text

    def test_sample_parameter_tuning_text(self, sample_parameter_tuning_text: str):
        assert len(sample_parameter_tuning_text) > 50
        assert "RRF" in sample_parameter_tuning_text or "parameter" in sample_parameter_tuning_text.lower()

    def test_sample_architectural_text(self, sample_architectural_text: str):
        assert len(sample_architectural_text) > 50
        assert "knowledge graph" in sample_architectural_text.lower()


# ── Clearinghouse integration script tests ──────────────────────────────────

class TestClearinghouseScript:
    """Verify the check_clearinghouse.py script functions."""

    def test_script_exists(self, repo_root: Path):
        assert (repo_root / "scripts" / "check_clearinghouse.py").is_file()

    def test_script_importable(self, repo_root: Path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_clearinghouse",
            repo_root / "scripts" / "check_clearinghouse.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "read_newsletter")
        assert hasattr(mod, "read_ledger_filtered")
        assert hasattr(mod, "read_state")

    def test_script_repo_name(self, repo_root: Path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_clearinghouse",
            repo_root / "scripts" / "check_clearinghouse.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.REPO_NAME == "autonomous-research-engineer"


# ── CLAUDE.md content tests ─────────────────────────────────────────────────

class TestClaudeMd:
    """Verify CLAUDE.md contains required sections."""

    def test_startup_protocol(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "Startup Protocol" in content

    def test_mentions_newsletter(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "newsletter" in content.lower()

    def test_mentions_ledger(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "ledger" in content.lower()

    def test_mentions_agent_factors(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "agent-factors" in content or "agent_factors" in content

    def test_mentions_blueprint(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "1832_autonomous_research_engineer_blueprint" in content

    def test_mentions_documentation_ordering(self, repo_root: Path):
        content = (repo_root / "CLAUDE.md").read_text()
        assert "session log" in content.lower() or "documentation ordering" in content.lower()
