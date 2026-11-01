import time
import datetime
from typing import Dict, Any

from graph.state import LeadPilotState
from agents.search_planning_agent import search_planning_agent, SearchPlanInput
from agents.business_discovery_agent import business_discovery_agent
from agents.data_quality_agent import data_quality_agent
from agents.website_verification_agent import website_verification_agent
from agents.business_enrichment_agent import business_enrichment_agent
from agents.lead_scoring_agent import lead_scoring_agent
from agents.excel_report_agent import excel_report_agent
from agents.outreach_personalization_agent import outreach_personalization_agent
from database.connection import SessionLocal
from database.repository import LeadRepository
from services.export_service import export_service
from config.logging_config import logger


def plan_search_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing plan_search_node")
    s_in = state["search_input"]
    plan_obj = SearchPlanInput(**s_in)
    plan_out = search_planning_agent.run(plan_obj)

    # Persist search job in DB
    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        repo.create_search_job(plan_out.job_id, plan_out.normalized_params, plan_out.estimated_api_calls)
    finally:
        db.close()

    state["job_id"] = plan_out.job_id
    state["execution_plan"] = plan_out.model_dump()
    state["current_step"] = "Search Planning Completed"
    state["step_timings"]["planning"] = round(time.time() - t0, 2)
    return state


def discover_businesses_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing discover_businesses_node")
    if state.get("is_cancelled"):
        state["status"] = "CANCELLED"
        return state

    plan = state["execution_plan"]
    queries = plan.get("queries", [])
    norm_params = plan.get("normalized_params", {})
    max_res = norm_params.get("max_results", 20)
    country = norm_params.get("country", "India")
    city = norm_params.get("city", "")
    area = norm_params.get("area", "")
    provider = norm_params.get("provider", "auto")

    records, calls, errors = business_discovery_agent.run(
        queries=queries,
        max_results=max_res,
        country=country,
        provider=provider,
        city=city,
        area=area
    )

    state["discovered_records"] = records
    state["api_calls_made"] += calls
    if errors:
        state["errors"].extend(errors)

    state["current_step"] = f"Discovered {len(records)} businesses"
    state["step_timings"]["discovery"] = round(time.time() - t0, 2)
    return state


def deduplicate_and_clean_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing deduplicate_and_clean_node")
    if state.get("is_cancelled"):
        state["status"] = "CANCELLED"
        return state

    raw_records = state.get("discovered_records", [])

    # Load existing leads for deduplication
    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        existing = repo.list_all_leads_dict()
    finally:
        db.close()

    unique_recs, dup_count, conflicts = data_quality_agent.run(raw_records, existing)

    state["deduplicated_records"] = unique_recs
    state["current_step"] = f"Deduplicated ({len(unique_recs)} unique, {dup_count} duplicates)"
    state["step_timings"]["deduplication"] = round(time.time() - t0, 2)
    return state


def verify_websites_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing verify_websites_node")
    if state.get("is_cancelled"):
        state["status"] = "CANCELLED"
        return state

    records = state.get("deduplicated_records", [])
    verified = website_verification_agent.run(records)

    state["verified_records"] = verified
    state["current_step"] = f"Verified {len(verified)} websites"
    state["step_timings"]["verification"] = round(time.time() - t0, 2)
    return state


def enrich_leads_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing enrich_leads_node")
    if state.get("is_cancelled"):
        state["status"] = "CANCELLED"
        return state

    records = state.get("verified_records", [])
    enriched = business_enrichment_agent.run(records)

    state["enriched_records"] = enriched
    state["current_step"] = f"Enriched {len(enriched)} leads"
    state["step_timings"]["enrichment"] = round(time.time() - t0, 2)
    return state


def score_leads_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing score_leads_node")
    if state.get("is_cancelled"):
        state["status"] = "CANCELLED"
        return state

    records = state.get("enriched_records", [])
    min_score = state.get("search_input", {}).get("min_score", 0.0)

    qualified, all_scored = lead_scoring_agent.run(
        records=records,
        min_score=min_score,
        exclude_existing_websites=False
    )

    state["qualified_leads"] = qualified
    state["all_scored_records"] = all_scored
    state["current_step"] = f"Scored leads ({len(qualified)} qualified >= {min_score})"
    state["step_timings"]["scoring"] = round(time.time() - t0, 2)
    return state


def persist_results_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing persist_results_node")
    records = state.get("all_scored_records", [])
    persisted = []

    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        for r in records:
            lead_obj, is_new, action = repo.create_or_merge_lead(r)
            # Record verification history
            repo.record_verification(
                lead_id=lead_obj.id,
                method="HTTP_AND_PLACES_VERIFICATION",
                status=lead_obj.website_status,
                evidence=r.get("verification_evidence", "Initial discovery verification"),
                source=r.get("source", "Places API"),
                confidence=lead_obj.verification_confidence,
                candidate_url=lead_obj.website_url
            )
            r_dict = dict(r)
            r_dict["id"] = lead_obj.id
            persisted.append(r_dict)

        # Update search job in DB
        repo.complete_search_job(
            job_id=state["job_id"],
            status="COMPLETED",
            discovered=len(state.get("discovered_records", [])),
            unique=len(persisted),
            errors=len(state.get("errors", [])),
            actual_api=state.get("api_calls_made", 0),
            summary=f"Persisted {len(persisted)} leads"
        )
    finally:
        db.close()

    state["persisted_leads"] = persisted
    state["current_step"] = f"Persisted {len(persisted)} leads in database"
    state["step_timings"]["persistence"] = round(time.time() - t0, 2)
    return state


def generate_reports_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing generate_reports_node")
    leads = state.get("persisted_leads", [])
    plan = state.get("execution_plan", {})
    norm_params = plan.get("normalized_params", {})
    prefix = f"leadpilot_{norm_params.get('city', 'leads')}_{norm_params.get('category', 'all')}"

    search_summary = {
        "job_id": state["job_id"],
        "location": f"{norm_params.get('area', '')} {norm_params.get('city', '')}, {norm_params.get('country', '')}".strip(),
        "category": norm_params.get("category", ""),
        "queries": ", ".join(plan.get("queries", [])),
        "actual_api_usage": state.get("api_calls_made", 0)
    }

    excel_path = excel_report_agent.run(
        leads=leads,
        search_summary=search_summary,
        filename_prefix=prefix
    )

    csv_path = export_service.export_to_csv(leads, filename_prefix=prefix)

    state["excel_report_path"] = excel_path
    state["csv_report_path"] = csv_path
    state["current_step"] = "Excel and CSV Reports Generated"
    state["step_timings"]["reporting"] = round(time.time() - t0, 2)
    return state


def generate_drafts_node(state: LeadPilotState) -> LeadPilotState:
    t0 = time.time()
    logger.info("Executing generate_drafts_node")
    # Only generate drafts for qualified prospects without confirmed website
    leads = state.get("persisted_leads", [])
    target_prospects = [
        l for l in leads if l.get("website_status") not in ("WEBSITE_FOUND", "WEBSITE_FOUND_ACCESSIBLE")
    ]

    drafts = outreach_personalization_agent.run(target_prospects)

    # Persist drafts in database
    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        for d in drafts:
            if d.get("has_email") and d.get("lead_id"):
                repo.create_or_update_draft(
                    lead_id=d["lead_id"],
                    recipient_email=d["recipient_email"],
                    subject=d["subject"],
                    body=d["body"],
                    personalization_evidence=d["personalization_evidence"]
                )
    finally:
        db.close()

    state["email_drafts"] = drafts
    state["status"] = "COMPLETED"
    state["current_step"] = f"Workflow Completed ({len(drafts)} outreach drafts ready)"
    state["step_timings"]["drafting"] = round(time.time() - t0, 2)
    return state

