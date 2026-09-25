# IRM Business Rule Extraction Agent

AI agent that analyzes an IRS Internal Revenue Manual (IRM) procedure and
extracts **business rules for workflow generation**. Built for Epic #4:
*Processing Decedent Account Refunds* — when the IRS receives a **Form 1310**
in response to a **CP 01H notice / Letter 12C**.

It outputs the rules as **JSON** and **BPMN 2.0 XML** that can be imported into
**Pega Blueprint**.

## Pipeline

```
IRM PDF ─► extract text ─► LLM extracts rules ─► guardrails ─► rules JSON ─┬─► JSON for Pega
             (pypdf)        (Bedrock/Claude)    (validate +               └─► BPMN 2.0 XML
                                                 ground + score)               for Pega
```

## Guardrails (anti-hallucination)

Public LLMs hallucinate, which is unacceptable for tax/legal content. Every
rule passes through layered controls:

1. **Constrained prompt** — the model is told to extract only, never invent, and
   to quote real source text.
2. **Schema validation** — output must fit the Pydantic `BusinessRule` shape or
   it is dropped.
3. **Source grounding** — each rule's `source_quote` must actually exist in the
   IRM text, or the rule is flagged as a possible hallucination.
4. **Confidence threshold** — low-confidence rules are flagged for human review.
5. **Amazon Bedrock Guardrails** (optional) — managed AWS content safety, applied
   at the model call when configured.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env         # then edit if needed
```

By default `LLM_PROVIDER=mock`, so it runs with **no AWS credentials** — good
for a public showcase. Set `LLM_PROVIDER=bedrock` (region `us-east-1`) to use
real Claude on Amazon Bedrock.

## Run

```bash
uvicorn app.main:app --reload
```

Open interactive docs at http://127.0.0.1:8000/docs

## Endpoints

| Method | Path                        | Purpose                                             |
|--------|-----------------------------|-----------------------------------------------------|
| GET    | `/health`                   | Service + provider status                           |
| POST   | `/extract-rules`            | Upload IRM PDF → business rules JSON (falls back to sample if no file) |
| POST   | `/extract-rules/sample`     | Run extraction on the built-in sample (no upload)   |
| POST   | `/extract-bpmn`             | One-shot: PDF/sample → BPMN 2.0 XML                  |
| POST   | `/extract-decision-table`   | One-shot: PDF/sample → decision-table JSON          |
| POST   | `/generate-bpmn`            | Business rules JSON → BPMN 2.0 XML                   |
| POST   | `/generate-decision-table`  | Business rules JSON → decision-table JSON           |

For a demo, the one-shot `/extract-*` endpoints are easiest (one click). The
`/generate-*` endpoints expect a real `rules` array in the body.

### Example: extract from a PDF

```bash
curl -X POST http://127.0.0.1:8000/extract-rules \
  -F "file=@21.6.6.pdf" -F "section=21.6.6.2.21"
```

### Example: rules → BPMN

Take the `rules` array from `/extract-rules` and POST it:

```bash
curl -X POST http://127.0.0.1:8000/generate-bpmn \
  -H "Content-Type: application/json" \
  -d '{"process_name":"Processing Decedent Account Refunds","rules":[ ... ]}' \
  -o decedent_refund_process.bpmn
```

## Notes

- The built-in sample text (`app/sample_irm.py`) is a condensed excerpt for the
  demo. In real use, upload the full IRM PDF and the agent extracts from it.
- BPMN follows the [BPMN 2.0 spec](https://www.bpmn.org/): rules map to exclusive
  gateways (conditions) + tasks (actions).
```
