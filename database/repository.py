import datetime
import json
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_

from database.models import (
    Lead, LeadEmail, VerificationResult, SearchJob, EmailDraft,
    ContactHistory, SuppressionList, AuditLog
)
from utils.deduplication import is_duplicate_record, merge_business_records, normalize_business_name
from config.logging_config import logger


class LeadRepository:
    def __init__(self, db: Session = None):
        if db is None:
            from database.connection import get_db_session
            self._session_ctx = get_db_session()
            self.db = self._session_ctx.__enter__()
        else:
            self._session_ctx = None
            self.db = db

    def __del__(self):
        if self._session_ctx is not None:
            try:
                self._session_ctx.__exit__(None, None, None)
            except Exception:
                pass

    # ------------------ LEAD OPERATIONS ------------------
    def get_lead_by_id(self, lead_id: int) -> Optional[Lead]:
        return self.db.query(Lead).filter(Lead.id == lead_id).first()

    def get_lead_by_place_id(self, place_id: str) -> Optional[Lead]:
        if not place_id:
            return None
        return self.db.query(Lead).filter(Lead.place_id == place_id).first()

    def get_lead_by_phone(self, phone: str) -> Optional[Lead]:
        if not phone:
            return None
        return self.db.query(Lead).filter(Lead.phone_number == phone).first()

    def list_all_leads_dict(self) -> List[Dict[str, Any]]:
        """Returns minimal dict representations of existing leads for deduplication checks."""
        leads = self.db.query(
            Lead.id, Lead.place_id, Lead.business_name, Lead.full_address,
            Lead.area, Lead.city, Lead.phone_number, Lead.website_url
        ).all()
        return [
            {
                "id": l.id,
                "place_id": l.place_id,
                "business_name": l.business_name,
                "full_address": l.full_address,
                "area": l.area,
                "city": l.city,
                "phone_number": l.phone_number,
                "website_url": l.website_url
            }
            for l in leads
        ]

    def create_or_merge_lead(self, lead_data: Dict[str, Any]) -> Tuple[Lead, bool, str]:
        """
        Deduplicates and creates or updates a lead.
        Returns: (lead_object, is_new, action_taken)
        """
        existing_dicts = self.list_all_leads_dict()
        is_dup, matched_lead, reason = is_duplicate_record(lead_data, existing_dicts)

        if is_dup and matched_lead:
            existing_lead = self.get_lead_by_id(matched_lead["id"])
            if existing_lead:
                merged, conflicts = merge_business_records(existing_lead.__dict__, lead_data)
                # Apply non-conflicting merged fields
                if not existing_lead.phone_number and merged.get("phone_number"):
                    existing_lead.phone_number = merged.get("phone_number")
                if not existing_lead.website_url and merged.get("website_url"):
                    existing_lead.website_url = merged.get("website_url")
                if not existing_lead.area and merged.get("area"):
                    existing_lead.area = merged.get("area")
                existing_lead.updated_at = datetime.datetime.utcnow()
                self.db.commit()
                return existing_lead, False, f"MERGED_{reason}"

        # Insert new lead
        norm_name = normalize_business_name(lead_data.get("business_name"))
        new_lead = Lead(
            place_id=lead_data.get("place_id"),
            business_name=lead_data.get("business_name") or "Unknown Business",
            normalized_business_name=norm_name,
            category=lead_data.get("category"),
            full_address=lead_data.get("full_address"),
            area=lead_data.get("area"),
            city=lead_data.get("city"),
            state=lead_data.get("state"),
            country=lead_data.get("country", "India"),
            phone_number=lead_data.get("phone_number"),
            website_url=lead_data.get("website_url"),
            maps_url=lead_data.get("maps_url"),
            rating=lead_data.get("rating"),
            review_count=lead_data.get("review_count", 0),
            latitude=lead_data.get("latitude"),
            longitude=lead_data.get("longitude"),
            website_status=lead_data.get("website_status", "UNVERIFIED"),
            verification_confidence=lead_data.get("verification_confidence", 0.0),
            lead_score=lead_data.get("lead_score", 0.0),
            priority=lead_data.get("priority", "Low"),
            scoring_explanation=lead_data.get("scoring_explanation"),
            contact_status=lead_data.get("contact_status", "Not contacted"),
            is_demo=lead_data.get("is_demo", False),
            source=lead_data.get("source", "Google Places API"),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            last_verified_at=datetime.datetime.utcnow() if lead_data.get("website_status") else None
        )
        self.db.add(new_lead)
        self.db.commit()
        self.db.refresh(new_lead)

        # Add email if present
        if lead_data.get("email"):
            email_rec = LeadEmail(
                lead_id=new_lead.id,
                email_address=lead_data.get("email"),
                email_source=lead_data.get("email_source", "Discovery/Enrichment"),
                validation_status="VALID",
                is_primary=True
            )
            self.db.add(email_rec)
            self.db.commit()

        return new_lead, True, "CREATED"

    def filter_leads(
        self,
        city: Optional[str] = None,
        category: Optional[str] = None,
        website_status: Optional[str] = None,
        priority: Optional[str] = None,
        contact_status: Optional[str] = None,
        min_score: Optional[float] = None,
        has_phone: Optional[bool] = None,
        has_email: Optional[bool] = None,
        is_demo: Optional[bool] = None,
        search_query: Optional[str] = None,
        limit: int = 200,
        offset: int = 0
    ) -> Tuple[List[Lead], int]:
        """Filters leads with pagination and returns (leads_list, total_count)."""
        query = self.db.query(Lead)

        if city:
            query = query.filter(func.lower(Lead.city) == city.lower())
        if category:
            query = query.filter(func.lower(Lead.category) == category.lower())
        if website_status and website_status != "All":
            query = query.filter(Lead.website_status == website_status)
        if priority and priority != "All":
            query = query.filter(Lead.priority == priority)
        if contact_status and contact_status != "All":
            query = query.filter(Lead.contact_status == contact_status)
        if min_score is not None:
            query = query.filter(Lead.lead_score >= min_score)
        if has_phone is True:
            query = query.filter(Lead.phone_number.isnot(None), Lead.phone_number != "")
        if has_email is True:
            query = query.filter(Lead.emails.any())
        if is_demo is not None:
            query = query.filter(Lead.is_demo == is_demo)
        if search_query:
            term = f"%{search_query.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Lead.business_name).like(term),
                    func.lower(Lead.full_address).like(term),
                    func.lower(Lead.area).like(term),
                    func.lower(Lead.phone_number).like(term)
                )
            )

        total_count = query.count()
        leads = query.order_by(desc(Lead.lead_score), desc(Lead.created_at)).offset(offset).limit(limit).all()
        return leads, total_count

    def update_lead(
        self,
        lead_id: int,
        updates: Optional[Dict[str, Any]] = None,
        crm_status: Optional[str] = None,
        notes: Optional[str] = None,
        deal_value: Optional[float] = None,
        **kwargs
    ) -> Optional[Lead]:
        lead = self.get_lead_by_id(lead_id)
        if not lead:
            return None
        all_updates = dict(updates or {})
        if crm_status is not None:
            all_updates["contact_status"] = crm_status
        if notes is not None:
            all_updates["notes"] = notes
        if deal_value is not None:
            all_updates["estimated_deal_value"] = deal_value
        all_updates.update({k: v for k, v in kwargs.items() if v is not None})
        for key, value in all_updates.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
        lead.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(lead)
        return lead

    # ------------------ SUPPRESSION OPERATIONS ------------------
    def is_suppressed(self, contact: str, contact_type: str = "email") -> bool:
        """Checks whether an email, phone, or domain is in the suppression list."""
        if not contact:
            return False
        clean = contact.strip().lower()
        # Direct match
        match = self.db.query(SuppressionList).filter(
            SuppressionList.normalized_contact == clean
        ).first()
        if match:
            return True
        # Check domain suppression if contact is email
        if contact_type == "email" and "@" in clean:
            domain = clean.split("@")[-1]
            domain_match = self.db.query(SuppressionList).filter(
                SuppressionList.normalized_contact == domain,
                SuppressionList.contact_type == "domain"
            ).first()
            if domain_match:
                return True
        return False

    def add_suppression(self, contact: str, contact_type: str, reason: str, source: str = "USER") -> SuppressionList:
        clean = contact.strip().lower()
        existing = self.db.query(SuppressionList).filter(SuppressionList.normalized_contact == clean).first()
        if existing:
            return existing
        sup = SuppressionList(
            normalized_contact=clean,
            contact_type=contact_type,
            reason=reason,
            source=source
        )
        self.db.add(sup)
        self.db.commit()
        self.db.refresh(sup)
        return sup

    # ------------------ EMAIL DRAFTS OPERATIONS ------------------
    def create_or_update_draft(
        self,
        lead_id: int,
        recipient_email: str,
        subject: str,
        body: str,
        personalization_evidence: Optional[str] = None
    ) -> EmailDraft:
        draft = self.db.query(EmailDraft).filter(EmailDraft.lead_id == lead_id).first()
        if draft:
            draft.recipient_email = recipient_email
            draft.subject = subject
            draft.body = body
            draft.personalization_evidence = personalization_evidence
            draft.status = "DRAFT_READY"
            draft.updated_at = datetime.datetime.utcnow()
        else:
            draft = EmailDraft(
                lead_id=lead_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                personalization_evidence=personalization_evidence,
                status="DRAFT_READY"
            )
            self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def list_drafts(self, status: Optional[str] = None) -> List[EmailDraft]:
        q = self.db.query(EmailDraft)
        if status and status != "All":
            q = q.filter(EmailDraft.status == status)
        return q.order_by(desc(EmailDraft.updated_at)).all()

    def update_draft_status(self, draft_id: int, status: str, error_message: Optional[str] = None, provider_id: Optional[str] = None):
        draft = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if draft:
            draft.status = status
            draft.updated_at = datetime.datetime.utcnow()
            if status == "APPROVED":
                draft.approved_at = datetime.datetime.utcnow()
            elif status == "SENT":
                draft.sent_at = datetime.datetime.utcnow()
                draft.provider_message_id = provider_id
            if error_message:
                draft.error_message = error_message
            self.db.commit()

    # ------------------ CONTACT HISTORY ------------------
    def log_contact_event(
        self,
        lead_id: int,
        contact_method: str,
        event_type: str,
        notes: Optional[str] = None,
        next_action: Optional[str] = None,
        next_action_date: Optional[datetime.datetime] = None
    ) -> ContactHistory:
        hist = ContactHistory(
            lead_id=lead_id,
            contact_method=contact_method,
            event_type=event_type,
            notes=notes,
            next_action=next_action,
            next_action_date=next_action_date
        )
        self.db.add(hist)
        # Also update parent lead contact status
        lead = self.get_lead_by_id(lead_id)
        if lead and event_type:
            lead.contact_status = event_type
            lead.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(hist)
        return hist

    def get_lead_contact_history(self, lead_id: int) -> List[ContactHistory]:
        return self.db.query(ContactHistory).filter(ContactHistory.lead_id == lead_id).order_by(desc(ContactHistory.event_timestamp)).all()

    # ------------------ VERIFICATION RESULTS ------------------
    def record_verification(
        self,
        lead_id: int,
        method: str,
        status: str,
        evidence: str,
        source: str,
        confidence: float,
        candidate_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> VerificationResult:
        res = VerificationResult(
            lead_id=lead_id,
            verification_method=method,
            candidate_url=candidate_url,
            verification_status=status,
            evidence_summary=evidence,
            source=source,
            confidence=confidence,
            error_message=error_message
        )
        self.db.add(res)
        lead = self.get_lead_by_id(lead_id)
        if lead:
            lead.website_status = status
            lead.verification_confidence = confidence
            lead.last_verified_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(res)
        return res

    # ------------------ SEARCH JOBS ------------------
    def create_search_job(self, job_id: str, params: Dict[str, Any], est_api: int = 0) -> SearchJob:
        job = SearchJob(
            id=job_id,
            query_parameters=json.dumps(params),
            status="RUNNING",
            estimated_api_usage=est_api
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def complete_search_job(
        self,
        job_id: str,
        status: str,
        discovered: int,
        unique: int,
        errors: int = 0,
        actual_api: int = 0,
        summary: Optional[str] = None
    ):
        job = self.db.query(SearchJob).filter(SearchJob.id == job_id).first()
        if job:
            job.status = status
            job.completed_at = datetime.datetime.utcnow()
            job.discovered_count = discovered
            job.unique_count = unique
            job.error_count = errors
            job.actual_api_usage = actual_api
            job.error_summary = summary
            self.db.commit()

    def get_recent_jobs(self, limit: int = 10) -> List[SearchJob]:
        return self.db.query(SearchJob).order_by(desc(SearchJob.started_at)).limit(limit).all()

    # ------------------ AUDIT LOGS ------------------
    def log_audit(self, event_type: str, entity_type: str, entity_id: str, outcome: str, details: Optional[str] = None):
        audit = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            outcome=outcome,
            sanitized_details=details
        )
        self.db.add(audit)
        self.db.commit()

    # ------------------ DASHBOARD METRICS ------------------
    def get_metrics(self) -> Dict[str, Any]:
        """Calculates real overview metrics from the live database."""
        total_discovered = self.db.query(func.count(Lead.id)).scalar() or 0
        no_website = self.db.query(func.count(Lead.id)).filter(Lead.website_status == "NO_WEBSITE_FOUND").scalar() or 0
        has_website = self.db.query(func.count(Lead.id)).filter(Lead.website_status == "WEBSITE_FOUND").scalar() or 0
        social_only = self.db.query(func.count(Lead.id)).filter(Lead.website_status == "SOCIAL_MEDIA_ONLY").scalar() or 0
        unverified = self.db.query(func.count(Lead.id)).filter(Lead.website_status == "UNVERIFIED").scalar() or 0
        high_priority = self.db.query(func.count(Lead.id)).filter(Lead.priority == "High").scalar() or 0
        
        pending_approval = self.db.query(func.count(EmailDraft.id)).filter(
            EmailDraft.status.in_(["DRAFT_READY", "PENDING_APPROVAL"])
        ).scalar() or 0
        
        emails_sent = self.db.query(func.count(EmailDraft.id)).filter(EmailDraft.status == "SENT").scalar() or 0
        
        interested = self.db.query(func.count(Lead.id)).filter(
            Lead.contact_status.in_(["Interested", "Meeting scheduled", "Proposal sent"])
        ).scalar() or 0
        
        converted = self.db.query(func.count(Lead.id)).filter(Lead.contact_status == "Converted").scalar() or 0

        # Estimated pipeline value
        pipeline_val = self.db.query(func.sum(Lead.estimated_deal_value)).filter(
            Lead.contact_status.in_(["Interested", "Meeting scheduled", "Proposal sent", "Converted"])
        ).scalar() or 0.0

        return {
            "total_discovered": total_discovered,
            "unique_businesses": total_discovered,
            "no_website_found": no_website,
            "has_website": has_website,
            "social_only": social_only,
            "unverified": unverified,
            "high_priority": high_priority,
            "pending_approval": pending_approval,
            "emails_sent": emails_sent,
            "interested": interested,
            "converted": converted,
            "pipeline_value": pipeline_val
        }

    def get_category_counts(self) -> List[Tuple[str, int]]:
        return self.db.query(Lead.category, func.count(Lead.id)).group_by(Lead.category).order_by(desc(func.count(Lead.id))).limit(10).all()

    def get_city_counts(self) -> List[Tuple[str, int]]:
        return self.db.query(Lead.city, func.count(Lead.id)).filter(Lead.city.isnot(None)).group_by(Lead.city).order_by(desc(func.count(Lead.id))).limit(10).all()

    def get_website_status_counts(self) -> List[Tuple[str, int]]:
        return self.db.query(Lead.website_status, func.count(Lead.id)).group_by(Lead.website_status).all()

    def get_priority_counts(self) -> List[Tuple[str, int]]:
        return self.db.query(Lead.priority, func.count(Lead.id)).group_by(Lead.priority).all()

    def get_contact_status_counts(self) -> List[Tuple[str, int]]:
        return self.db.query(Lead.contact_status, func.count(Lead.id)).group_by(Lead.contact_status).all()

    # ============================================================
    # API-FACING METHODS  (used by server.py / FastAPI endpoints)
    # ============================================================

    # ── Dashboard ────────────────────────────────────────────────
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Returns a dict compatible with the /api/metrics endpoint."""
        total     = self.db.query(func.count(Lead.id)).scalar() or 0
        verified  = self.db.query(func.count(Lead.id)).filter(Lead.website_status == "WEBSITE_FOUND").scalar() or 0
        high_sc   = self.db.query(func.count(Lead.id)).filter(Lead.lead_score >= 70).scalar() or 0
        sent      = self.db.query(func.count(EmailDraft.id)).filter(EmailDraft.status == "SENT").scalar() or 0
        avg_sc    = self.db.query(func.avg(Lead.lead_score)).scalar() or 0.0
        return {
            "total_leads":      total,
            "verified_leads":   verified,
            "high_score_leads": high_sc,
            "emails_sent":      sent,
            "avg_score":        round(float(avg_sc), 1),
        }

    # ── Leads — paginated filter (new signature for REST API) ────
    def filter_leads(
        self,
        page: int = 1,
        per_page: int = 50,
        search: str = "",
        crm_status: Optional[str] = None,
        min_score: int = 0,
        has_website: Optional[bool] = None,
        sort_by: str = "score",
        sort_dir: str = "desc",
    ) -> Tuple[List[Dict], int]:
        """Paginated lead list for the REST API. Returns (list_of_dicts, total_count)."""
        q = self.db.query(Lead)

        if search:
            term = f"%{search.lower()}%"
            q = q.filter(or_(
                func.lower(Lead.business_name).like(term),
                func.lower(Lead.full_address).like(term),
                func.lower(Lead.category).like(term),
                func.lower(Lead.phone_number).like(term),
            ))

        if crm_status:
            q = q.filter(Lead.contact_status == crm_status)

        if min_score and min_score > 0:
            q = q.filter(Lead.lead_score >= min_score)

        if has_website is True:
            q = q.filter(Lead.website_status == "WEBSITE_FOUND")
        elif has_website is False:
            q = q.filter(Lead.website_status == "NO_WEBSITE_FOUND")

        # Sorting
        sort_col_map = {
            "score":         Lead.lead_score,
            "business_name": Lead.business_name,
            "rating":        Lead.rating,
            "created_at":    Lead.created_at,
        }
        col = sort_col_map.get(sort_by, Lead.lead_score)
        if sort_dir == "asc":
            q = q.order_by(col)
        else:
            q = q.order_by(desc(col))

        total = q.count()
        offset = (page - 1) * per_page
        rows = q.offset(offset).limit(per_page).all()

        def _lead_dict(l: Lead) -> Dict:
            return {
                "id":           l.id,
                "business_name": l.business_name,
                "category":     l.category,
                "score":        int(l.lead_score or 0),
                "lead_score":   l.lead_score or 0.0,
                "has_website":  l.website_status == "WEBSITE_FOUND",
                "website_status": l.website_status,
                "website":      l.website_url,
                "website_url":  l.website_url,
                "phone":        l.phone_number,
                "phone_number": l.phone_number,
                "address":      l.full_address,
                "full_address": l.full_address,
                "area":         l.area,
                "city":         l.city,
                "state":        l.state,
                "country":      l.country,
                "rating":       l.rating,
                "review_count": l.review_count,
                "crm_status":   l.contact_status or "new",
                "contact_status": l.contact_status or "Not contacted",
                "priority":     l.priority or "Low",
                "scoring_explanation": l.scoring_explanation,
                "maps_url":     l.maps_url,
                "verification_confidence": l.verification_confidence,
                "deal_value":   l.estimated_deal_value,
                "estimated_deal_value": l.estimated_deal_value,
                "notes":        l.notes if hasattr(l, "notes") else None,
                "is_demo":      l.is_demo,
                "source":       getattr(l, "source", None) or ("OpenStreetMap" if l.place_id and str(l.place_id).startswith("osm:") else ("Simulated Places Data (Demo Mode)" if l.is_demo else "Google Places API")),
                "attribution":  "Data © OpenStreetMap contributors (ODbL)" if (getattr(l, "source", None) == "OpenStreetMap" or (l.place_id and str(l.place_id).startswith("osm:"))) else "Data © Google LLC",
                "created_at":   str(l.created_at)[:19] if l.created_at else None,
                "last_verified_at": str(l.last_verified_at)[:19] if l.last_verified_at else None,
            }

        return [_lead_dict(l) for l in rows], total

    # ── Single lead dict for API ─────────────────────────────────
    def get_lead_dict(self, lead_id: int) -> Optional[Dict[str, Any]]:
        l = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not l:
            return None
        return {
            "id":           l.id,
            "business_name": l.business_name,
            "category":     l.category,
            "score":        int(l.lead_score or 0),
            "lead_score":   l.lead_score or 0.0,
            "has_website":  l.website_status == "WEBSITE_FOUND",
            "website_status": l.website_status,
            "website":      l.website_url,
            "website_url":  l.website_url,
            "phone":        l.phone_number,
            "phone_number": l.phone_number,
            "address":      l.full_address,
            "full_address": l.full_address,
            "area":         l.area,
            "city":         l.city,
            "state":        l.state,
            "country":      l.country,
            "rating":       l.rating,
            "review_count": l.review_count,
            "crm_status":   l.contact_status or "new",
            "contact_status": l.contact_status or "Not contacted",
            "priority":     l.priority or "Low",
            "scoring_explanation": l.scoring_explanation,
            "maps_url":     l.maps_url,
            "verification_confidence": l.verification_confidence,
            "deal_value":   l.estimated_deal_value,
            "estimated_deal_value": l.estimated_deal_value,
            "notes":        l.notes if hasattr(l, "notes") else None,
            "is_demo":      l.is_demo,
            "source":       getattr(l, "source", None) or ("OpenStreetMap" if l.place_id and str(l.place_id).startswith("osm:") else ("Simulated Places Data (Demo Mode)" if l.is_demo else "Google Places API")),
            "attribution":  "Data © OpenStreetMap contributors (ODbL)" if (getattr(l, "source", None) == "OpenStreetMap" or (l.place_id and str(l.place_id).startswith("osm:"))) else "Data © Google LLC",
            "created_at":   str(l.created_at)[:19] if l.created_at else None,
            "last_verified_at": str(l.last_verified_at)[:19] if l.last_verified_at else None,
        }

    # ── Delete lead ──────────────────────────────────────────────
    def delete_lead(self, lead_id: int) -> bool:
        l = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not l:
            return False
        self.db.delete(l)
        self.db.commit()
        return True

    # ── Email drafts (API-facing) ─────────────────────────────────
    def get_email_drafts(self, status: Optional[str] = None) -> List[Dict]:
        q = self.db.query(EmailDraft)
        if status and status not in ("all", ""):
            # Map friendly names to DB values
            status_map = {
                "pending":  ["DRAFT_READY", "PENDING_APPROVAL"],
                "approved": ["APPROVED"],
                "rejected": ["REJECTED"],
                "sent":     ["SENT"],
            }
            db_statuses = status_map.get(status.lower(), [status.upper()])
            q = q.filter(EmailDraft.status.in_(db_statuses))
        drafts = q.order_by(desc(EmailDraft.updated_at)).all()

        def _draft_dict(d: EmailDraft) -> Dict:
            # Try to get lead name
            lead = self.db.query(Lead.business_name).filter(Lead.id == d.lead_id).first()
            return {
                "id":             d.id,
                "lead_id":        d.lead_id,
                "recipient_name": lead.business_name if lead else f"Lead #{d.lead_id}",
                "recipient_email": d.recipient_email,
                "subject":        d.subject,
                "body":           d.body,
                "status":         d.status.lower() if d.status else "draft",
                "created_at":     str(d.created_at)[:19] if d.created_at else None,
                "updated_at":     str(d.updated_at)[:19] if d.updated_at else None,
            }

        return [_draft_dict(d) for d in drafts]

    def get_draft_by_id(self, draft_id: int) -> Optional[Dict]:
        d = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not d:
            return None
        lead = self.db.query(Lead.business_name).filter(Lead.id == d.lead_id).first()
        return {
            "id":             d.id,
            "lead_id":        d.lead_id,
            "recipient_name": lead.business_name if lead else f"Lead #{d.lead_id}",
            "recipient_email": d.recipient_email,
            "subject":        d.subject,
            "body":           d.body,
            "status":         d.status.lower() if d.status else "draft",
        }

    def update_draft(self, draft_id: int, subject: Optional[str] = None, body: Optional[str] = None) -> bool:
        d = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not d:
            return False
        if subject is not None:
            d.subject = subject
        if body is not None:
            d.body = body
        d.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        return True

    def set_draft_status(self, draft_id: int, status: str) -> bool:
        status_map = {"approved": "APPROVED", "rejected": "REJECTED", "sent": "SENT"}
        db_status = status_map.get(status.lower(), status.upper())
        self.update_draft_status(draft_id, db_status)
        return True

    # ── Suppression (API-facing shorthand) ───────────────────────
    def add_to_suppression(self, email: str, reason: str = "manual") -> None:
        contact_type = "email" if "@" in email else "domain"
        self.add_suppression(email, contact_type, reason, "API")

    # ── Chart data ───────────────────────────────────────────────
    def get_website_status_counts(self) -> Dict[str, int]:  # type: ignore[override]
        rows = self.db.query(Lead.website_status, func.count(Lead.id)).group_by(Lead.website_status).all()
        result = {"has_website": 0, "no_website": 0, "unknown": 0}
        for status, cnt in rows:
            if status == "WEBSITE_FOUND":
                result["has_website"] += cnt
            elif status == "NO_WEBSITE_FOUND":
                result["no_website"] += cnt
            else:
                result["unknown"] += cnt
        return result

    def get_score_distribution(self) -> Dict[str, Any]:
        buckets = ["0-20", "21-40", "41-60", "61-80", "81-100"]
        ranges  = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
        counts = []
        for lo, hi in ranges:
            n = self.db.query(func.count(Lead.id)).filter(
                Lead.lead_score >= lo, Lead.lead_score <= hi
            ).scalar() or 0
            counts.append(n)
        return {"buckets": buckets, "counts": counts}

    def get_crm_pipeline_counts(self) -> Dict[str, int]:
        statuses = ["new", "contacted", "qualified", "proposal", "closed"]
        result = {s: 0 for s in statuses}
        rows = self.db.query(Lead.contact_status, func.count(Lead.id)).group_by(Lead.contact_status).all()
        for status, cnt in rows:
            key = (status or "new").lower()
            if key in result:
                result[key] += cnt
            else:
                result["new"] += cnt  # default unmapped to "new"
        return result

    def get_recent_jobs(self, limit: int = 20) -> List[Dict]:
        jobs = self.db.query(SearchJob).order_by(desc(SearchJob.started_at)).limit(limit).all()
        return [
            {
                "id":         j.id,
                "status":     j.status,
                "discovered": j.discovered_count,
                "unique":     j.unique_count,
                "started_at": str(j.started_at)[:19] if j.started_at else None,
                "completed_at": str(j.completed_at)[:19] if j.completed_at else None,
            }
            for j in jobs
        ]

