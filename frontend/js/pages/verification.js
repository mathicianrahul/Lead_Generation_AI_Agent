import { api } from '../api.js';

export async function renderVerification(container) {
  let data;
  try {
    data = await api.get('/api/leads?per_page=200&sort_by=score&sort_dir=desc');
  } catch {
    data = { leads: [] };
  }

  const leads = data.leads || [];
  const withSite    = leads.filter(l => l.has_website === true);
  const withoutSite = leads.filter(l => !l.has_website);

  container.innerHTML = `
    <div class="stats-grid" style="margin-bottom:24px">
      <div class="stat-card"><div class="stat-icon green">✅</div><div class="stat-info"><div class="stat-label">Have Website</div><div class="stat-value">${withSite.length}</div></div></div>
      <div class="stat-card"><div class="stat-icon orange">❌</div><div class="stat-info"><div class="stat-label">No Website</div><div class="stat-value">${withoutSite.length}</div><div class="stat-sub">High opportunity leads</div></div></div>
      <div class="stat-card"><div class="stat-icon blue">📊</div><div class="stat-info"><div class="stat-label">Total Verified</div><div class="stat-value">${leads.length}</div></div></div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('all', this)">All Leads (${leads.length})</button>
      <button class="tab-btn" onclick="switchTab('no-site', this)">No Website (${withoutSite.length})</button>
      <button class="tab-btn" onclick="switchTab('with-site', this)">Has Website (${withSite.length})</button>
    </div>

    <div class="table-container">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Business</th><th>Score</th><th>Website Status</th><th>URL</th><th>Phone</th>
          </tr></thead>
          <tbody id="verifyBody"></tbody>
        </table>
      </div>
    </div>
  `;

  renderVerifyTable(leads);

  window.switchTab = (tab, btn) => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const filtered = tab === 'no-site' ? withoutSite : tab === 'with-site' ? withSite : leads;
    renderVerifyTable(filtered);
  };
}

function renderVerifyTable(leads) {
  const tbody = document.getElementById('verifyBody');
  if (!tbody) return;
  if (!leads.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-empty"><div class="table-empty-icon">🔍</div><div class="table-empty-text">No leads in this category</div></td></tr>`;
    return;
  }
  tbody.innerHTML = leads.map(l => {
    const sc = l.score || 0;
    const cls = sc >= 70 ? 'high' : sc >= 40 ? 'medium' : 'low';
    const webStatus = l.has_website
      ? `<span class="badge badge-green">✅ Has Website</span>`
      : `<span class="badge badge-red">❌ No Website</span>`;
    return `<tr>
      <td><div style="font-weight:600; color:var(--text-primary)">${l.business_name}</div><div style="font-size:11px; color:var(--text-muted)">${l.category||''}</div></td>
      <td><div class="score-bar"><div class="score-bar-track"><div class="score-bar-fill ${cls}" style="width:${sc}%"></div></div><span class="score-val">${sc}</span></div></td>
      <td>${webStatus}</td>
      <td style="font-size:12px; color:var(--blue-400)">${l.website ? `<a href="${l.website}" target="_blank" style="color:inherit">${l.website.replace(/^https?:\/\//,'').substring(0,35)}</a>` : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td style="font-size:13px">${l.phone||'<span style="color:var(--text-muted)">—</span>'}</td>
    </tr>`;
  }).join('');
}

