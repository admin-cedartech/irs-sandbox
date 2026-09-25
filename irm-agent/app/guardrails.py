"""Guardrail layer: turns raw LLM output into trustworthy business rules.

Layers applied here:
  2. Schema validation      - each rule must fit the Pydantic BusinessRule shape.
  3. Source grounding       - source_quote must actually exist in the source text.
  4. Confidence thresholds  - low-confidence or ungrounded rules are flagged.

(Layer 1 is the constrained prompt in prompt.py; optional Amazon Bedrock
Guardrails are applied inside the Bedrock provider.)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from .config import settings
from .schemas import BusinessRule, ExtractionMetadata


def _normalize(text: str) -> str:
    """Collapse whitespace so grounding tolerates PDF line-break noise."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_grounded(quote: str, source_text: str) -> bool:
    if not quote:
        return False
    return _normalize(quote) in _normalize(source_text)


def apply_guardrails(
    raw: Dict[str, Any],
    source_text: str,
    provider_name: str,
    model_id: str | None,
) -> Tuple[List[BusinessRule], ExtractionMetadata]:
    raw_rules = raw.get("rules", []) if isinstance(raw, dict) else []

    accepted: List[BusinessRule] = []
    dropped = 0
    flagged = 0

    for item in raw_rules:
        # Layer 2: schema validation.
        try:
            rule = BusinessRule.model_validate(item)
        except ValidationError:
            dropped += 1
            continue

        # Layer 3: grounding.
        rule.grounded = _is_grounded(rule.source_quote, source_text)
        if not rule.grounded:
            # A rule whose quote isn't in the source is a likely hallucination.
            # Keep it but flag loudly for human review rather than silently trust.
            rule.flagged_for_review = True
            rule.review_reason = "source_quote not found in document (possible hallucination)"
            flagged += 1
            accepted.append(rule)
            continue

        # Layer 4: confidence threshold.
        if rule.confidence < settings.confidence_threshold:
            rule.flagged_for_review = True
            rule.review_reason = (
                f"confidence {rule.confidence:.2f} below threshold "
                f"{settings.confidence_threshold:.2f}"
            )
            flagged += 1

        accepted.append(rule)

    metadata = ExtractionMetadata(
        provider=provider_name,
        model_id=model_id,
        source_chars=len(source_text),
        rules_returned_by_llm=len(raw_rules),
        rules_accepted=len(accepted),
        rules_flagged=flagged,
        rules_dropped=dropped,
        guardrails_applied=[
            "constrained_prompt",
            "schema_validation",
            "source_grounding",
            "confidence_threshold",
        ]
        + (["bedrock_guardrails"] if settings.bedrock_guardrail_id else []),
    )
    return accepted, metadata
