import { api } from '../api.js';

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="stats-grid" id="statsGrid">
      ${[1,2,3,4,5].map(() => `<div class="stat-card" style="animation: pulse 1.5s infinite"><div class="spinner" style="margin:0;width:24px;height:24px"></div></div>`).join('')}
    </div>
    <div class="charts-grid">
      <div class="chart-card">
        <div class="chart-title">🌐 Website Status</div>
        <div class="chart-wrap"><canvas id="websiteChart"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">📊 Score Distribution</div>
        <div class="chart-wrap"><canvas id="scoreChart"></canvas></div>
      </div>
    </div>
    <div class="chart-card">
      <div class="chart-title">💼 CRM Pipeline</div>
      <div class="chart-wrap" style="height:160px"><canvas id="crmChart"></canvas></div>
    </div>
  `;

  // Load data in parallel
  const [metrics, websiteData, scoreData, crmData] = await Promise.allSettled([
    api.get('/api/metrics'),
    api.get('/api/charts/website-status'),
    api.get('/api/charts/score-distribution'),
    api.get('/api/charts/crm-pipeline'),
  ]);

  const m = metrics.value || {};
  renderStats(m);
  if (websiteData.value)  renderWebsiteChart(websiteData.value);
  if (scoreData.value)    renderScoreChart(scoreData.value);
  if (crmData.value)      renderCrmChart(crmData.value);
}

function renderStats(m) {
  const grid = document.getElementById('statsGrid');
  if (!grid) return;
  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-icon blue">👥</div>
      <div class="stat-info">
        <div class="stat-label">Total Leads</div>
        <div class="stat-value">${m.total_leads ?? 0}</div>
        <div class="stat-sub">In database</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon green">✅</div>
      <div class="stat-info">
        <div class="stat-label">Verified</div>
        <div class="stat-value">${m.verified_leads ?? 0}</div>
        <div class="stat-sub">Website confirmed</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon purple">⭐</div>
      <div class="stat-info">
        <div class="stat-label">High Score</div>
        <div class="stat-value">${m.high_score_leads ?? 0}</div>
        <div class="stat-sub">Score ≥ 70</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon orange">📧</div>
      <div class="stat-info">
        <div class="stat-label">Emails Sent</div>
        <div class="stat-value">${m.emails_sent ?? 0}</div>
        <div class="stat-sub">This session</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon cyan">📈</div>
      <div class="stat-info">
        <div class="stat-label">Avg Score</div>
        <div class="stat-value">${Math.round(m.avg_score ?? 0)}</div>
        <div class="stat-sub">Lead quality</div>
      </div>
    </div>
  `;
}

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94A3B8', font: { family: 'Inter', size: 12 } } },
    },
  };
}

function renderWebsiteChart(data) {
  const ctx = document.getElementById('websiteChart');
  if (!ctx || typeof Chart === 'undefined') return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Has Website', 'No Website', 'Unknown'],
      datasets: [{
        data: [data.has_website || 0, data.no_website || 0, data.unknown || 0],
        backgroundColor: ['#10B981', '#F87171', '#6B7280'],
        borderColor: '#1A2235',
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      ...chartDefaults(),
      cutout: '65%',
      plugins: {
        ...chartDefaults().plugins,
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} leads`,
          }
        }
      },
    },
  });
}

function renderScoreChart(data) {
  const ctx = document.getElementById('scoreChart');
  if (!ctx || typeof Chart === 'undefined') return;
  const buckets = data.buckets || ['0-20','21-40','41-60','61-80','81-100'];
  const counts  = data.counts  || [0,0,0,0,0];
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: buckets,
      datasets: [{
        label: 'Leads',
        data: counts,
        backgroundColor: ['#F87171','#FB923C','#FBBF24','#34D399','#3B82F6'],
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      ...chartDefaults(),
      scales: {
        x: { ticks: { color: '#64748B' }, grid: { color: 'rgba(30,58,95,0.3)' } },
        y: { ticks: { color: '#64748B' }, grid: { color: 'rgba(30,58,95,0.3)' }, beginAtZero: true },
      },
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  });
}

function renderCrmChart(data) {
  const ctx = document.getElementById('crmChart');
  if (!ctx || typeof Chart === 'undefined') return;
  const labels = ['New', 'Contacted', 'Qualified', 'Proposal', 'Closed'];
  const values = [data.new||0, data.contacted||0, data.qualified||0, data.proposal||0, data.closed||0];
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Leads',
        data: values,
        backgroundColor: 'rgba(59,130,246,0.7)',
        borderColor: '#3B82F6',
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      ...chartDefaults(),
      indexAxis: 'y',
      scales: {
        x: { ticks: { color: '#64748B' }, grid: { color: 'rgba(30,58,95,0.3)' }, beginAtZero: true },
        y: { ticks: { color: '#94A3B8' }, grid: { display: false } },
      },
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  });
}

