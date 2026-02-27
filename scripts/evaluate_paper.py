"""CLI tool for paper evaluation: classify innovation type from a ComprehensionSummary.

Usage:
    python3 scripts/evaluate_paper.py --classify-only --input summary.json
    python3 scripts/evaluate_paper.py --classify-only --input - < summary.json
    python3 scripts/evaluate_paper.py --classify-only --input summary.json --artifact-store /tmp/store
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run paper evaluation CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Evaluate a research paper's innovation type."
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="Run only the classification stage (no feasibility/translation).",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to ComprehensionSummary JSON file, or '-' for stdin.",
    )
    parser.add_argument(
        "--artifact-store",
        default="artifacts/store/",
        help="Path to artifact store directory (default: artifacts/store/).",
    )

    args = parser.parse_args(argv)

    try:
        # Read input
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.input).read_text()

        # Parse ComprehensionSummary
        from research_engineer.comprehension.schema import ComprehensionSummary

        summary = ComprehensionSummary.model_validate_json(raw)

        # Analyze topology
        from research_engineer.comprehension.topology import analyze_topology

        topology = analyze_topology(summary)

        # Initialize artifact registry
        from agent_factors.artifacts import ArtifactRegistry

        store_dir = Path(args.artifact_store)
        store_dir.mkdir(parents=True, exist_ok=True)
        registry = ArtifactRegistry(store_dir=store_dir)

        # Ensure seed artifact
        from research_engineer.classifier.seed_artifact import register_seed_artifact

        register_seed_artifact(registry)

        # Classify
        from research_engineer.classifier.heuristics import classify

        result = classify(summary, topology, [], registry)

        # Output
        print(result.model_dump_json(indent=2))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
