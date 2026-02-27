"""CLI tool for feasibility checking: assess implementability of a classified paper.

Usage:
    python3 scripts/check_feasibility.py --input summary.json --classification classification.json
    python3 scripts/check_feasibility.py --input summary.json --classification classification.json --manifests-dir /path/to/manifests
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run feasibility check CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on FEASIBLE/FEASIBLE_WITH_ADAPTATION,
                   1 on ESCALATE/NOT_FEASIBLE,
                   2 on error.
    """
    parser = argparse.ArgumentParser(
        description="Check feasibility of a classified research paper."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to ComprehensionSummary JSON file.",
    )
    parser.add_argument(
        "--classification",
        required=True,
        help="Path to ClassificationResult JSON file.",
    )
    parser.add_argument(
        "--manifests-dir",
        default=None,
        help="Path to manifests directory (default: ../clearinghouse/manifests/).",
    )

    args = parser.parse_args(argv)

    try:
        # Read inputs
        summary_raw = Path(args.input).read_text()
        classification_raw = Path(args.classification).read_text()

        # Parse models
        from research_engineer.comprehension.schema import ComprehensionSummary
        from research_engineer.classifier.types import ClassificationResult

        summary = ComprehensionSummary.model_validate_json(summary_raw)
        classification = ClassificationResult.model_validate_json(classification_raw)

        # Determine manifests directory
        if args.manifests_dir:
            manifests_dir = Path(args.manifests_dir)
        else:
            manifests_dir = Path(__file__).resolve().parent.parent.parent / "clearinghouse" / "manifests"

        # Run feasibility assessment
        from research_engineer.feasibility.gate import assess_feasibility, FeasibilityStatus

        result = assess_feasibility(summary, classification, manifests_dir)

        # Output
        print(result.model_dump_json(indent=2))

        # Exit code based on status
        if result.status in (FeasibilityStatus.FEASIBLE, FeasibilityStatus.FEASIBLE_WITH_ADAPTATION):
            return 0
        return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
