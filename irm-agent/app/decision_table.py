"""Generate a decision-table JSON view of the business rules for Pega.

Pega often imports decision logic as a table: each rule is a row with its
conditions (the "when") and the action (the "then"). This is a flatter, more
import-friendly representation than BPMN for pure decision logic.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .schemas import BusinessRule


def _collect_condition_columns(rules: List[BusinessRule]) -> List[str]:
    """Stable, de-duplicated list of every fact used across all rules."""
    seen: List[str] = []
    for rule in rules:
        for cond in rule.conditions:
            if cond.fact not in seen:
                seen.append(cond.fact)
    return seen


def rules_to_decision_table(process_name: str, rules: List[BusinessRule]) -> Dict[str, Any]:
    """Build a decision table: shared condition columns + one row per rule."""
    columns = _collect_condition_columns(rules)

    rows: List[Dict[str, Any]] = []
    for rule in rules:
        # Map this rule's conditions by fact for quick lookup.
        by_fact = {c.fact: c for c in rule.conditions}
        when: Dict[str, Any] = {}
        for col in columns:
            cond = by_fact.get(col)
            if cond is None:
                when[col] = None  # not relevant to this rule ("-")
            else:
                when[col] = {"operator": cond.operator.value, "value": cond.value}

        rows.append(
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "when": when,
                "then": rule.action,
                "source_reference": rule.source_reference,
                "source_quote": rule.source_quote,
                "confidence": rule.confidence,
                "grounded": rule.grounded,
                "flagged_for_review": rule.flagged_for_review,
                "review_reason": rule.review_reason,
            }
        )

    return {
        "process_name": process_name,
        "condition_columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
