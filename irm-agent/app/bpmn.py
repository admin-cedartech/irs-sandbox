"""Generate BPMN 2.0 XML from business rules for import into Pega Blueprint.

Each rule becomes: an exclusive gateway (the conditions) with a conditional
sequence flow to a task (the action). All rules branch from a single start
event; every task flows to a single end event. This produces a valid BPMN 2.0
process that Pega can import as a decision-driven workflow.

Spec reference: https://www.bpmn.org/
"""
from __future__ import annotations

from typing import List
from xml.sax.saxutils import escape

from .schemas import BusinessRule

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"


def _condition_expression(rule: BusinessRule) -> str:
    """Build a human-readable boolean expression from conditions (AND)."""
    parts = []
    for c in rule.conditions:
        val = c.value
        if isinstance(val, str):
            val_repr = f'"{val}"'
        else:
            val_repr = str(val)
        parts.append(f"{c.fact} {c.operator.value} {val_repr}")
    return " AND ".join(parts) if parts else "true"


def rules_to_bpmn(process_name: str, rules: List[BusinessRule]) -> str:
    process_id = "Process_DecedentRefund"
    start_id = "StartEvent_1"
    end_id = "EndEvent_1"

    elements: List[str] = []
    flows: List[str] = []

    elements.append(f'<startEvent id="{start_id}" name="Form 1310 received (CP 01H / Letter 12C)" />')

    prev = start_id
    for idx, rule in enumerate(rules, start=1):
        gw_id = f"Gateway_{idx}"
        task_id = f"Task_{idx}"
        expr = escape(_condition_expression(rule))
        name = escape(rule.name)
        action = escape(rule.action)

        elements.append(
            f'<exclusiveGateway id="{gw_id}" name="{name}?" />'
        )
        elements.append(
            f'<task id="{task_id}" name="{action}">'
            f"<documentation>{escape(rule.source_reference)}: {escape(rule.source_quote)}</documentation>"
            f"</task>"
        )

        # Flow from previous node into this gateway.
        flows.append(f'<sequenceFlow id="flow_{prev}_{gw_id}" sourceRef="{prev}" targetRef="{gw_id}" />')
        # Conditional flow gateway -> task (rule matched).
        flows.append(
            f'<sequenceFlow id="flow_{gw_id}_{task_id}" sourceRef="{gw_id}" targetRef="{task_id}" name="yes">'
            f'<conditionExpression xsi:type="tFormalExpression">{expr}</conditionExpression>'
            f"</sequenceFlow>"
        )
        # Task -> end.
        flows.append(f'<sequenceFlow id="flow_{task_id}_{end_id}" sourceRef="{task_id}" targetRef="{end_id}" />')

        prev = gw_id

    # If no rules, connect start straight to end so the XML is still valid.
    if not rules:
        flows.append(f'<sequenceFlow id="flow_empty" sourceRef="{start_id}" targetRef="{end_id}" />')

    elements.append(f'<endEvent id="{end_id}" name="Refund processed" />')

    body = "\n    ".join(elements + flows)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<definitions xmlns="{BPMN_NS}" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'id="Definitions_1" targetNamespace="http://irs.gov/irm/21.6.6">\n'
        f'  <process id="{process_id}" name="{escape(process_name)}" isExecutable="false">\n'
        f"    {body}\n"
        "  </process>\n"
        "</definitions>\n"
    )
