"""Comprehension schema: Pydantic v2 models for paper comprehension output.

Defines ComprehensionSummary, PaperClaim, MathCore, PaperSection, and SectionType —
the structured output of the paper comprehension pipeline (Stage 1).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SectionType(str, Enum):
    """Standard paper section types."""

    title = "title"
    abstract = "abstract"
    method = "method"
    results = "results"
    limitations = "limitations"
    other = "other"


class PaperSection(BaseModel):
    """A single extracted section from a paper."""

    model_config = ConfigDict()

    section_type: SectionType
    heading: str = ""
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("section content must not be empty")
        return v


class PaperClaim(BaseModel):
    """A quantitative or qualitative claim extracted from a paper."""

    model_config = ConfigDict()

    claim_text: str
    metric_name: str | None = None
    metric_value: float | None = None
    baseline_comparison: float | None = None
    dataset: str | None = None

    @field_validator("claim_text")
    @classmethod
    def claim_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("claim_text must not be empty")
        return v

    @field_validator("metric_value", "baseline_comparison")
    @classmethod
    def metric_finite(cls, v: float | None) -> float | None:
        if v is not None and not (-1e12 < v < 1e12):
            raise ValueError("metric value must be finite")
        return v


class MathCore(BaseModel):
    """Mathematical core extracted from a paper's method section."""

    model_config = ConfigDict()

    formulation: str | None = None
    complexity: str | None = None
    assumptions: list[str] = Field(default_factory=list)


class ComprehensionSummary(BaseModel):
    """Structured comprehension output from paper parsing.

    This is the primary output of Stage 1 and the input to Stages 2-4.
    """

    model_config = ConfigDict()

    title: str = ""
    transformation_proposed: str
    inputs_required: list[str] = Field(default_factory=list)
    outputs_produced: list[str] = Field(default_factory=list)
    claims: list[PaperClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    mathematical_core: MathCore = Field(default_factory=MathCore)
    sections: list[PaperSection] = Field(default_factory=list)
    paper_terms: list[str] = Field(default_factory=list)

    @field_validator("transformation_proposed")
    @classmethod
    def transformation_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("transformation_proposed must not be empty")
        return v
