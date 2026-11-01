import { api } from '../api.js';
import { toast } from '../app.js';

export async function renderReports(container) {
  let metrics = {};
  try { metrics = await api.get('/api/metrics'); } catch {}

  container.innerHTML = `
    <div class="section-header" style="margin-bottom:24px">
      <div>
        <div class="section-title">📈 Reports & Exports</div>
        <div class="section-sub">Download your verified lead data in multi-sheet Excel or CRM CSV</div>
      </div>
    </div>

    <div class="export-grid">
      <div class="export-card">
        <span class="export-icon">📊</span>
        <div class="export-title">Excel Report</div>
        <div class="export-desc">Full 5-sheet workbook with high-priority leads, verification details, and formula-injection protected cells.</div>
        <button class="btn btn-success" onclick="downloadExcel()">⬇ Download Excel</button>
      </div>
      <div class="export-card">
        <span class="export-icon">📄</span>
        <div class="export-title">CSV Export</div>
        <div class="export-desc">Clean flat-file CSV ready for instant import into Salesforce, HubSpot, Zoho, or any CRM.</div>
        <button class="btn btn-primary" onclick="downloadCSV()">⬇ Download CSV</button>
      </div>
    </div>

    <div class="card" style="margin-top:28px">
      <div class="section-title" style="margin-bottom:16px">📊 Summary Statistics</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Total Leads</div><div class="detail-value" style="font-size:22px; font-weight:800">${metrics.total_leads||0}</div></div>
        <div class="detail-item"><div class="detail-label">Verified (Website)</div><div class="detail-value" style="font-size:22px; font-weight:800; color:var(--green-400)">${metrics.verified_leads||0}</div></div>
        <div class="detail-item"><div class="detail-label">High-Quality (Score ≥ 70)</div><div class="detail-value" style="font-size:22px; font-weight:800; color:var(--blue-400)">${metrics.high_score_leads||0}</div></div>
        <div class="detail-item"><div class="detail-label">Average Score</div><div class="detail-value" style="font-size:22px; font-weight:800">${Math.round(metrics.avg_score||0)}/100</div></div>
        <div class="detail-item"><div class="detail-label">Emails Sent</div><div class="detail-value" style="font-size:22px; font-weight:800; color:var(--cyan-400)">${metrics.emails_sent||0}</div></div>
      </div>
    </div>
  `;

  window.downloadExcel = () => {
    toast('Generating Excel report...', 'info');
    window.location.href = '/api/export/excel';
  };

  window.downloadCSV = () => {
    toast('Generating CSV...', 'info');
    window.location.href = '/api/export/csv';
  };
}

