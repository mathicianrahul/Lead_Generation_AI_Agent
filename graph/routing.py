from graph.state import LeadPilotState


def route_after_discovery(state: LeadPilotState) -> str:
    """Routes workflow after discovery step."""
    if state.get("is_cancelled"):
        return "end"
    if not state.get("discovered_records"):
        return "persist_results"
    return "deduplicate_and_clean"


def route_after_cancellation_check(state: LeadPilotState) -> str:
    """Checks if search was cancelled by user."""
    if state.get("is_cancelled"):
        return "end"
    return "continue"

