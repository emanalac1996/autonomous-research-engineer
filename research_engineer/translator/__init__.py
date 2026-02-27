"""Stage 4: Blueprint translation — WU decomposition, change patterns, serialization."""

from research_engineer.translator.change_patterns import (
    ChangePatternReport,
    ChangePatternStats,
    mine_ledger,
)
from research_engineer.translator.manifest_targeter import (
    FileTarget,
    FileTargeting,
    identify_targets,
)
from research_engineer.translator.serializer import serialize_blueprint, write_blueprint
from research_engineer.translator.translator import (
    TranslationInput,
    TranslationResult,
    translate,
)
from research_engineer.translator.wu_decomposer import (
    DecompositionConfig,
    decompose,
    validate_decomposition,
)

__all__ = [
    "ChangePatternReport",
    "ChangePatternStats",
    "mine_ledger",
    "FileTarget",
    "FileTargeting",
    "identify_targets",
    "serialize_blueprint",
    "write_blueprint",
    "TranslationInput",
    "TranslationResult",
    "translate",
    "DecompositionConfig",
    "decompose",
    "validate_decomposition",
]
