"""Classification types for the innovation-type classifier (Stage 2).

Defines the 4-type innovation taxonomy and the ClassificationResult model
that all downstream stages (feasibility gate, translator) consume.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_factors.g_layer.escalation import EscalationTrigger


class InnovationType(str, Enum):
    """The four innovation types for paper classification."""

    parameter_tuning = "parameter_tuning"
    modular_swap = "modular_swap"
    pipeline_restructuring = "pipeline_restructuring"
    architectural_innovation = "architectural_innovation"


class ClassificationResult(BaseModel):
    """Result of innovation-type classification."""

    model_config = ConfigDict()

    innovation_type: InnovationType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    topology_signal: str = ""
    manifest_evidence: list[str] = Field(default_factory=list)
    escalation_trigger: EscalationTrigger | None = None

    @field_validator("rationale")
    @classmethod
    def rationale_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rationale must not be empty")
        return v
