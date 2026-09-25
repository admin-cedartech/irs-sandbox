"""Pydantic models that define and validate the extracted business rules.

These models ARE the first guardrail: the LLM output must fit this exact shape
or it is rejected. Every rule must carry a source_quote so we can verify it is
grounded in the real IRM text (anti-hallucination).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Operator(str, Enum):
    EQ = "=="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    CONTAINS = "contains"


class Condition(BaseModel):
    """A single testable condition, e.g. taxpayer.age < 25."""

    fact: str = Field(..., description="Dotted fact/attribute the condition tests, e.g. 'claim.form_1310_present'.")
    operator: Operator = Field(..., description="Comparison operator.")
    value: Any = Field(None, description="Value to compare against. May be null for 'exists'.")
    description: Optional[str] = Field(None, description="Plain-language restatement of the condition.")


class BusinessRule(BaseModel):
    """One extracted business rule, grounded in the source document."""

    rule_id: str = Field(..., description="Stable identifier, e.g. 'R-001'.")
    name: str = Field(..., description="Short human-readable name.")
    description: str = Field(..., description="What the rule does in plain language.")
    conditions: List[Condition] = Field(default_factory=list, description="ALL must be true (logical AND).")
    action: str = Field(..., description="The action/outcome when conditions are met.")
    source_reference: str = Field(..., description="IRM section citation, e.g. 'IRM 21.6.6.2.21.2'.")
    source_quote: str = Field(..., description="Verbatim text from the IRM this rule is based on. Used for grounding verification.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence 0..1.")

    # Populated by the guardrail layer, not the LLM.
    grounded: bool = Field(default=False, description="True if source_quote was verified against the source text.")
    flagged_for_review: bool = Field(default=False, description="True if low confidence or ungrounded.")
    review_reason: Optional[str] = Field(default=None, description="Why the rule was flagged, if it was.")


class ExtractionMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}

    provider: str
    model_id: Optional[str] = None
    source_chars: int
    rules_returned_by_llm: int
    rules_accepted: int
    rules_flagged: int
    rules_dropped: int
    guardrails_applied: List[str]


class ExtractRulesResponse(BaseModel):
    process_name: str = Field(default="Processing Decedent Account Refunds")
    rules: List[BusinessRule]
    metadata: ExtractionMetadata


class GenerateBpmnRequest(BaseModel):
    process_name: str = Field(default="Processing Decedent Account Refunds")
    rules: List[BusinessRule]
