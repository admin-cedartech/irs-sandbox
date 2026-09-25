"""FastAPI service: IRM -> business rules (JSON) -> BPMN 2.0 (XML) for Pega."""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response

from .bpmn import rules_to_bpmn
from .config import settings
from .decision_table import rules_to_decision_table
from .guardrails import apply_guardrails
from .llm import LLMError, get_provider
from .pdf_ingest import prepare_source_text
from .sample_irm import SAMPLE_DECEDENT_REFUND_TEXT
from .schemas import ExtractRulesResponse, GenerateBpmnRequest

app = FastAPI(
    title="IRM Business Rule Extraction Agent",
    description=(
        "Analyzes an IRS Internal Revenue Manual (IRM) procedure and extracts "
        "business rules for Processing Decedent Account Refunds (Form 1310 in "
        "response to CP 01H / Letter 12C). Outputs JSON and BPMN 2.0 for Pega."
    ),
    version="0.1.0",
)


@app.get("/")
def root() -> RedirectResponse:
    """Send the base URL to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "bedrock_guardrails": bool(settings.bedrock_guardrail_id),
    }


def _run_extraction(source_text: str, section_hint: str) -> ExtractRulesResponse:
    provider = get_provider()
    try:
        raw = provider.extract(source_text, section_hint)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rules, metadata = apply_guardrails(
        raw, source_text, provider.name, provider.model_id
    )
    return ExtractRulesResponse(rules=rules, metadata=metadata)


@app.post("/extract-rules", response_model=ExtractRulesResponse)
async def extract_rules(
    file: UploadFile | None = File(default=None, description="IRM PDF to analyze."),
    section: str = Form(default="21.6.6.2.21", description="IRM section to target."),
) -> ExtractRulesResponse:
    """Upload an IRM PDF and get validated, grounded business rules as JSON.

    If no file is provided, the built-in sample decedent-refund text is used so
    the endpoint is demoable without an upload.
    """
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        try:
            source_text = prepare_source_text(data, section)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc
    else:
        source_text = SAMPLE_DECEDENT_REFUND_TEXT

    return _run_extraction(source_text, section)


@app.post("/extract-rules/sample", response_model=ExtractRulesResponse)
def extract_rules_sample() -> ExtractRulesResponse:
    """Run extraction against the built-in sample text (no upload)."""
    return _run_extraction(SAMPLE_DECEDENT_REFUND_TEXT, "21.6.6.2.21")


@app.post("/generate-bpmn")
def generate_bpmn(req: GenerateBpmnRequest) -> Response:
    """Turn a set of business rules into BPMN 2.0 XML for Pega import.

    Note: send REAL rules here (e.g. the `rules` array returned by
    /extract-rules). If you submit the Swagger example body unchanged, you will
    get BPMN full of placeholder "string" values. For a one-step demo, use
    /extract-bpmn instead.
    """
    xml = rules_to_bpmn(req.process_name, req.rules)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="decedent_refund_process.bpmn"'},
    )


@app.post("/generate-decision-table")
def generate_decision_table(req: GenerateBpmnRequest) -> dict:
    """Turn a set of business rules into a decision-table JSON for Pega.

    Send REAL rules (e.g. the `rules` array from /extract-rules). For a one-step
    demo, use /extract-decision-table instead.
    """
    return rules_to_decision_table(req.process_name, req.rules)


@app.post("/extract-bpmn")
async def extract_bpmn(
    file: UploadFile | None = File(default=None, description="IRM PDF to analyze."),
    section: str = Form(default="21.6.6.2.21", description="IRM section to target."),
) -> Response:
    """One-shot: extract rules from the IRM and return BPMN 2.0 XML directly.

    Upload the IRM PDF (or omit the file to use the built-in sample). This runs
    extraction + guardrails + BPMN generation in a single call, so the BPMN
    always contains the real extracted rules.
    """
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        try:
            source_text = prepare_source_text(data, section)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc
    else:
        source_text = SAMPLE_DECEDENT_REFUND_TEXT

    result = _run_extraction(source_text, section)
    xml = rules_to_bpmn(result.process_name, result.rules)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="decedent_refund_process.bpmn"'},
    )


@app.post("/extract-decision-table")
async def extract_decision_table(
    file: UploadFile | None = File(default=None, description="IRM PDF to analyze."),
    section: str = Form(default="21.6.6.2.21", description="IRM section to target."),
) -> dict:
    """One-shot: extract rules from the IRM and return a decision-table JSON.

    Upload the IRM PDF (or omit the file to use the built-in sample). Runs
    extraction + guardrails + decision-table generation in a single call.
    """
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        try:
            source_text = prepare_source_text(data, section)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc
    else:
        source_text = SAMPLE_DECEDENT_REFUND_TEXT

    result = _run_extraction(source_text, section)
    return rules_to_decision_table(result.process_name, result.rules)
