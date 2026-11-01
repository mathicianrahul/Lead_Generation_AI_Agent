import { api } from '../api.js';
import { toast } from '../app.js';

export async function renderOutreach(container) {
  container.innerHTML = `
    <div class="tabs">
      <button class="tab-btn active" onclick="loadDrafts('pending', this)">⏳ Pending Approval</button>
      <button class="tab-btn" onclick="loadDrafts('approved', this)">✅ Approved</button>
      <button class="tab-btn" onclick="loadDrafts('rejected', this)">❌ Rejected</button>
      <button class="tab-btn" onclick="loadDrafts('sent', this)">📤 Sent</button>
    </div>
    <div id="draftsPanel"></div>
  `;

  window.loadDrafts = async (status, btn) => {
    if (btn) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
    const panel = document.getElementById('draftsPanel');
    if (panel) panel.innerHTML = '<div class="spinner"></div>';

    try {
      const { drafts } = await api.get(`/api/drafts${status ? `?status=${status}` : ''}`);
      renderDrafts(drafts || [], status);
    } catch (err) {
      if (panel) {
        panel.innerHTML = `<div class="table-empty"><div class="table-empty-icon">⚠️</div><div class="table-empty-text">${err.message}</div></div>`;
      }
    }
  };

  window.approveDraft = async (id) => {
    try {
      await api.post(`/api/drafts/${id}/approve`, {});
      toast('Draft approved! Ready for safe sending.', 'success');
      window.loadDrafts('pending');
    } catch (err) { toast(err.message, 'error'); }
  };

  window.rejectDraft = async (id) => {
    try {
      await api.post(`/api/drafts/${id}/reject`, {});
      toast('Draft rejected.', 'info');
      window.loadDrafts('pending');
    } catch (err) { toast(err.message, 'error'); }
  };

  window.loadDrafts('pending');
}

function renderDrafts(drafts, status) {
  const panel = document.getElementById('draftsPanel');
  if (!panel) return;
  if (!drafts.length) {
    panel.innerHTML = `<div class="table-empty" style="padding:60px 20px">
      <div class="table-empty-icon">📭</div>
      <div class="table-empty-text">No ${status || ''} drafts found</div>
      <div class="table-empty-sub">Run a lead search to generate personalized email outreach drafts.</div>
    </div>`;
    return;
  }

  panel.innerHTML = drafts.map(d => `
    <div class="draft-card">
      <div class="draft-header">
        <div>
          <div class="draft-recipient">📧 ${d.recipient_name || ('Lead #' + d.lead_id)} <span style="font-size:12px; color:var(--text-muted); font-weight:normal">(${d.recipient_email || 'No email'})</span></div>
          <div class="draft-subject">${d.subject || '(no subject)'}</div>
        </div>
        <div style="display:flex; gap:8px; flex-shrink:0">
          ${d.status === 'pending' || d.status === 'draft_ready' ? `
            <button class="btn btn-success btn-sm" onclick="approveDraft(${d.id})">✅ Approve</button>
            <button class="btn btn-danger btn-sm" onclick="rejectDraft(${d.id})">❌ Reject</button>
          ` : `<span class="badge ${d.status==='approved'?'badge-green':d.status==='sent'?'badge-cyan':'badge-red'}">${d.status}</span>`}
        </div>
      </div>
      <div class="draft-preview">${(d.body || '').substring(0, 300)}${d.body && d.body.length > 300 ? '...' : ''}</div>
    </div>
  `).join('');
}

