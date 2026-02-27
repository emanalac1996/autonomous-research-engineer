#!/usr/bin/env python3
"""Clearinghouse integration: read newsletter, ledger, and state summary.

Usage:
    python3 scripts/check_clearinghouse.py              # full startup check
    python3 scripts/check_clearinghouse.py --newsletter  # newsletter only
    python3 scripts/check_clearinghouse.py --ledger      # filtered ledger entries only
    python3 scripts/check_clearinghouse.py --state       # state summary only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_NAME = "autonomous-research-engineer"
CLEARINGHOUSE = Path(__file__).resolve().parent.parent.parent / "clearinghouse"


def read_newsletter() -> str | None:
    """Read the current clearinghouse newsletter."""
    newsletter = CLEARINGHOUSE / "coordination" / "newsletter" / "current.md"
    if not newsletter.is_file():
        print(f"[WARN] Newsletter not found: {newsletter}", file=sys.stderr)
        return None
    text = newsletter.read_text(encoding="utf-8")
    print(f"[OK] Newsletter read ({len(text)} chars)")
    return text


def read_ledger_filtered() -> list[dict]:
    """Read ledger entries where autonomous-research-engineer appears in affected_repos."""
    ledger = CLEARINGHOUSE / "coordination" / "ledger.jsonl"
    if not ledger.is_file():
        print(f"[WARN] Ledger not found: {ledger}", file=sys.stderr)
        return []
    entries = []
    for line in ledger.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        affected = entry.get("affected_repos", [])
        if REPO_NAME in affected:
            entries.append(entry)
    print(f"[OK] Ledger scanned — {len(entries)} entries affect {REPO_NAME}")
    for e in entries:
        eid = e.get("entry_id", "?")
        title = e.get("title", "(no title)")
        print(f"  {eid}: {title}")
    return entries


def read_state() -> str | None:
    """Read the clearinghouse state summary."""
    state = CLEARINGHOUSE / "coordination" / "state" / "current_state.yaml"
    if not state.is_file():
        print(f"[WARN] State file not found: {state}", file=sys.stderr)
        return None
    text = state.read_text(encoding="utf-8")
    print(f"[OK] State summary read ({len(text)} chars)")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Check clearinghouse integration")
    parser.add_argument("--newsletter", action="store_true", help="Read newsletter only")
    parser.add_argument("--ledger", action="store_true", help="Read filtered ledger only")
    parser.add_argument("--state", action="store_true", help="Read state summary only")
    args = parser.parse_args()

    # If no specific flag, do full startup check
    run_all = not (args.newsletter or args.ledger or args.state)

    if not CLEARINGHOUSE.is_dir():
        print(f"[ERROR] Clearinghouse not found at {CLEARINGHOUSE}", file=sys.stderr)
        sys.exit(1)

    print(f"Clearinghouse: {CLEARINGHOUSE}")
    print()

    if run_all or args.newsletter:
        read_newsletter()
        print()

    if run_all or args.ledger:
        read_ledger_filtered()
        print()

    if run_all or args.state:
        read_state()
        print()

    print("Startup check complete.")


if __name__ == "__main__":
    main()
