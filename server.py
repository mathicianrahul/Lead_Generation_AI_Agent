"""
LeadPilot AI — FastAPI Backend Server
Replaces Streamlit with a proper REST API + SSE for the custom HTML frontend.
"""
import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Bootstrap path so local modules resolve correctly
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import settings
from config.logging_config import logger
from database.connection import init_db, get_db_session, SessionLocal
from database.models import Lead, LeadEmail, EmailDraft, SearchJob, VerificationResult
from database.repository import LeadRepository
from services.export_service import ExportService
from services.google_maps_scraper import google_maps_scraper
from graph.workflow import run_lead_workflow

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LeadPilot AI",
    description="AI Multi-Agent Lead Generation & Website Sales Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

@app.on_event("startup")
async def startup():
    init_db()

# ---------------------------------------------------------------------------
# In-memory job tracker for SSE progress
# ---------------------------------------------------------------------------
_jobs: Dict[str, Dict] = {}   # job_id -> {status, progress, logs, result}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str
    location: str
    radius_km: int = 10
    max_results: int = 20
    provider: str = "auto"

class LeadUpdateRequest(BaseModel):
    crm_status: Optional[str] = None
    notes: Optional[str] = None
    deal_value: Optional[float] = None

class DraftUpdateRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class SuppressRequest(BaseModel):
    email: str
    reason: str = "manual"

class GoogleMapsSearchRequest(BaseModel):
    query: str
    location: str
    max_results: int = 20
    headless: bool = False

# ---------------------------------------------------------------------------
# Root — serve index.html
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"status": "LeadPilot AI API running", "frontend": "not built yet"})

# Serve the entire frontend folder as static at /app
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "version": "1.0.0",
        "google_places_configured": bool(settings.google_maps_api_key),
    }

# ---------------------------------------------------------------------------
# Settings / config status
# ---------------------------------------------------------------------------
@app.get("/api/settings")
async def get_settings():
    return {
        "demo_mode": settings.demo_mode,
        "discovery_provider": settings.discovery_provider,
        "overpass_api_url": settings.overpass_api_url,
        "google_places_api": "configured" if settings.google_maps_api_key else "missing",
        "openai_api": "configured" if settings.openai_api_key else "missing",
        "huggingface_api": "configured" if settings.huggingface_api_token else "missing",
        "gmail_configured": settings.has_gmail_config(),
        "scoring_weights": {
            "website_opportunity": settings.scoring_weights.website_opportunity,
            "phone_available": settings.scoring_weights.phone_available,
            "email_available": settings.scoring_weights.email_available,
            "active_operations": settings.scoring_weights.active_operations,
            "category_website_value": settings.scoring_weights.category_website_value,
        },
        "daily_email_cap": settings.max_daily_emails,
        "max_search_results": settings.max_search_results,
    }

# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------
@app.get("/api/metrics")
async def get_metrics():
    repo = LeadRepository()
    try:
        metrics = repo.get_dashboard_metrics()
        return metrics
    except Exception as e:
        # Return safe defaults if DB is empty
        return {
            "total_leads": 0,
            "verified_leads": 0,
            "high_score_leads": 0,
            "emails_sent": 0,
            "avg_score": 0,
            "recent_jobs": [],
        }

# ---------------------------------------------------------------------------
# Leads CRUD
# ---------------------------------------------------------------------------
@app.get("/api/leads")
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str = Query("", alias="q"),
    crm_status: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    has_website: Optional[bool] = None,
    sort_by: str = "score",
    sort_dir: str = "desc",
):
    repo = LeadRepository()
    try:
        leads, total = repo.filter_leads(
            page=page,
            per_page=per_page,
            search=search,
            crm_status=crm_status,
            min_score=min_score,
            has_website=has_website,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return {
            "leads": leads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        }
    except Exception as e:
        return {"leads": [], "total": 0, "page": 1, "per_page": per_page, "pages": 1}


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int):
    repo = LeadRepository()
    lead = repo.get_lead_dict(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: int, body: LeadUpdateRequest):
    repo = LeadRepository()
    updated = repo.update_lead(
        lead_id=lead_id,
        crm_status=body.crm_status,
        notes=body.notes,
        deal_value=body.deal_value,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "lead_id": lead_id}


@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int):
    repo = LeadRepository()
    ok = repo.delete_lead(lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True}

# ---------------------------------------------------------------------------
# Search / Lead discovery — SSE streaming
# ---------------------------------------------------------------------------
@app.post("/api/search")
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_run_search_job, job_id, req)
    return {"job_id": job_id}


async def _run_search_job(job_id: str, req: SearchRequest):
    """Run the full lead workflow in a background task."""
    job = _jobs[job_id]
    job["status"] = "running"
    job["logs"].append("🚀 Starting LeadPilot AI workflow...")

    def progress_cb(step_name: str, pct: int, msg: str):
        job["progress"] = pct
        job["logs"].append(msg)

    try:
        search_params = {
            "category": req.query,
            "city": req.location,
            "area": "",
            "country": "India",
            "max_results": req.max_results,
            "min_score": 50.0,
            "budget_limit": 50,
            "provider": req.provider or "auto",
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_lead_workflow(search_params, progress_callback=progress_cb),
        )

        job["progress"] = 100
        job["status"] = "done"
        leads_count = len(result.get("persisted_leads", [])) or len(result.get("qualified_leads", []))
        job["logs"].append(f"✅ Pipeline complete! {leads_count} leads processed.")
        job["result"] = {"leads_saved": leads_count}
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        job["logs"].append(f"❌ Error: {exc}")


@app.get("/api/search/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE endpoint — stream job progress to the browser."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        sent_log_idx = 0
        while True:
            job = _jobs.get(job_id, {})
            new_logs = job.get("logs", [])[sent_log_idx:]
            for log in new_logs:
                yield f"data: {json.dumps({'type': 'log', 'message': log, 'progress': job.get('progress', 0)})}\n\n"
            sent_log_idx += len(new_logs)

            if job.get("status") in ("done", "error"):
                payload = {
                    "type": "done",
                    "status": job["status"],
                    "result": job.get("result"),
                    "error": job.get("error"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/search/{job_id}/status")
async def job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ---------------------------------------------------------------------------
# Google Maps Browser Scraper — SSE streaming
# ---------------------------------------------------------------------------
@app.post("/api/scrape/google-maps")
async def start_gmaps_scrape(req: GoogleMapsSearchRequest, background_tasks: BackgroundTasks):
    """Launch a Google Maps browser scraping job (opens Chrome to find leads)."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_run_gmaps_scrape_job, job_id, req)
    return {"job_id": job_id}


async def _run_gmaps_scrape_job(job_id: str, req: GoogleMapsSearchRequest):
    """Run the Google Maps Playwright scraper in a background task."""
    job = _jobs[job_id]
    job["status"] = "running"
    job["logs"].append("Starting Google Maps browser automation...")

    def progress_cb(step_name: str, pct: int, msg: str):
        job["progress"] = pct
        job["logs"].append(msg)

    try:
        leads, error = await google_maps_scraper.scrape_leads(
            query=req.query,
            location=req.location,
            max_results=req.max_results,
            headless=req.headless,
            progress_callback=progress_cb,
        )

        if error and not leads:
            job["status"] = "error"
            job["error"] = error
            job["logs"].append(f"Scraping failed: {error}")
            return

        # Persist scraped leads to database
        if leads:
            job["logs"].append(f"Saving {len(leads)} leads to database...")
            db = SessionLocal()
            try:
                repo = LeadRepository(db)
                saved_count = 0
                for lead_data in leads:
                    try:
                        lead_obj, is_new, action = repo.create_or_merge_lead(lead_data)
                        # Record verification
                        repo.record_verification(
                            lead_id=lead_obj.id,
                            method="GOOGLE_MAPS_BROWSER_SCRAPE",
                            status=lead_obj.website_status,
                            evidence="Extracted via Google Maps browser automation",
                            source="Google Maps (Browser)",
                            confidence=lead_obj.verification_confidence or 0.5,
                            candidate_url=lead_obj.website_url,
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.warning("Failed to save lead '%s': %s",
                                       lead_data.get("business_name", "?"), str(e))
            finally:
                db.close()
            job["logs"].append(f"Saved {saved_count} leads to database!")
        else:
            saved_count = 0

        job["progress"] = 100
        job["status"] = "done"
        job["logs"].append(
            f"Google Maps scraping complete! {len(leads)} businesses found, {saved_count} saved."
        )
        job["result"] = {
            "leads_found": len(leads),
            "leads_saved": saved_count,
            "source": "Google Maps (Browser)",
        }

        if error:
            job["logs"].append(f"Note: {error}")

    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        job["logs"].append(f"Scraper error: {exc}")
        logger.error("Scraper job %s failed: %s", job_id, exc, exc_info=True)


@app.get("/api/scrape/{job_id}/stream")
async def stream_scrape_job(job_id: str):
    """SSE endpoint — stream scrape job progress to the browser."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        sent_log_idx = 0
        while True:
            job = _jobs.get(job_id, {})
            new_logs = job.get("logs", [])[sent_log_idx:]
            for log in new_logs:
                yield f"data: {json.dumps({'type': 'log', 'message': log, 'progress': job.get('progress', 0)})}\n\n"
            sent_log_idx += len(new_logs)

            if job.get("status") in ("done", "error"):
                payload = {
                    "type": "done",
                    "status": job["status"],
                    "result": job.get("result"),
                    "error": job.get("error"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Email Drafts
# ---------------------------------------------------------------------------
@app.get("/api/drafts")
async def list_drafts(status: Optional[str] = None):
    repo = LeadRepository()
    try:
        drafts = repo.get_email_drafts(status=status)
        return {"drafts": drafts}
    except Exception:
        return {"drafts": []}


@app.get("/api/drafts/{draft_id}")
async def get_draft(draft_id: int):
    repo = LeadRepository()
    draft = repo.get_draft_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.put("/api/drafts/{draft_id}")
async def update_draft(draft_id: int, body: DraftUpdateRequest):
    repo = LeadRepository()
    ok = repo.update_draft(draft_id, subject=body.subject, body=body.body)
    if not ok:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True}


@app.post("/api/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int):
    repo = LeadRepository()
    ok = repo.set_draft_status(draft_id, "approved")
    if not ok:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "status": "approved"}


@app.post("/api/drafts/{draft_id}/reject")
async def reject_draft(draft_id: int):
    repo = LeadRepository()
    ok = repo.set_draft_status(draft_id, "rejected")
    if not ok:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "status": "rejected"}

# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------
@app.post("/api/suppress")
async def suppress_email(body: SuppressRequest):
    repo = LeadRepository()
    repo.add_to_suppression(body.email, body.reason)
    return {"success": True}

# ---------------------------------------------------------------------------
# Charts data
# ---------------------------------------------------------------------------
@app.get("/api/charts/website-status")
async def chart_website_status():
    repo = LeadRepository()
    try:
        data = repo.get_website_status_counts()
        return data
    except Exception:
        return {"has_website": 0, "no_website": 0, "unknown": 0}


@app.get("/api/charts/score-distribution")
async def chart_score_distribution():
    repo = LeadRepository()
    try:
        return repo.get_score_distribution()
    except Exception:
        return {"buckets": [], "counts": []}


@app.get("/api/charts/crm-pipeline")
async def chart_crm_pipeline():
    repo = LeadRepository()
    try:
        return repo.get_crm_pipeline_counts()
    except Exception:
        return {"new": 0, "contacted": 0, "qualified": 0, "proposal": 0, "closed": 0}

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@app.get("/api/export/excel")
async def export_excel():
    svc = ExportService()
    repo = LeadRepository()
    try:
        leads, _ = repo.filter_leads(page=1, per_page=10000)
        path = svc.export_to_excel(leads)
        return FileResponse(
            path=path,
            filename="leadpilot_export.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/csv")
async def export_csv():
    svc = ExportService()
    repo = LeadRepository()
    try:
        leads, _ = repo.filter_leads(page=1, per_page=10000)
        path = svc.export_to_csv(leads)
        return FileResponse(
            path=path,
            filename="leadpilot_export.csv",
            media_type="text/csv",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Recent jobs
# ---------------------------------------------------------------------------
@app.get("/api/jobs")
async def list_jobs():
    repo = LeadRepository()
    try:
        jobs = repo.get_recent_jobs(limit=20)
        return {"jobs": jobs}
    except Exception:
        return {"jobs": []}
