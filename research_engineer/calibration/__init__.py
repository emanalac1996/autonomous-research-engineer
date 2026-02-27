"""Stage 5: Trust calibration — accuracy tracking, maturity gating, heuristic evolution."""

from research_engineer.calibration.heuristic_evolver import (
    EvolutionProposal,
    EvolutionResult,
    MisclassificationPattern,
    RuleMutation,
    analyze_misclassifications,
    apply_evolution,
    propose_mutations,
)
from research_engineer.calibration.maturity_assessor import (
    CalibrationEvidence,
    MaturityAssessment,
    assess_maturity,
)
from research_engineer.calibration.report import (
    CalibrationInput,
    CalibrationReport,
    CalibrationReportMarkdown,
    generate_report,
    render_markdown,
)
from research_engineer.calibration.tracker import (
    AccuracyRecord,
    AccuracyReport,
    AccuracyTracker,
    ClassificationConfusionMatrix,
    PerTypeAccuracy,
)

__all__ = [
    # tracker (5.1)
    "AccuracyRecord",
    "AccuracyReport",
    "AccuracyTracker",
    "ClassificationConfusionMatrix",
    "PerTypeAccuracy",
    # maturity_assessor (5.2)
    "CalibrationEvidence",
    "MaturityAssessment",
    "assess_maturity",
    # heuristic_evolver (5.3)
    "EvolutionProposal",
    "EvolutionResult",
    "MisclassificationPattern",
    "RuleMutation",
    "analyze_misclassifications",
    "apply_evolution",
    "propose_mutations",
    # report (5.4)
    "CalibrationInput",
    "CalibrationReport",
    "CalibrationReportMarkdown",
    "generate_report",
    "render_markdown",
]
