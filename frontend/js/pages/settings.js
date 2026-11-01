import { api } from '../api.js';

export async function renderSettings(container) {
  let cfg = {};
  try { cfg = await api.get('/api/settings'); } catch {}

  const statusBadge = (val, okVal) => {
    const ok = val === okVal || val === 'configured';
    return ok
      ? `<span class="badge badge-green">✅ ${val}</span>`
      : `<span class="badge badge-red">❌ ${val||'not set'}</span>`;
  };

  container.innerHTML = `
    <div class="section-header" style="margin-bottom:24px">
      <div>
        <div class="section-title">⚙️ Settings & Integrations</div>
        <div class="section-sub">Configuration status for all LeadPilot AI services</div>
      </div>
    </div>

    <div class="settings-grid">
      <div class="integration-card">
        <div class="integration-icon">🗺️</div>
        <div class="integration-info">
          <div class="integration-name">Google Places API (New)</div>
          <div class="integration-desc">Primary business discovery provider</div>
          <div style="margin-top:8px">${statusBadge(cfg.google_places_api, 'configured')}</div>
          ${cfg.demo_mode ? `<div style="margin-top:6px"><span class="badge badge-yellow">DEMO MODE — Mock data fallback</span></div>` : ''}
        </div>
      </div>

      <div class="integration-card">
        <div class="integration-icon">🌍</div>
        <div class="integration-info">
          <div class="integration-name">OpenStreetMap Overpass API</div>
          <div class="integration-desc">Free open-source business discovery & fallback</div>
          <div style="margin-top:8px"><span class="badge badge-green">✅ Ready (Public Service)</span></div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:6px">Data © OpenStreetMap contributors (ODbL)</div>
        </div>
      </div>

      <div class="integration-card">
        <div class="integration-icon">🤖</div>
        <div class="integration-info">
          <div class="integration-name">OpenAI / LLM</div>
          <div class="integration-desc">Email personalization & enrichment</div>
          <div style="margin-top:8px">${statusBadge(cfg.openai_api, 'configured')}</div>
        </div>
      </div>

      <div class="integration-card">
        <div class="integration-icon">🤗</div>
        <div class="integration-info">
          <div class="integration-name">Hugging Face</div>
          <div class="integration-desc">Alternative LLM backend</div>
          <div style="margin-top:8px">${statusBadge(cfg.huggingface_api, 'configured')}</div>
        </div>
      </div>

      <div class="integration-card">
        <div class="integration-icon">📧</div>
        <div class="integration-info">
          <div class="integration-name">Gmail OAuth</div>
          <div class="integration-desc">Email delivery (human approval required)</div>
          <div style="margin-top:8px">${cfg.gmail_configured ? `<span class="badge badge-green">✅ Connected</span>` : `<span class="badge badge-yellow">⚠️ Simulation mode</span>`}</div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:24px">
      <div class="section-title" style="margin-bottom:16px">⚡ System Configuration</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Demo Mode</div><div class="detail-value">${cfg.demo_mode ? '<span class="badge badge-yellow">Active</span>' : '<span class="badge badge-green">Off</span>'}</div></div>
        <div class="detail-item"><div class="detail-label">Daily Email Cap</div><div class="detail-value">${cfg.daily_email_cap||50} emails/day</div></div>
        <div class="detail-item"><div class="detail-label">Max Search Results</div><div class="detail-value">${cfg.max_search_results||50} per query</div></div>
      </div>
    </div>

    <div class="card" style="margin-top:24px; background: rgba(37,99,235,0.05); border-color: rgba(37,99,235,0.2)">
      <div style="font-size:14px; color:var(--text-secondary); line-height:1.8">
        <strong style="color:var(--blue-400)">📋 How to configure:</strong><br>
        Edit the <code style="background:var(--bg-primary); padding:2px 6px; border-radius:4px">.env</code> file in the project root to set API keys.<br>
        • <code>GOOGLE_MAPS_API_KEY</code> — Google Places API (requires billing enabled on Google Cloud)<br>
        • <code>OPENAI_API_KEY</code> — For GPT-based email personalization<br>
        • <code>HUGGINGFACE_API_KEY</code> — Alternative free LLM backend<br>
        • <code>DEMO_MODE=true</code> — Generate labeled realistic mock data (no Google billing required)<br>
        Restart the server after editing <code>.env</code>.
      </div>
    </div>
  `;
}

