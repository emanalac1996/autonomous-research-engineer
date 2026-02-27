"""Historical change pattern analyzer: mine ledger for blueprint statistics.

Reads the clearinghouse ledger (JSONL) to extract historical patterns about
WU counts, test ratios, and phase counts per meta-category and innovation type.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ChangePatternStats(BaseModel):
    """Statistics for one group of ledger entries."""

    avg_wu_count: float = 0.0
    avg_test_ratio: float = 0.0
    sample_count: int = 0
    common_phase_count: int = 1


class ChangePatternReport(BaseModel):
    """Aggregate change pattern report from ledger mining."""

    by_meta_category: dict[str, ChangePatternStats] = Field(default_factory=dict)
    by_innovation_type: dict[str, ChangePatternStats] = Field(default_factory=dict)
    total_entries: int = 0
    entries_with_blueprint_ref: int = 0


# Default fallback stats per innovation type (from plan spec)
DEFAULT_PATTERN_STATS: dict[str, ChangePatternStats] = {
    "parameter_tuning": ChangePatternStats(
        avg_wu_count=2.0, avg_test_ratio=4.0, sample_count=0, common_phase_count=1
    ),
    "modular_swap": ChangePatternStats(
        avg_wu_count=4.0, avg_test_ratio=3.5, sample_count=0, common_phase_count=1
    ),
    "pipeline_restructuring": ChangePatternStats(
        avg_wu_count=8.0, avg_test_ratio=3.0, sample_count=0, common_phase_count=2
    ),
    "architectural_innovation": ChangePatternStats(
        avg_wu_count=14.0, avg_test_ratio=2.5, sample_count=0, common_phase_count=3
    ),
}


_INNOVATION_KEYWORDS: dict[str, list[str]] = {
    "parameter_tuning": ["parameter", "tuning", "config", "weight", "threshold"],
    "modular_swap": ["swap", "replace", "substitute", "component", "module swap"],
    "pipeline_restructuring": [
        "pipeline", "restructure", "reorder", "stage", "topology",
    ],
    "architectural_innovation": [
        "architecture", "primitive", "novel", "new framework", "scaffold",
    ],
}


def _infer_innovation_type(entry: dict) -> str | None:
    """Infer innovation type from ledger entry text fields.

    Returns innovation type string or None if unrecognizable.
    """
    text_fields = " ".join(
        str(entry.get(f, "")).lower()
        for f in ("title", "description", "summary", "claim", "detail")
    )

    best_type: str | None = None
    best_score = 0

    for itype, keywords in _INNOVATION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_fields)
        if score > best_score:
            best_score = score
            best_type = itype

    return best_type if best_score > 0 else None


def _extract_wu_count(entry: dict) -> int | None:
    """Extract WU count from a ledger entry if available."""
    # Check working_units_completed list
    wus = entry.get("working_units_completed")
    if isinstance(wus, list) and wus:
        return len(wus)

    # Check summary for WU mentions
    for field in ("summary", "description", "detail"):
        text = str(entry.get(field, ""))
        # Look for "N WUs" or "N working units" patterns
        import re
        match = re.search(r"(\d+)\s+(?:WU|working\s+unit)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def _extract_test_count(entry: dict) -> int | None:
    """Extract test count from a ledger entry."""
    tc = entry.get("test_count")
    if isinstance(tc, (int, float)) and tc > 0:
        return int(tc)
    return None


def mine_ledger(ledger_path: Path) -> ChangePatternReport:
    """Mine the clearinghouse ledger for historical change patterns.

    Args:
        ledger_path: Path to the JSONL ledger file.

    Returns:
        ChangePatternReport with statistics by meta-category and innovation type.
    """
    if not ledger_path.exists():
        return ChangePatternReport(
            by_innovation_type={
                k: v.model_copy() for k, v in DEFAULT_PATTERN_STATS.items()
            }
        )

    entries: list[dict] = []
    try:
        for line in ledger_path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return ChangePatternReport(
            by_innovation_type={
                k: v.model_copy() for k, v in DEFAULT_PATTERN_STATS.items()
            }
        )

    total_entries = len(entries)
    entries_with_blueprint_ref = sum(
        1 for e in entries if e.get("blueprint_ref")
    )

    # Group by meta_category
    meta_groups: dict[str, list[dict]] = {}
    for entry in entries:
        mc = entry.get("meta_category")
        if mc:
            meta_groups.setdefault(mc, []).append(entry)

    # Group by inferred innovation type
    itype_groups: dict[str, list[dict]] = {}
    for entry in entries:
        itype = _infer_innovation_type(entry)
        if itype:
            itype_groups.setdefault(itype, []).append(entry)

    def _compute_stats(group: list[dict]) -> ChangePatternStats:
        wu_counts = [c for e in group if (c := _extract_wu_count(e)) is not None]
        test_counts = [c for e in group if (c := _extract_test_count(e)) is not None]

        avg_wu = sum(wu_counts) / len(wu_counts) if wu_counts else 0.0
        # test_ratio = tests / wus
        avg_test_ratio = 0.0
        if wu_counts and test_counts:
            ratios = []
            for tc, wc in zip(test_counts, wu_counts):
                if wc > 0:
                    ratios.append(tc / wc)
            avg_test_ratio = sum(ratios) / len(ratios) if ratios else 0.0

        return ChangePatternStats(
            avg_wu_count=avg_wu,
            avg_test_ratio=avg_test_ratio,
            sample_count=len(group),
            common_phase_count=max(1, int(avg_wu / 5)) if avg_wu > 0 else 1,
        )

    by_meta = {mc: _compute_stats(g) for mc, g in meta_groups.items()}
    by_itype = {it: _compute_stats(g) for it, g in itype_groups.items()}

    # Merge with defaults if < 3 entries with blueprint_ref
    if entries_with_blueprint_ref < 3:
        for itype, default_stats in DEFAULT_PATTERN_STATS.items():
            if itype not in by_itype:
                by_itype[itype] = default_stats.model_copy()
            else:
                # Blend: weighted average favoring defaults for sparse data
                existing = by_itype[itype]
                weight = min(existing.sample_count / 3.0, 1.0)
                by_itype[itype] = ChangePatternStats(
                    avg_wu_count=(
                        existing.avg_wu_count * weight
                        + default_stats.avg_wu_count * (1 - weight)
                    ),
                    avg_test_ratio=(
                        existing.avg_test_ratio * weight
                        + default_stats.avg_test_ratio * (1 - weight)
                    ),
                    sample_count=existing.sample_count,
                    common_phase_count=existing.common_phase_count,
                )

    return ChangePatternReport(
        by_meta_category=by_meta,
        by_innovation_type=by_itype,
        total_entries=total_entries,
        entries_with_blueprint_ref=entries_with_blueprint_ref,
    )
