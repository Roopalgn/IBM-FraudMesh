"""Run: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000."""
from __future__ import annotations

import os
import platform
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from fraudmesh.demo import demo_request
from fraudmesh.graph_engine import AnalysisCapacityError
from fraudmesh.privacy import PrivacyContractError, validate_shared_signals
from fraudmesh.service import analyze_for_dashboard
from fraudmesh.analysis import analyze_signals
from fraudmesh.audit import record_analysis, verify_journal

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 128_000


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scenario_id: Literal["synthetic-common", "synthetic-ring", "synthetic-normal", "synthetic-local", "synthetic-custom"] = "synthetic-custom"
    shared_signals: list[dict] | None = Field(default=None, max_length=200)


app = FastAPI(title="FraudMesh synthetic prototype", version="0.1.0")
origins = [value.strip() for value in os.environ.get(
    "FRAUDMESH_ALLOWED_ORIGINS", "http://localhost:4173,http://127.0.0.1:4173").split(",") if value.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    if request.method == "POST":
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request exceeds the demo size limit"})
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Default validation errors can echo rejected raw values. Do not return them.
    return JSONResponse(status_code=422, content={"detail": "Invalid analysis request; use only the documented shared-signal schema"})


@app.get("/health")
def health():
    return {"status": "ok", "application": "FraudMesh", "service": "fraudmesh-computed-analysis", "synthetic_only": True,
            "architecture": platform.machine(), "python": platform.python_version(),
            "confidential_execution_verified": False}


@app.get("/demo/scenario")
def scenario(name: Annotated[Literal["common", "ring", "normal", "local"], Query()] = "common",
             profile: Annotated[Literal["person3.graph.v2", "dashboard.v1"], Query()] = "person3.graph.v2"):
    request = {"scenario_id": f"synthetic-{name}"} if profile == "person3.graph.v2" else demo_request(name)
    return {"response_profile": profile, "scenario_id": f"synthetic-{name}", "synthetic": True,
            "analysis_request": request}


def audit_path():
    return Path(os.environ.get("FRAUDMESH_AUDIT_PATH", str(ROOT / "output" / "analysis-audit.sqlite3")))


@app.get("/audit/status")
def audit_status():
    try:
        return verify_journal(audit_path())
    except (OSError, sqlite3.Error):
        raise HTTPException(503, "Local analysis journal is unavailable") from None


@app.post("/analyze")
def analyze(payload: AnalysisRequest):
    start = perf_counter()
    signals = payload.shared_signals
    if signals is None:
        if payload.scenario_id not in {"synthetic-common", "synthetic-ring", "synthetic-normal", "synthetic-local"}:
            raise HTTPException(422, "A scenario-reference request must identify a supported synthetic scenario")
        signals = demo_request(payload.scenario_id.removeprefix("synthetic-"))["shared_signals"]
    try:
        if signals:
            validate_shared_signals(signals)
        nodes = {signal[field] for signal in signals
                 for field in ("source_entity_token", "destination_entity_token")}
        if len(nodes) > 60:
            raise HTTPException(413, "The demo supports at most 60 pseudonymous entities")
        result = analyze_signals(signals) if payload.shared_signals is None else analyze_for_dashboard(signals, payload.scenario_id)
    except PrivacyContractError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisCapacityError as exc:
        raise HTTPException(413, str(exc)) from exc
    result["measurement"] = {"analysis_ms": round((perf_counter()-start)*1000, 3),
                             "scope": "Scenario-reference requests include bank-local ML/preparation; signal requests exclude it. Both exclude HTTP transport, journal write, and rendering."}
    try:
        result["audit"] = record_analysis(audit_path(), signals, result, payload.scenario_id)
    except (OSError, sqlite3.Error):
        raise HTTPException(503, "Analysis journal could not be recorded; no success response returned") from None
    return result


# Serve only public frontend assets. Raw data, source modules and .git are not mounted.
app.mount("/src", StaticFiles(directory=ROOT / "frontend" / "src"), name="frontend-src")
app.mount("/public", StaticFiles(directory=ROOT / "frontend" / "public"), name="frontend-public")


@app.get("/styles.css", include_in_schema=False)
def styles():
    from fastapi.responses import FileResponse
    return FileResponse(ROOT / "frontend" / "styles.css", media_type="text/css")


@app.get("/", include_in_schema=False)
def dashboard():
    from fastapi.responses import FileResponse
    return FileResponse(ROOT / "frontend" / "index.html")
