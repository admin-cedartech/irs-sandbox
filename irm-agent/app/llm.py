"""LLM extraction layer: swappable Bedrock provider + deterministic mock.

Both providers return the same shape: a dict with a "rules" list of raw rule
dicts. The guardrail layer validates/ grounds them afterward.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .config import settings
from .prompt import SYSTEM_PROMPT, build_user_prompt


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> Dict[str, Any]:
    """Pull the first JSON object out of a model response."""
    text = text.strip()
    # Strip markdown code fences if present.
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("No JSON object found in LLM response.")
    return json.loads(text[start : end + 1])


class MockProvider:
    """Deterministic offline provider.

    It parses the well-known sample IRM sentences into rules so the demo runs
    without AWS. Every source_quote is a real substring of the input text, so
    the grounding guardrail passes honestly.
    """

    name = "mock"
    model_id = None

    def extract(self, source_text: str, section_hint: str) -> Dict[str, Any]:
        rules: List[Dict[str, Any]] = []
        t = source_text

        def quote_for(needle: str) -> str:
            idx = t.find(needle)
            return t[idx : idx + len(needle)] if idx != -1 else needle

        catalog = [
            {
                "trigger": "Form 1310 is not required",
                "rule": {
                    "rule_id": "R-001",
                    "name": "Surviving spouse joint return",
                    "description": "Surviving spouse filing a joint return does not need Form 1310; refund may be issued in both names.",
                    "conditions": [
                        {"fact": "claim.claimant_type", "operator": "==", "value": "surviving_spouse", "description": "Claimant is a surviving spouse"},
                        {"fact": "return.joint", "operator": "==", "value": True, "description": "Original or amended joint return"},
                    ],
                    "action": "Issue the refund in both names without requiring Form 1310.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "a Form 1310 is not required and the refund may be issued in both names",
                    "confidence": 0.9,
                },
            },
            {
                "trigger": "both the Form 1310\nand the court certificate must be received together",
                "rule": {
                    "rule_id": "R-002",
                    "name": "Court-appointed representative documentation",
                    "description": "Court-appointed personal representative must submit Form 1310 and court certificate together; otherwise correspond to request it.",
                    "conditions": [
                        {"fact": "claim.court_appointed_representative", "operator": "==", "value": True, "description": "Claimant is a court-appointed personal representative"},
                    ],
                    "action": "Require Form 1310 and court certificate together; if court certificate missing, correspond to request documentation.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "both the Form 1310\nand the court certificate must be received together",
                    "confidence": 0.88,
                },
            },
            {
                "trigger": "-X freeze will be present",
                "rule": {
                    "rule_id": "R-003",
                    "name": "Minus-X freeze suspend and release",
                    "description": "If a -X freeze will post and systemic refund criteria are met, suspend until freeze posts, then release.",
                    "conditions": [
                        {"fact": "account.minus_x_freeze_pending", "operator": "==", "value": True, "description": "-X freeze will be present after adjustment posts"},
                        {"fact": "refund.systemic_criteria_met", "operator": "==", "value": True, "description": "Meets criteria for a systemic refund"},
                    ],
                    "action": "Suspend the case until the freeze has posted, then release the refund.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "suspend the case until the freeze has posted and\nthen release the refund",
                    "confidence": 0.85,
                },
            },
            {
                "trigger": "input TC 971\nAC 807",
                "rule": {
                    "rule_id": "R-004",
                    "name": "Current year systemic release via TC 971 AC 807",
                    "description": "For a current year refund where TC 971 AC 807 applies, input it to release systemically.",
                    "conditions": [
                        {"fact": "refund.tax_year_status", "operator": "==", "value": "current_year", "description": "Current year refund"},
                        {"fact": "procedure.tc971_ac807_applies", "operator": "==", "value": True, "description": "TC 971 AC 807 procedure applies"},
                    ],
                    "action": "Input TC 971 AC 807 to release the refund systemically.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "input TC 971\nAC 807 to release the refund systemically",
                    "confidence": 0.86,
                },
            },
            {
                "trigger": "considered prior year and a manual refund is\nrequired",
                "rule": {
                    "rule_id": "R-005",
                    "name": "Prior year manual refund",
                    "description": "After the current year processing cycle ends, later cycles are prior year and require a manual refund.",
                    "conditions": [
                        {"fact": "refund.tax_year_status", "operator": "==", "value": "prior_year", "description": "Prior year (after current cycle ended)"},
                    ],
                    "action": "Issue a manual refund; perfect Form 1310 with the tax year.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "considered prior year and a manual refund is\nrequired",
                    "confidence": 0.84,
                },
            },
            {
                "trigger": "CII case",
                "rule": {
                    "rule_id": "R-006",
                    "name": "CII case note",
                    "description": "For CII cases, do not refile Form 1310 but leave a case note documenting the action.",
                    "conditions": [
                        {"fact": "case.cii", "operator": "==", "value": True, "description": "Case is a CII case"},
                    ],
                    "action": "Do not refile Form 1310; leave a case note documenting the action taken.",
                    "source_reference": "IRM 21.6.6.2.21.2",
                    "source_quote": "there is no need to refile the Form 1310, but leave a\ncase note",
                    "confidence": 0.83,
                },
            },
        ]

        for entry in catalog:
            if entry["trigger"] in t:
                rule = dict(entry["rule"])
                rule["source_quote"] = quote_for(rule["source_quote"])
                rules.append(rule)

        return {"rules": rules}


class BedrockProvider:
    """Amazon Bedrock (Claude) provider via boto3."""

    def __init__(self) -> None:
        import boto3  # imported lazily so mock mode needs no AWS deps at runtime

        self.name = "bedrock"
        self.model_id = settings.bedrock_model_id
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def extract(self, source_text: str, section_hint: str) -> Dict[str, Any]:
        # Uses the Bedrock Converse API, which is the recommended, model-agnostic
        # way to call Claude 4.x. Works with cross-region inference profile IDs
        # (e.g. "us.anthropic.claude-sonnet-4-5-20250929-v1:0").
        kwargs: Dict[str, Any] = {
            "modelId": self.model_id,
            "system": [{"text": SYSTEM_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": build_user_prompt(source_text, section_hint)}],
                }
            ],
            "inferenceConfig": {"maxTokens": 4096, "temperature": 0},
        }
        # Optional Amazon Bedrock Guardrails (managed content safety).
        if settings.bedrock_guardrail_id and settings.bedrock_guardrail_version:
            kwargs["guardrailConfig"] = {
                "guardrailIdentifier": settings.bedrock_guardrail_id,
                "guardrailVersion": settings.bedrock_guardrail_version,
            }

        try:
            resp = self._client.converse(**kwargs)
        except Exception as exc:  # boto/client errors
            raise LLMError(f"Bedrock invocation failed: {exc}") from exc

        # Converse returns output.message.content -> list of blocks with "text".
        blocks = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        return _extract_json(text)


def get_provider():
    if settings.llm_provider.lower() == "bedrock":
        return BedrockProvider()
    return MockProvider()
