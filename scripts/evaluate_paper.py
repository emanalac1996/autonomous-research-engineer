"""CLI tool for paper evaluation: classify and optionally translate to blueprint.

Usage:
    python3 scripts/evaluate_paper.py --classify-only --input summary.json
    python3 scripts/evaluate_paper.py --classify-only --input - < summary.json
    python3 scripts/evaluate_paper.py --translate --input summary.json --output-dir plans/
    python3 scripts/evaluate_paper.py --translate --input summary.json --manifests-dir ... --ledger ...
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
        "--translate",
        action="store_true",
        help="Run full pipeline: classify + translate to ADR-005 blueprint.",
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
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for blueprint files (used with --translate).",
    )
    parser.add_argument(
        "--manifests-dir",
        default=None,
        help="Path to manifests directory for file targeting.",
    )
    parser.add_argument(
        "--ledger",
        default=None,
        help="Path to clearinghouse ledger for historical patterns.",
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

        classification = classify(summary, topology, [], registry)

        if args.classify_only:
            print(classification.model_dump_json(indent=2))
            return 0

        if args.translate:
            from research_engineer.translator.translator import (
                TranslationInput,
                translate,
            )
            from research_engineer.translator.serializer import write_blueprint

            output_dir = Path(args.output_dir) if args.output_dir else Path("plans")
            manifests_dir = Path(args.manifests_dir) if args.manifests_dir else None
            ledger_path = Path(args.ledger) if args.ledger else None

            translation_input = TranslationInput(
                summary=summary,
                classification=classification,
                manifests_dir=manifests_dir,
                ledger_path=ledger_path,
            )

            result = translate(translation_input)
            blueprint_path = write_blueprint(result, output_dir)

            output = {
                "blueprint_path": str(blueprint_path),
                "wu_count": result.blueprint.total_wu_count,
                "validation_passed": result.validation_report.overall_passed,
                "test_estimate_low": result.test_estimate_low,
                "test_estimate_high": result.test_estimate_high,
            }
            print(json.dumps(output, indent=2))
            return 0

        # Default: classify only
        print(classification.model_dump_json(indent=2))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
