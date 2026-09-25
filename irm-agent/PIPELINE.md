# IRM Business Rule Extraction Agent — Pipeline

## The flow

```
   ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
   │   IRM PDF   │ ──► │ Extract text │ ──► │  LLM reads it   │ ──► │  GUARDRAILS  │
   │  (uploaded) │     │   (pypdf)    │     │ (Claude/Bedrock)│     │ verify rules │
   └─────────────┘     └──────────────┘     └─────────────────┘     └──────┬───────┘
                                                                           │
                                        ┌──────────────────────────────────┘
                                        ▼
                              ┌───────────────────┐
                              │  Business Rules   │
                              └─────────┬─────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                       ▼
          ┌────────────┐         ┌────────────┐         ┌──────────────────┐
          │    JSON    │         │  BPMN 2.0  │         │  Decision Table  │
          │  (rules)   │         │ (for Pega) │         │   (for Pega)     │
          └────────────┘         └────────────┘         └──────────────────┘
```

## The guardrails (why the output is trustworthy)

```
   LLM proposes rules
          │
          ▼
   ┌──────────────────────────────────────────────┐
   │  1. Schema check    — must fit exact structure │
   │  2. Source grounding — quote must exist in IRM │
   │  3. Confidence score — low ones get flagged    │
   │  4. Human review     — for anything flagged    │
   └──────────────────────────────────────────────┘
          │
          ▼
   Only verified rules pass  →  nothing invented survives
```

## One line

Dense IRS PDF in → LLM reads it under guardrails → trustworthy business rules
out as JSON, BPMN, and a decision table → Pega turns those into a workflow.
