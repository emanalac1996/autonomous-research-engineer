"""CLI tool for generating calibration reports.

Usage:
    python3 scripts/calibration_report.py --records accuracy.jsonl
    python3 scripts/calibration_report.py --records accuracy.jsonl --json
    python3 scripts/calibration_report.py --records accuracy.jsonl --apply-evolution
    python3 scripts/calibration_report.py --records accuracy.jsonl --output report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run calibration report CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success/ready, 1 if maturity not ready, 2 on error.
    """
    parser = argparse.ArgumentParser(
        description="Generate calibration report for classification accuracy."
    )
    parser.add_argument(
        "--records",
        required=True,
        help="Path to JSONL file with AccuracyRecord data.",
    )
    parser.add_argument(
        "--artifact-store",
        default="artifacts/store/",
        help="Path to artifact store directory (default: artifacts/store/).",
    )
    parser.add_argument(
        "--repo",
        default="autonomous-research-engineer",
        help="Repository name (default: autonomous-research-engineer).",
    )
    parser.add_argument(
        "--maturity-level",
        default="foundational",
        help="Current maturity level (default: foundational).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write markdown report (default: stdout).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of markdown.",
    )
    parser.add_argument(
        "--apply-evolution",
        action="store_true",
        help="Auto-apply proposed heuristic mutations.",
    )

    args = parser.parse_args(argv)

    try:
        from agent_factors.artifacts import ArtifactRegistry

        from research_engineer.calibration.heuristic_evolver import apply_evolution
        from research_engineer.calibration.report import (
            CalibrationInput,
            generate_report,
            render_markdown,
        )
        from research_engineer.calibration.tracker import AccuracyTracker
        from research_engineer.classifier.seed_artifact import register_seed_artifact

        # Build tracker from records file
        records_path = Path(args.records)
        tracker = AccuracyTracker(store_path=records_path)

        # Build artifact registry
        store_dir = Path(args.artifact_store)
        store_dir.mkdir(parents=True, exist_ok=True)
        registry = ArtifactRegistry(store_dir=store_dir)
        register_seed_artifact(registry)

        # Generate report
        cal_input = CalibrationInput(
            tracker=tracker,
            registry=registry,
            repo_name=args.repo,
            current_maturity_level=args.maturity_level,
        )
        report = generate_report(cal_input)

        # Apply evolution if requested
        if args.apply_evolution and report.evolution_proposal:
            apply_evolution(report.evolution_proposal, registry, auto_apply=True)

        # Output
        if args.json:
            print(report.model_dump_json(indent=2))
        else:
            md = render_markdown(report)
            if args.output:
                Path(args.output).write_text(md.content)
            else:
                print(md.content)

        # Exit code based on maturity recommendation
        if report.maturity_assessment.recommendation == "ready":
            return 0
        return 1 if report.maturity_assessment.recommendation != "ready" else 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
