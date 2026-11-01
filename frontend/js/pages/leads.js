import { api } from '../api.js';
import { toast, openModal, closeModal } from '../app.js';

let state = { page: 1, per_page: 50, q: '', crm_status: '', min_score: 0, sort_by: 'score', sort_dir: 'desc' };

export async function renderLeads(container) {
  container.innerHTML = `
    <div class="table-container">
      <div class="table-header">
        <span class="table-title">👥 Lead Database</span>
        <div class="table-actions filter-bar">
          <div class="search-input-wrap">
            <input class="form-control" id="leadSearch" placeholder="Search leads..." value="${state.q}" />
          </div>
          <select class="form-control" id="crmFilter">
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="proposal">Proposal</option>
            <option value="closed">Closed</option>
            <option value="lost">Lost</option>
          </select>
          <select class="form-control" id="scoreFilter">
            <option value="0">Any Score</option>
            <option value="70">Score ≥ 70</option>
            <option value="50">Score ≥ 50</option>
            <option value="30">Score ≥ 30</option>
          </select>
          <button class="btn btn-secondary btn-sm" onclick="applyFilters()">Apply</button>
          <button class="btn btn-secondary btn-sm" onclick="resetFilters()">Reset</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th onclick="sortBy('business_name')">Business ↕</th>
              <th>Category</th>
              <th onclick="sortBy('score')">Score ↕</th>
              <th>Website</th>
              <th>Phone</th>
              <th>Rating</th>
              <th>CRM Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="leadsBody">
            <tr><td colspan="8" class="table-empty">
              <div class="spinner"></div>
              <div class="loading-text">Loading leads...</div>
            </td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination" id="pagination"></div>
    </div>
  `;

  // Bind filter events
  document.getElementById('leadSearch').addEventListener('keydown', e => {
    if (e.key === 'Enter') applyFilters();
  });

  window.applyFilters = () => {
    state.q           = document.getElementById('leadSearch').value;
    state.crm_status  = document.getElementById('crmFilter').value;
    state.min_score   = parseInt(document.getElementById('scoreFilter').value) || 0;
    state.page        = 1;
    loadLeads();
  };

  window.resetFilters = () => {
    state = { page: 1, per_page: 50, q: '', crm_status: '', min_score: 0, sort_by: 'score', sort_dir: 'desc' };
    document.getElementById('leadSearch').value  = '';
    document.getElementById('crmFilter').value   = '';
    document.getElementById('scoreFilter').value = '0';
    loadLeads();
  };

  window.sortBy = (col) => {
    if (state.sort_by === col) state.sort_dir = state.sort_dir === 'asc' ? 'desc' : 'asc';
    else { state.sort_by = col; state.sort_dir = 'desc'; }
    loadLeads();
  };

  window.goPage = (p) => { state.page = p; loadLeads(); };

  window.viewLead  = async (id) => showLeadModal(id);
  window.editLead  = async (id) => showEditModal(id);

  loadLeads();
}

async function loadLeads() {
  const params = new URLSearchParams({
    page:       state.page,
    per_page:   state.per_page,
    q:          state.q,
    min_score:  state.min_score,
    sort_by:    state.sort_by,
    sort_dir:   state.sort_dir,
  });
  if (state.crm_status) params.set('crm_status', state.crm_status);

  try {
    const data = await api.get(`/api/leads?${params}`);
    renderTable(data.leads || []);
    renderPagination(data.page, data.pages, data.total);
  } catch (err) {
    const tbody = document.getElementById('leadsBody');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="table-empty"><div class="table-empty-icon">⚠️</div><div class="table-empty-text">Error loading leads</div><div class="table-empty-sub">${err.message}</div></td></tr>`;
    }
  }
}

function scoreClass(s) {
  if (s >= 70) return 'high';
  if (s >= 40) return 'medium';
  return 'low';
}

function crmBadge(status) {
  const map = {
    new: 'badge-blue', contacted: 'badge-cyan', qualified: 'badge-green',
    proposal: 'badge-purple', closed: 'badge-green', lost: 'badge-red',
  };
  return `<span class="badge ${map[status] || 'badge-gray'}">${status || 'new'}</span>`;
}

function renderTable(leads) {
  const tbody = document.getElementById('leadsBody');
  if (!tbody) return;
  if (!leads.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty">
      <div class="table-empty-icon">📭</div>
      <div class="table-empty-text">No leads found</div>
      <div class="table-empty-sub">Run a search to discover leads, or adjust your filters.</div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = leads.map(l => {
    const sc = l.score || 0;
    const cls = scoreClass(sc);
    const websiteBadge = l.has_website
      ? `<span class="badge badge-green">✅ Yes</span>`
      : `<span class="badge badge-red">❌ No</span>`;
    const isDemo = l.is_demo ? ' <span class="badge badge-yellow" style="font-size:10px">DEMO</span>' : '';

    return `<tr>
      <td>
        <div style="font-weight:600; color:var(--text-primary)">${l.business_name || '—'}${isDemo}</div>
        <div style="font-size:11px; color:var(--text-muted)">${l.address || ''}</div>
      </td>
      <td><span class="badge badge-blue">${l.category || 'Business'}</span></td>
      <td>
        <div class="score-bar">
          <div class="score-bar-track">
            <div class="score-bar-fill ${cls}" style="width:${sc}%"></div>
          </div>
          <span class="score-val" style="color:${cls==='high'?'var(--green-400)':cls==='medium'?'var(--yellow-400)':'var(--red-400)'}">${sc}</span>
        </div>
      </td>
      <td>${websiteBadge}</td>
      <td style="font-size:13px">${l.phone || '<span style="color:var(--text-muted)">—</span>'}</td>
      <td style="font-size:13px">${l.rating ? `⭐ ${l.rating} (${l.review_count||0})` : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td>${crmBadge(l.crm_status)}</td>
      <td>
        <div style="display:flex; gap:6px">
          <button class="btn btn-secondary btn-sm" onclick="viewLead(${l.id})">View</button>
          <button class="btn btn-secondary btn-sm" onclick="editLead(${l.id})">Edit</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function renderPagination(page, pages, total) {
  const el = document.getElementById('pagination');
  if (!el) return;

  const start = Math.max(1, page - 2);
  const end   = Math.min(pages, page + 2);
  let btns = '';
  for (let i = start; i <= end; i++) {
    btns += `<button class="page-btn ${i===page?'active':''}" onclick="goPage(${i})">${i}</button>`;
  }

  el.innerHTML = `
    <span class="pagination-info">Showing ${Math.min((page-1)*state.per_page+1, total)}–${Math.min(page*state.per_page, total)} of ${total} leads</span>
    <div class="pagination-controls">
      <button class="page-btn" onclick="goPage(1)" ${page<=1?'disabled':''}>«</button>
      <button class="page-btn" onclick="goPage(${page-1})" ${page<=1?'disabled':''}>‹</button>
      ${btns}
      <button class="page-btn" onclick="goPage(${page+1})" ${page>=pages?'disabled':''}>›</button>
      <button class="page-btn" onclick="goPage(${pages})" ${page>=pages?'disabled':''}>»</button>
    </div>
  `;
}

async function showLeadModal(id) {
  try {
    const l = await api.get(`/api/leads/${id}`);
    openModal(`
      <div class="modal-title">${l.business_name}</div>
      <div class="detail-grid" style="margin-bottom:20px">
        <div class="detail-item"><div class="detail-label">Category</div><div class="detail-value">${l.category||'—'}</div></div>
        <div class="detail-item"><div class="detail-label">Score</div><div class="detail-value">${l.score||0}/100</div></div>
        <div class="detail-item"><div class="detail-label">Phone</div><div class="detail-value">${l.phone||'—'}</div></div>
        <div class="detail-item"><div class="detail-label">Website</div><div class="detail-value">${l.website ? `<a href="${l.website}" target="_blank" style="color:var(--blue-400)">${l.website}</a>` : '—'}</div></div>
        <div class="detail-item"><div class="detail-label">Address</div><div class="detail-value">${l.address||'—'}</div></div>
        <div class="detail-item"><div class="detail-label">Rating</div><div class="detail-value">${l.rating ? `⭐ ${l.rating} (${l.review_count||0} reviews)` : '—'}</div></div>
        <div class="detail-item"><div class="detail-label">CRM Status</div><div class="detail-value">${l.crm_status||'new'}</div></div>
        <div class="detail-item"><div class="detail-label">Deal Value</div><div class="detail-value">${l.deal_value ? `₹${l.deal_value.toLocaleString()}` : '—'}</div></div>
      </div>
      ${l.notes ? `<div class="detail-item"><div class="detail-label">Notes</div><div class="detail-value" style="margin-top:4px">${l.notes}</div></div>` : ''}
      <div style="margin-top:20px; display:flex; gap:8px; justify-content:flex-end">
        <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        <button class="btn btn-primary" onclick="closeModal(); editLead(${l.id})">Edit</button>
      </div>
    `);
  } catch (err) {
    toast(`Error loading lead: ${err.message}`, 'error');
  }
}

async function showEditModal(id) {
  try {
    const l = await api.get(`/api/leads/${id}`);
    openModal(`
      <div class="modal-title">Edit Lead: ${l.business_name}</div>
      <div class="form-group">
        <label class="form-label">CRM Status</label>
        <select class="form-control" id="editStatus">
          ${['new','contacted','qualified','proposal','closed','lost'].map(s =>
            `<option value="${s}" ${l.crm_status===s?'selected':''}>${s.charAt(0).toUpperCase()+s.slice(1)}</option>`
          ).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Deal Value (₹)</label>
        <input class="form-control" id="editDeal" type="number" value="${l.deal_value||''}" placeholder="0" />
      </div>
      <div class="form-group">
        <label class="form-label">Notes</label>
        <textarea class="form-control" id="editNotes">${l.notes||''}</textarea>
      </div>
      <div style="display:flex; gap:8px; justify-content:flex-end">
        <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveLead(${id})">Save Changes</button>
      </div>
    `);

    window.saveLead = async (leadId) => {
      try {
        await api.put(`/api/leads/${leadId}`, {
          crm_status: document.getElementById('editStatus').value,
          deal_value: parseFloat(document.getElementById('editDeal').value) || null,
          notes:      document.getElementById('editNotes').value,
        });
        toast('Lead updated successfully!', 'success');
        closeModal();
        loadLeads();
      } catch (err) {
        toast(`Error saving: ${err.message}`, 'error');
      }
    };
  } catch (err) {
    toast(`Error loading lead: ${err.message}`, 'error');
  }
}

