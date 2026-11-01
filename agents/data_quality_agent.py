from typing import List, Dict, Any, Tuple
from utils.deduplication import is_duplicate_record, merge_business_records, normalize_business_name
from utils.phone_utils import normalize_phone_number
from config.logging_config import logger


class DataQualityAgent:
    """Agent 6: Deduplication, data normalization, and quality validation."""

    def run(
        self,
        new_records: List[Dict[str, Any]],
        existing_records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int, List[str]]:
        """
        Deduplicates incoming records against each other and against existing records.
        Returns:
            (deduplicated_records, duplicates_merged_count, conflict_logs)
        """
        unique_records = []
        all_pool = list(existing_records)
        duplicates_count = 0
        conflict_logs = []

        seen_existing_ids = set()
        for rec in new_records:
            # 1. Normalize Phone Number
            raw_phone = rec.get("phone_number")
            if raw_phone:
                e164, national, _ = normalize_phone_number(raw_phone, "IN")
                rec["phone_number"] = e164 or national or raw_phone

            # 2. Normalize Business Name
            rec["normalized_business_name"] = normalize_business_name(rec.get("business_name"))

            # 3. Deduplicate
            is_dup, matched, reason = is_duplicate_record(rec, all_pool)
            if is_dup and matched:
                duplicates_count += 1
                merged, conflicts = merge_business_records(matched, rec)
                if conflicts:
                    conflict_logs.extend(conflicts)
                logger.debug("Deduplicated record '%s' (Reason: %s)", rec.get("business_name"), reason)
                # If matched was an existing DB record that hasn't been queued yet in this run, keep merged for update
                matched_id = matched.get("id")
                if matched_id and matched_id not in seen_existing_ids:
                    seen_existing_ids.add(matched_id)
                    unique_records.append(merged)
            else:
                unique_records.append(rec)
                all_pool.append(rec)

        logger.info("DataQualityAgent processed %d records: %d unique, %d duplicate/merged",
                    len(new_records), len(unique_records), duplicates_count)

        return unique_records, duplicates_count, conflict_logs


data_quality_agent = DataQualityAgent()
