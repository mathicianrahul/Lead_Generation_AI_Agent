from typing import TypedDict, List, Dict, Any, Optional


class LeadPilotState(TypedDict):
    """LangGraph state schema representing the complete multi-agent workflow state."""
    job_id: str
    search_input: Dict[str, Any]
    execution_plan: Dict[str, Any]
    discovered_records: List[Dict[str, Any]]
    deduplicated_records: List[Dict[str, Any]]
    verified_records: List[Dict[str, Any]]
    enriched_records: List[Dict[str, Any]]
    qualified_leads: List[Dict[str, Any]]
    all_scored_records: List[Dict[str, Any]]
    persisted_leads: List[Dict[str, Any]]
    email_drafts: List[Dict[str, Any]]
    excel_report_path: Optional[str]
    csv_report_path: Optional[str]
    api_calls_made: int
    errors: List[str]
    current_step: str
    is_cancelled: bool
    status: str
    step_timings: Dict[str, float]

