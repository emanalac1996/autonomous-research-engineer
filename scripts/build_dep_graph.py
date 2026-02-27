"""CLI tool for building and querying the codebase dependency graph.

Usage:
    python3 scripts/build_dep_graph.py --stats
    python3 scripts/build_dep_graph.py --query downstream <node_id>
    python3 scripts/build_dep_graph.py --manifests-dir /path/to/manifests --stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run dependency graph CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Build and query the codebase dependency graph."
    )
    parser.add_argument(
        "--manifests-dir",
        default=None,
        help="Path to manifests directory (default: ../clearinghouse/manifests/).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print graph statistics summary.",
    )
    parser.add_argument(
        "--query",
        nargs=2,
        metavar=("QUERY_TYPE", "NODE_ID"),
        help="Query the graph: 'downstream <node_id>' or 'upstream <node_id>'.",
    )

    args = parser.parse_args(argv)

    try:
        from research_engineer.feasibility.dependency_graph import build_dependency_graph

        # Determine manifests directory
        if args.manifests_dir:
            manifests_dir = Path(args.manifests_dir)
        else:
            manifests_dir = Path(__file__).resolve().parent.parent.parent / "clearinghouse" / "manifests"

        # Build graph
        graph = build_dependency_graph(manifests_dir)

        if args.query:
            query_type, node_id = args.query
            if query_type == "downstream":
                result = sorted(graph.downstream(node_id))
            elif query_type == "upstream":
                result = sorted(graph.upstream(node_id))
            else:
                print(f"Unknown query type: {query_type}", file=sys.stderr)
                return 1
            print(json.dumps(result, indent=2))
        else:
            # Default: print stats
            stats = graph.stats()
            print(json.dumps(stats.model_dump(), indent=2))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
