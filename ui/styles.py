# Custom CSS for LeadPilot AI SaaS UI styling

CUSTOM_CSS = """
<style>
    /* Global layout enhancements */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-align: center;
    }
    .badge-high {
        background-color: #DCFCE7;
        color: #15803D;
    }
    .badge-medium {
        background-color: #FEF9C3;
        color: #854D0E;
    }
    .badge-low {
        background-color: #F1F5F9;
        color: #475569;
    }
    .badge-no-web {
        background-color: #FEE2E2;
        color: #B91C1C;
    }
    .badge-social {
        background-color: #F3E8FF;
        color: #6B21A8;
    }
    .badge-has-web {
        background-color: #E0E7FF;
        color: #3730A3;
    }
    .badge-demo {
        background-color: #FFEDD5;
        color: #C2410C;
        border: 1px dashed #FB923C;
    }

    /* Section Headers */
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .section-subtitle {
        font-size: 0.88rem;
        color: #64748B;
        margin-bottom: 18px;
    }

    /* Custom buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.15s ease-in-out;
    }
</style>
"""

