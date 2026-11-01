import pytest
from services.gmail_service import GmailService
from agents.email_delivery_agent import EmailDeliveryAgent


def test_send_blocked_without_human_approval():
    agent = EmailDeliveryAgent()
    draft = {
        "recipient_email": "prospect@legitbusiness.com",
        "subject": "Website proposal",
        "body": "Hello"
    }
    success, msg_id, status = agent.run(
        draft=draft,
        is_human_approved=False,
        is_suppressed=False,
        today_sent_count=0
    )
    assert success is False
    assert "APPROVAL_REQUIRED" in status


def test_send_blocked_if_suppressed():
    agent = EmailDeliveryAgent()
    draft = {
        "recipient_email": "optout@legitbusiness.com",
        "subject": "Website proposal",
        "body": "Hello"
    }
    success, msg_id, status = agent.run(
        draft=draft,
        is_human_approved=True,
        is_suppressed=True,
        today_sent_count=0
    )
    assert success is False
    assert "SUPPRESSED" in status


def test_send_blocked_on_daily_cap_exceeded():
    service = GmailService(daily_cap=5)
    agent = EmailDeliveryAgent(delivery_service=service)
    draft = {
        "recipient_email": "prospect@legitbusiness.com",
        "subject": "Website proposal",
        "body": "Hello"
    }
    success, msg_id, status = agent.run(
        draft=draft,
        is_human_approved=True,
        is_suppressed=False,
        today_sent_count=5  # Daily limit reached
    )
    assert success is False
    assert "Daily email limit reached" in status


def test_send_blocked_invalid_recipient():
    agent = EmailDeliveryAgent()
    draft = {
        "recipient_email": "not-an-email",
        "subject": "Website proposal",
        "body": "Hello"
    }
    success, msg_id, status = agent.run(
        draft=draft,
        is_human_approved=True,
        is_suppressed=False,
        today_sent_count=0
    )
    assert success is False
    assert "INVALID_RECIPIENT" in status


def test_approved_send_succeeds_in_simulation_mode():
    service = GmailService(daily_cap=10)
    agent = EmailDeliveryAgent(delivery_service=service)
    draft = {
        "recipient_email": "owner@clinic.org",
        "subject": "Tailored Website for Arogya Clinic",
        "body": "Dear Doctor, We can help build your website..."
    }
    success, msg_id, status = agent.run(
        draft=draft,
        is_human_approved=True,
        is_suppressed=False,
        today_sent_count=1
    )
    assert success is True
    assert msg_id is not None
    assert "sim_gmail_msg_" in msg_id
