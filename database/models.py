import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from database.connection import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String(255), unique=True, nullable=True, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    normalized_business_name = Column(String(255), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    full_address = Column(Text, nullable=True)
    area = Column(String(150), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    phone_number = Column(String(50), nullable=True, index=True)
    website_url = Column(String(500), nullable=True)
    maps_url = Column(String(500), nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Website verification fields
    # Values: NO_WEBSITE_FOUND, WEBSITE_FOUND, SOCIAL_MEDIA_ONLY, DIRECTORY_ONLY, UNVERIFIED, CHECK_FAILED
    website_status = Column(String(50), default="UNVERIFIED", index=True)
    verification_confidence = Column(Float, default=0.0)

    # Lead Qualification fields
    lead_score = Column(Float, default=0.0, index=True)
    # Values: High (80-100), Medium (60-79), Low (0-59)
    priority = Column(String(20), default="Low", index=True)
    scoring_explanation = Column(Text, nullable=True)

    # CRM tracking fields
    # Values: Not contacted, Email drafted, Email sent, Call planned, Interested, Meeting scheduled, Proposal sent, Converted, Not interested, Opted out, Do not contact
    contact_status = Column(String(50), default="Not contacted", index=True)
    notes = Column(Text, nullable=True)
    estimated_deal_value = Column(Float, nullable=True)
    next_follow_up_date = Column(DateTime, nullable=True)

    # Data origin flag: False = Real API data, True = Simulated/Demo data
    is_demo = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)

    # Relationships
    emails = relationship("LeadEmail", back_populates="lead", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="lead", cascade="all, delete-orphan")
    email_drafts = relationship("EmailDraft", back_populates="lead", cascade="all, delete-orphan")
    contact_history = relationship("ContactHistory", back_populates="lead", cascade="all, delete-orphan")


class LeadEmail(Base):
    __tablename__ = "lead_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    email_address = Column(String(255), nullable=False)
    email_source = Column(String(100), nullable=True)
    validation_status = Column(String(50), default="VALID")
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lead = relationship("Lead", back_populates="emails")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    verification_method = Column(String(100), nullable=False)
    candidate_url = Column(String(500), nullable=True)
    verification_status = Column(String(50), nullable=False)
    evidence_summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    confidence = Column(Float, default=0.0)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)
    error_message = Column(Text, nullable=True)

    lead = relationship("Lead", back_populates="verification_results")


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id = Column(String(100), primary_key=True)
    query_parameters = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    discovered_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    estimated_api_usage = Column(Integer, default=0)
    actual_api_usage = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    personalization_evidence = Column(Text, nullable=True)
    # Statuses: NOT_DRAFTED, DRAFT_READY, PENDING_APPROVAL, APPROVED, SENT, SEND_FAILED, REPLIED, OPTED_OUT, DO_NOT_CONTACT
    status = Column(String(50), default="DRAFT_READY", index=True)
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    lead = relationship("Lead", back_populates="email_drafts")


class ContactHistory(Base):
    __tablename__ = "contact_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    contact_method = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)
    next_action = Column(String(255), nullable=True)
    next_action_date = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="contact_history")


class SuppressionList(Base):
    __tablename__ = "suppression_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    normalized_contact = Column(String(255), unique=True, nullable=False, index=True)
    contact_type = Column(String(50), nullable=False)  # email, phone, domain
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    source = Column(String(100), default="MANUAL")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    outcome = Column(String(50), default="SUCCESS")
    sanitized_details = Column(Text, nullable=True)

