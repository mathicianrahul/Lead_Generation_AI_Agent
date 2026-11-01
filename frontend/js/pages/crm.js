import { api } from '../api.js';

export async function renderCRM(container) {
  let data;
  try {
    data = await api.get('/api/leads?per_page=500');
  } catch {
    data = { leads: [] };
  }

  const leads = data.leads || [];
  const columns = [
    { key: 'new',       label: 'New',       color: 'var(--blue-400)' },
    { key: 'contacted', label: 'Contacted', color: 'var(--cyan-400)' },
    { key: 'qualified', label: 'Qualified', color: 'var(--green-400)' },
    { key: 'proposal',  label: 'Proposal',  color: 'var(--purple-400)' },
    { key: 'closed',    label: 'Closed ✅', color: 'var(--green-400)' },
  ];

  const grouped = {};
  columns.forEach(c => { grouped[c.key] = []; });
  leads.forEach(l => {
    const s = (l.crm_status || 'new').toLowerCase();
    if (grouped[s]) grouped[s].push(l);
    else grouped['new'].push(l);
  });

  const totalValue = leads.reduce((sum, l) => sum + (l.deal_value || 0), 0);
  const closed = grouped['closed'] || [];
  const closedValue = closed.reduce((sum, l) => sum + (l.deal_value || 0), 0);

  container.innerHTML = `
    <div class="stats-grid" style="margin-bottom:24px">
      <div class="stat-card"><div class="stat-icon blue">📋</div><div class="stat-info"><div class="stat-label">Total Leads</div><div class="stat-value">${leads.length}</div></div></div>
      <div class="stat-card"><div class="stat-icon purple">💰</div><div class="stat-info"><div class="stat-label">Pipeline Value</div><div class="stat-value">₹${(totalValue/1000).toFixed(0)}k</div></div></div>
      <div class="stat-card"><div class="stat-icon green">🤝</div><div class="stat-info"><div class="stat-label">Closed Deals</div><div class="stat-value">${closed.length}</div><div class="stat-sub">₹${(closedValue/1000).toFixed(0)}k won</div></div></div>
    </div>
    <div class="kanban-board">
      ${columns.map(col => `
        <div class="kanban-col">
          <div class="kanban-col-header">
            <span class="kanban-col-title" style="color:${col.color}">${col.label}</span>
            <span class="kanban-count">${grouped[col.key].length}</span>
          </div>
          ${grouped[col.key].length
            ? grouped[col.key].map(l => `
              <div class="kanban-card" onclick="router.navigate('leads')">
                <div class="kanban-card-name">${l.business_name}</div>
                <div class="kanban-card-sub">Score: ${l.score||0} • ${l.category||'Business'}</div>
                ${l.deal_value ? `<div class="kanban-card-sub" style="color:var(--green-400); margin-top:4px">₹${l.deal_value.toLocaleString()}</div>` : ''}
              </div>
            `).join('')
            : `<div style="color:var(--text-muted); font-size:12px; text-align:center; padding:20px">No leads</div>`
          }
        </div>
      `).join('')}
    </div>
  `;
}

