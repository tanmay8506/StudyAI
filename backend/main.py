"""
backend/main.py
────────────────
FastAPI entry point for StudyAI.

Endpoints:
  POST /generate          — triggers the full 12-agent pipeline as a background task
  GET  /status/{upc}      — returns current pipeline_status + per-unit statuses
  POST /generate/rerun    — force-reruns the pipeline from a specific agent

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import silence_warnings  # noqa: F401 — must be first import
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from database import queries as q
from pipeline.orchestrator import run_pipeline
from utils.rate_limiter import patch_gemini_sdk

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("studyai.main")


# ─────────────────────────────────────────────────────────────────────────────
# Startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("StudyAI backend starting")
    patch_gemini_sdk()
    yield
    log.info("StudyAI backend shutting down")


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="StudyAI",
    description="12-agent pipeline for DU B.Sc. NEP/UGCF 2022 exam notes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    upc: str = Field(..., description="University Paper Code — e.g. BSCMT201")


class RerunRequest(BaseModel):
    upc: str
    from_agent: int = Field(
        ..., ge=1, le=12,
        description="Re-run the pipeline from this agent number (clears downstream data)"
    )


class UnitStatus(BaseModel):
    unit_id: str
    unit_number: int
    unit_name: str
    status: str


class PipelineStatus(BaseModel):
    upc: str
    pipeline_status: str
    units: list[UnitStatus]


# ─────────────────────────────────────────────────────────────────────────────
# In-memory guard: prevent duplicate pipeline runs for the same UPC
# ─────────────────────────────────────────────────────────────────────────────

_active_runs: set[str] = set()


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/generate", status_code=202)
async def generate(request: GenerateRequest,
                   background_tasks: BackgroundTasks) -> dict:
    """
    Kick off the 12-agent pipeline for a UPC.
    Returns immediately (202 Accepted).  Frontend polls /status/{upc} or uses
    Supabase Realtime on the `units` table for live progress.
    """
    upc = request.upc.strip().upper()

    # Guard: reject if already running
    if upc in _active_runs:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for {upc}. Poll /status/{upc} for progress.",
        )

    # Guard: reject unknown UPC early (before backgrounding)
    paper = q.get_paper(upc)
    if paper is None:
        # Decoder will attempt registry lookup — only reject if registry is confirmed empty
        # Let the pipeline handle it so the decoder error message is surfaced properly.
        pass

    _active_runs.add(upc)

    async def _run_and_cleanup():
        try:
            import asyncio
            
            log.info("MOCK PIPELINE: Running simulation for %s to test frontend animations", upc)
            
            # Create a mock paper
            q.upsert_paper(upc, {"paper_name": "Telemetry Simulation Paper", "pipeline_status": "generating"})
            
            # Create 4 mock units
            units = []
            for i in range(1, 5):
                u = q.create_unit(upc, i, f"Simulated Study Unit {i}")
                units.append(u)
                
            # Simulate the pipeline agents working on the units
            for u in units:
                q.set_unit_status(u["id"], "generating")
                await asyncio.sleep(5) # 5 second delay per unit for dramatic effect
                q.set_unit_status(u["id"], "complete")
                
            q.set_paper_status(upc, "complete")
            log.info("MOCK PIPELINE: Simulation complete for %s", upc)
            
        finally:
            _active_runs.discard(upc)

    background_tasks.add_task(_run_and_cleanup)

    log.info("Pipeline queued for %s", upc)
    return {"upc": upc, "status": "queued", "message": "Pipeline started."}


@app.get("/status/{upc}", response_model=PipelineStatus)
async def get_status(upc: str) -> PipelineStatus:
    """
    Returns current pipeline and unit statuses.
    Frontend can poll this on reconnect as a fallback to Supabase Realtime.
    """
    upc = upc.strip().upper()
    paper = q.get_paper(upc)
    if not paper:
        raise HTTPException(status_code=404, detail=f"UPC {upc} not found.")

    units = q.get_units_for_paper(upc)
    return PipelineStatus(
        upc=upc,
        pipeline_status=paper.get("pipeline_status", "unknown"),
        units=[
            UnitStatus(
                unit_id=u["id"],
                unit_number=u["unit_number"],
                unit_name=u["unit_name"],
                status=u.get("status", "unknown"),
            )
            for u in units
        ],
    )


@app.post("/generate/rerun", status_code=202)
async def force_rerun(request: RerunRequest,
                      background_tasks: BackgroundTasks) -> dict:
    """
    Force re-runs the pipeline from a specific agent number.
    Clears all data produced by that agent and downstream agents, then re-runs.

    Useful for prompt tuning: change writer_invariant.txt, then call
    POST /generate/rerun  {"upc": "BSCMT201", "from_agent": 5}
    to wipe all topic content and regenerate.
    """
    upc = request.upc.strip().upper()

    if upc in _active_runs:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for {upc}.",
        )

    paper = q.get_paper(upc)
    if not paper:
        raise HTTPException(status_code=404, detail=f"UPC {upc} not found.")

    _active_runs.add(upc)

    async def _run_and_cleanup():
        try:
            await run_pipeline(upc, force_rerun_from=request.from_agent)
        finally:
            _active_runs.discard(upc)

    background_tasks.add_task(_run_and_cleanup)

    log.info("Force rerun from agent %d queued for %s", request.from_agent, upc)
    return {
        "upc": upc,
        "from_agent": request.from_agent,
        "status": "queued",
        "message": f"Pipeline re-running from agent {request.from_agent}.",
    }


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to the StudyAI Academic Brutalism Backend API Server.",
        "status": "healthy",
        "frontend_url": "http://localhost:3000",
        "documentation": "This server runs a 12-agent pipeline to generate structured exam notes.",
        "endpoints": {
            "POST /generate": "Triggers the pipeline for a given UPC.",
            "GET /status/{upc}": "Retrieves the live pipeline and unit generation status.",
            "POST /generate/rerun": "Force-reruns the pipeline from a specific agent.",
            "GET /health": "Simple health check endpoint."
        }
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}