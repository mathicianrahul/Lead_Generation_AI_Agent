# 🧭 LeadPilot AI
### AI Multi-Agent Lead Generation & Website Sales Agent

**LeadPilot AI** is a complete, production-grade AI lead generation system designed specifically for website development businesses and digital agencies. It discovers local businesses listed on Google Maps, verifies their website presence through multi-stage network checks, qualifies prospects based on commercial viability, enriches verified contact channels, generates multi-sheet Excel reports, and prepares evidence-grounded outreach email drafts with a strict human approval gate.

---

## 🌟 Key Features

1. **Multi-Provider Business Discovery**: Supports **Google Places API** and **OpenStreetMap Overpass API** with automatic fallback. Configurable via the `DISCOVERY_PROVIDER` environment variable (`auto`, `google`, `osm`).
2. **Transparent Website Verification Pipeline**:
   - Safe HTTP verification with full SSRF protection (rejects localhost, loopbacks, and private IP ranges `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`).
   - Identifies social-media-only profiles (`SOCIAL_MEDIA_ONLY`) vs. third-party marketplace listings (`DIRECTORY_ONLY`) vs. independent websites (`WEBSITE_FOUND`) vs. businesses without any website (`NO_WEBSITE_FOUND`).
   - Distinguishes "No website found" from technical check failures (`CHECK_FAILED`).
3. **Stateful LangGraph Workflow**: Multi-agent graph with 10 specialized agents, conditional transitions, failure recovery, and real-time execution progress.
4. **Deterministic & Explainable Lead Scoring**:
   - Scores prospects from 0 to 100 based on website opportunity, valid phone numbers, validated email, review counts, and category value.
   - Configurable scoring weights accessible via the UI Settings.
5. **Multi-Sheet Formatted Excel Reports**:
   - Generates Excel workbooks (`.xlsx`) via `openpyxl` with 5 sheets: *High-Priority Leads*, *All Prospects*, *Needs Verification*, *Contact History*, and *Search Summary*.
   - Includes formula-injection protection (escapes `=,+,-,@` triggers), column autofilter, hyperlinks, and frozen headers.
   - Also supports clean CSV export.
6. **AI Outreach Personalization**:
   - Powered by Hugging Face Inference Providers API (or OpenAI-compatible models) with a high-performance built-in deterministic engine that operates without any external API keys.
   - Only uses verified business facts; never hallucinates contact details or false urgency.
7. **Human-in-the-Loop Email Delivery & CRM**:
   - Gmail OAuth 2.0 integration with an explicit human approval gate.
   - Suppression list (Do-Not-Contact) enforcement.
   - Configurable daily sending caps to prevent quota exhaustion.
   - CRM pipeline tracking with conversion stages and deal value estimates.

---

## 🏗️ Multi-Agent Architecture

```text
                  START
                    |
                    v
       [Search Planning Agent]
                    |
                    v
      [Business Discovery Agent] (Google Places / OpenStreetMap)
                    |
                    v
    [Data Quality & Deduplication] (Place ID -> Phone -> Name/Address)
                    |
                    v
      [Website Verification Agent] (Safe HTTP / SSRF Defense / Classification)
                    |
                    v
      [Business Enrichment Agent] (Email Validation & Field Provenance)
                    |
                    v
       [Lead Scoring Agent] (0-100 Qualification Score)
                    |
                    v
      [Database Persistence Node] (SQLite / SQLAlchemy)
                    |
         +----------+----------+
         |                     |
         v                     v
[Excel Report Agent]  [Outreach Personalization Agent]
                               |
                               v
                       [Human Approval]
                               |
                               v
                    [Email Delivery Agent] (Gmail OAuth)
                               |
                               v
                         [CRM Agent]
                               |
                              END
```

---

## 📁 Project Structure

```text
Lead Generation Agent/
├── app.py                            # Streamlit Application Entrypoint
├── requirements.txt                  # Python Dependencies
├── README.md                         # Documentation & Setup Guide
├── .env.example                      # Environment Configuration Template
├── .gitignore                        # Git Secrets & Artifact Exclusions
│
├── config/
│   ├── settings.py                   # Pydantic Settings & Safety Thresholds
│   └── logging_config.py             # Sanitized Structured Logger
│
├── database/
│   ├── connection.py                 # SQLAlchemy Connection & Session Management
│   ├── models.py                     # Schema: Leads, Drafts, History, Suppression
│   └── repository.py                 # Data Access Layer & Analytics Queries
│
├── services/
│   ├── discovery_provider.py         # Abstract Discovery Provider Interface
│   ├── discovery_manager.py          # Provider Orchestrator & Auto-Fallback
│   ├── google_places_service.py      # Google Places API Search & Details
│   ├── osm_service.py                # OpenStreetMap Overpass API Discovery
│   ├── website_check_service.py      # Safe HTTP Probing & SSRF Protection
│   ├── web_search_service.py         # Secondary Web Lookup Service
│   ├── scoring_service.py            # 0-100 Heuristic Qualification Scoring
│   ├── export_service.py             # Formatted Excel (.xlsx) & CSV Exporter
│   ├── llm_service.py                # Hugging Face / Deterministic AI Engine
│   └── gmail_service.py              # Gmail API OAuth 2.0 Sender
│
├── agents/
│   ├── search_planning_agent.py      # Agent 1: Search Planning
│   ├── business_discovery_agent.py   # Agent 2: Business Discovery
│   ├── website_verification_agent.py # Agent 3: Website Detection & Verification
│   ├── business_enrichment_agent.py  # Agent 4: Business Contact Enrichment
│   ├── lead_scoring_agent.py         # Agent 5: Lead Qualification & Scoring
│   ├── data_quality_agent.py         # Agent 6: Deduplication & Normalization
│   ├── excel_report_agent.py         # Agent 7: Multi-Sheet Excel Reports
│   ├── outreach_personalization_agent.py # Agent 8: AI Outreach Personalization
│   ├── email_delivery_agent.py       # Agent 9: Safe Email Delivery & Gatekeeping
│   └── crm_agent.py                  # Agent 10: CRM & Pipeline Tracking
│
├── graph/
│   ├── state.py                      # LangGraph State Schema
│   ├── nodes.py                      # Graph Execution Nodes
│   ├── routing.py                    # Conditional Workflow Transitions
│   └── workflow.py                   # Compiled StateGraph & Runner
│
├── ui/
│   ├── styles.py                     # Custom CSS & Professional SaaS Theme
│   ├── overview.py                   # Page 1: Executive Dashboard & Metrics
│   ├── find_leads.py                 # Page 2: Lead Discovery & Search Form
│   ├── lead_database.py              # Page 3: Filterable Lead Directory & Inspector
│   ├── verification.py               # Page 4: Website Verification Hub & Override
│   ├── outreach.py                   # Page 5: Email Drafts & Approval Gate
│   ├── crm.py                        # Page 6: Sales Opportunity CRM
│   ├── reports.py                    # Page 7: Report Generation & Download Center
│   └── settings.py                   # Page 8: Keys, Weights & System Health
│
├── utils/
│   ├── phone_utils.py                # Phone Normalization (E.164 & National)
│   ├── url_validation.py             # SSRF Defense, Scheme & Host Validation
│   ├── email_validation.py           # Business Email Syntax & Domain Checking
│   ├── deduplication.py              # Multi-tier Deduplication & Merging
│   └── text_sanitization.py          # Formula Injection Protection
│
├── exports/                          # Output Directory for Generated Reports
│   └── .gitkeep
│
└── tests/
    ├── test_scoring.py               # Unit Tests: Lead Qualification Scoring
    ├── test_deduplication.py         # Unit Tests: Deduplication Cascade
    ├── test_website_verification.py  # Unit Tests: SSRF Defense & Verification
    ├── test_excel_export.py          # Unit Tests: Excel Formatting & Formula Defense
    ├── test_email_approval.py        # Unit Tests: Approval Gate & Safety Limits
    └── test_workflow.py              # Integration Test: End-to-End LangGraph Flow
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Clone and Setup Environment
```bash
git clone <repository-url>
cd "Lead Generation Agent"

# Create a virtual environment (optional but recommended)
python -m venv venv

# Activate on Windows:
venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys:
- `GOOGLE_MAPS_API_KEY`: Required for live Google Places discovery. If omitted, the application operates in **Demo Mode**, generating realistically modeled, clearly labeled test data so all features can be evaluated without cost.
- `HUGGINGFACE_API_TOKEN` / `OPENAI_API_KEY`: Optional. If omitted, LeadPilot's built-in rule engine generates tailored, evidence-grounded proposals.
- `GMAIL_CREDENTIALS_FILE`: Optional. Required only when sending live outreach emails via Gmail OAuth 2.0.

### 4. Run the Automated Tests
```bash
python -m pytest tests/
```
All 26 automated unit and integration tests will execute and pass without requiring external API spend.

### 5. Launch the Application

#### Option A: Premium Interactive Custom UI (Recommended)
```bash
python run.py
```
*(or `python -m uvicorn server:app --reload --port 8000`)*

Open your browser to `http://localhost:8000`.

#### Option B: Legacy Streamlit UI
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🔒 Security & Privacy Safeguards

- **SSRF Protection**: All HTTP verification requests pass through strict IP resolution checks, rejecting localhost, RFC 1918 private subnets, link-local addresses, and loopback ranges.
- **Formula Injection Defense**: All exported cells in `.xlsx` and `.csv` that begin with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with a leading single quote.
- **Sanitized Logging**: API keys, Bearer tokens, and secrets are dynamically masked in log outputs.
- **Human Approval Gate**: Emails can never be sent automatically. The UI requires explicit, manual human review, previewing the exact recipient and proposal text before dispatch.
- **Do-Not-Contact Enforcement**: Global suppression list prevents outreach to any email, phone number, or domain marked as opted out.

---

## 🧪 Testing Summary

The project includes an automated test suite covering:
- **Lead Scoring**: Confirmed website absence, existing websites, missing phones/emails, priority bands.
- **Deduplication**: Place ID collisions, varying phone formats (`+91` vs `0`), address matching, safe field merging.
- **Website Verification**: SSRF defenses against `127.0.0.1`, `localhost`, `192.168.1.1`, social media detection, 404 responses, and DNS failures.
- **Excel Generation**: 5-sheet generation, autofilters, cell styling, hyperlinks, and formula sanitization.
- **Email Approvals**: Rejection of unapproved sends, suppression checks, daily caps, and invalid address rejection.
- **LangGraph Workflow**: End-to-end execution of all 10 agents and database persistence.

---

## 📄 License
MIT License. Built for professional agency and freelance web development lead generation.

