"""Stage 1: Paper comprehension — parsing, schema, topology change detection."""

from research_engineer.comprehension.parser import parse_paper
from research_engineer.comprehension.schema import (
    ComprehensionSummary,
    MathCore,
    PaperClaim,
    PaperSection,
    SectionType,
)
from research_engineer.comprehension.topology import (
    TopologyChange,
    TopologyChangeType,
    analyze_topology,
)
from research_engineer.comprehension.vocabulary import (
    VocabularyMapping,
    build_vocabulary_mapping,
)

__all__ = [
    "ComprehensionSummary",
    "MathCore",
    "PaperClaim",
    "PaperSection",
    "SectionType",
    "parse_paper",
    "TopologyChange",
    "TopologyChangeType",
    "analyze_topology",
    "VocabularyMapping",
    "build_vocabulary_mapping",
]
