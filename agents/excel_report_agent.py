from typing import List, Dict, Any, Optional
from services.export_service import export_service
from config.logging_config import logger


class ExcelReportAgent:
    """Agent 7: Generates multi-sheet downloadable Excel reports with styling and protection."""

    def __init__(self, exporter=export_service):
        self.exporter = exporter

    def run(
        self,
        leads: List[Dict[str, Any]],
        search_summary: Optional[Dict[str, Any]] = None,
        contact_history: Optional[List[Dict[str, Any]]] = None,
        filename_prefix: str = "leadpilot_leads",
        min_high_priority_score: float = 80.0
    ) -> str:
        """Generates formatted Excel report and returns the absolute file path."""
        path = self.exporter.export_to_excel(
            leads=leads,
            search_summary=search_summary,
            contact_history=contact_history,
            filename_prefix=filename_prefix,
            min_high_priority_score=min_high_priority_score
        )
        logger.info("ExcelReportAgent successfully generated report at %s", path)
        return path


excel_report_agent = ExcelReportAgent()

