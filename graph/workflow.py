import time
from typing import Dict, Any, Callable, Optional
from langgraph.graph import StateGraph, START, END

from graph.state import LeadPilotState
from graph.nodes import (
    plan_search_node,
    discover_businesses_node,
    deduplicate_and_clean_node,
    verify_websites_node,
    enrich_leads_node,
    score_leads_node,
    persist_results_node,
    generate_reports_node,
    generate_drafts_node
)
from graph.routing import route_after_discovery
from config.logging_config import logger


def build_lead_workflow():
    """Builds and compiles the stateful LangGraph lead generation workflow."""
    workflow = StateGraph(LeadPilotState)

    # Add Nodes
    workflow.add_node("plan_search", plan_search_node)
    workflow.add_node("discover_businesses", discover_businesses_node)
    workflow.add_node("deduplicate_and_clean", deduplicate_and_clean_node)
    workflow.add_node("verify_websites", verify_websites_node)
    workflow.add_node("enrich_leads", enrich_leads_node)
    workflow.add_node("score_leads", score_leads_node)
    workflow.add_node("persist_results", persist_results_node)
    workflow.add_node("generate_reports", generate_reports_node)
    workflow.add_node("generate_drafts", generate_drafts_node)

    # Edges
    workflow.add_edge(START, "plan_search")
    workflow.add_edge("plan_search", "discover_businesses")

    # Conditional Routing after discovery
    workflow.add_conditional_edges(
        "discover_businesses",
        route_after_discovery,
        {
            "deduplicate_and_clean": "deduplicate_and_clean",
            "persist_results": "persist_results",
            "end": END
        }
    )

    workflow.add_edge("deduplicate_and_clean", "verify_websites")
    workflow.add_edge("verify_websites", "enrich_leads")
    workflow.add_edge("enrich_leads", "score_leads")
    workflow.add_edge("score_leads", "persist_results")
    workflow.add_edge("persist_results", "generate_reports")
    workflow.add_edge("generate_reports", "generate_drafts")
    workflow.add_edge("generate_drafts", END)

    return workflow.compile()


lead_graph = build_lead_workflow()


def run_lead_workflow(
    search_params: Dict[str, Any],
    progress_callback: Optional[Callable[[str, int, str], None]] = None
) -> LeadPilotState:
    """
    Executes the multi-agent pipeline and reports progress.
    progress_callback signature: (step_name, percentage, detail_message)
    """
    initial_state: LeadPilotState = {
        "job_id": "",
        "search_input": search_params,
        "execution_plan": {},
        "discovered_records": [],
        "deduplicated_records": [],
        "verified_records": [],
        "enriched_records": [],
        "qualified_leads": [],
        "all_scored_records": [],
        "persisted_leads": [],
        "email_drafts": [],
        "excel_report_path": None,
        "csv_report_path": None,
        "api_calls_made": 0,
        "errors": [],
        "current_step": "Initiating Search",
        "is_cancelled": False,
        "status": "RUNNING",
        "step_timings": {}
    }

    steps = [
        ("plan_search", "Search Planning Agent", 10),
        ("discover_businesses", "Business Discovery Agent", 30),
        ("deduplicate_and_clean", "Data Quality & Deduplication Agent", 45),
        ("verify_websites", "Website Verification Agent", 60),
        ("enrich_leads", "Business Enrichment Agent", 70),
        ("score_leads", "Lead Scoring Agent", 80),
        ("persist_results", "Database Persistence", 88),
        ("generate_reports", "Excel Report Generation Agent", 94),
        ("generate_drafts", "Outreach Personalization Agent", 100),
    ]

    current_state = initial_state
    for node_name, label, pct in steps:
        if current_state.get("is_cancelled"):
            current_state["status"] = "CANCELLED"
            break

        if progress_callback:
            progress_callback(node_name, pct, f"Running {label}...")

        # Execute node
        node_func = globals().get(f"{node_name}_node")
        if node_func:
            current_state = node_func(current_state)

        # Check conditional exit after discovery
        if node_name == "discover_businesses" and not current_state.get("discovered_records"):
            logger.info("No records discovered, persisting summary and exiting early.")
            current_state = persist_results_node(current_state)
            break

    if progress_callback:
        progress_callback("completed", 100, "Workflow execution complete!")

    return current_state

