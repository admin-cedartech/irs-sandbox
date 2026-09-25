"""Generate deliverable artifact files from the extracted business rules.

Writes to ./output/:
  - decedent_refund_rules.json          (business rules JSON)
  - decedent_refund_process.bpmn        (BPMN 2.0 XML for Pega)
  - decedent_refund_decision_table.json (decision-table JSON for Pega)

Uses whatever LLM_PROVIDER is configured in .env (mock by default, so it runs
with no AWS). Run:  python generate_artifacts.py
"""
import json
import os

from app.bpmn import rules_to_bpmn
from app.decision_table import rules_to_decision_table
from app.guardrails import apply_guardrails
from app.llm import get_provider
from app.sample_irm import SAMPLE_DECEDENT_REFUND_TEXT

PROCESS = "Processing Decedent Account Refunds"
OUT = "output"
os.makedirs(OUT, exist_ok=True)

provider = get_provider()
raw = provider.extract(SAMPLE_DECEDENT_REFUND_TEXT, "21.6.6.2.21")
rules, meta = apply_guardrails(raw, SAMPLE_DECEDENT_REFUND_TEXT, provider.name, provider.model_id)

with open(os.path.join(OUT, "decedent_refund_rules.json"), "w", encoding="utf-8") as f:
    json.dump(
        {"process_name": PROCESS, "rules": [r.model_dump() for r in rules], "metadata": meta.model_dump()},
        f,
        indent=2,
    )

with open(os.path.join(OUT, "decedent_refund_process.bpmn"), "w", encoding="utf-8") as f:
    f.write(rules_to_bpmn(PROCESS, rules))

with open(os.path.join(OUT, "decedent_refund_decision_table.json"), "w", encoding="utf-8") as f:
    json.dump(rules_to_decision_table(PROCESS, rules), f, indent=2)

print(f"Provider: {provider.name}  Rules: {len(rules)}")
print("Wrote output/decedent_refund_rules.json, .bpmn, _decision_table.json")
