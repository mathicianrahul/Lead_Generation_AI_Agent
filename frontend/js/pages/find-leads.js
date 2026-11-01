import { api } from '../api.js';
import { toast } from '../app.js';

export function renderFindLeads(container) {
  container.innerHTML = `
    <div class="search-hero">
      <h2>🔍 AI-Powered Lead Discovery</h2>
      <p>Find businesses without websites — your potential clients. Powered by 10 specialized AI agents.</p>
      <div class="search-grid">
        <div class="form-group" style="margin:0">
          <label class="form-label">Business Type / Niche</label>
          <input class="form-control" id="searchQuery" placeholder="e.g. Dental Clinic, Cafe, Real Estate..." />
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">Location</label>
          <input class="form-control" id="searchLocation" placeholder="e.g. Mumbai, Delhi, Bengaluru..." />
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">Radius (km)</label>
          <input class="form-control" id="searchRadius" type="number" value="10" min="1" max="100" />
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">Max Results</label>
          <input class="form-control" id="searchMax" type="number" value="20" min="5" max="100" />
        </div>
        <div class="form-group" style="margin:0; justify-content:flex-end">
          <label class="form-label">&nbsp;</label>
          <button class="btn btn-primary btn-lg" id="searchBtn" onclick="startSearch()">
            🚀 Find Leads
          </button>
        </div>
      </div>
    </div>

    <div id="progressPanel" style="display:none">
      <div class="progress-panel">
        <div class="progress-header">
          <span class="progress-title">🤖 AI Agents Running...</span>
          <span class="progress-pct" id="progressPct">0%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" id="progressFill" style="width:0%"></div>
        </div>
        <div class="progress-log" id="progressLog"></div>
      </div>
    </div>

    <div id="searchResult" style="display:none">
      <div class="card" style="text-align:center; padding:32px">
        <div id="resultEmoji" style="font-size:48px; margin-bottom:12px">✅</div>
        <div id="resultTitle" style="font-size:22px; font-weight:700; margin-bottom:8px">Search Complete!</div>
        <div id="resultSub" style="color:var(--text-muted); margin-bottom:20px"></div>
        <button class="btn btn-primary" onclick="router.navigate('leads')">View Leads →</button>
      </div>
    </div>

    <div class="card" style="margin-top:24px">
      <div class="section-title" style="margin-bottom:16px">🤖 How It Works</div>
      <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px,1fr)); gap:16px">
        ${[
          ['🎯','Search Planning','Analyzes your query and optimizes search parameters'],
          ['📍','Business Discovery','Finds businesses via Google Places + demo data'],
          ['🌐','Website Verification','Checks if each business has a live website'],
          ['🔎','Business Enrichment','Extracts contact info, social links, details'],
          ['⭐','Lead Scoring','Scores 0–100 based on 15+ quality signals'],
          ['🧹','Data Quality','Deduplicates and validates all records'],
          ['📊','Excel Report','Generates formatted multi-sheet Excel workbook'],
          ['✍️','Outreach Personalization','Writes personalized email drafts per lead'],
          ['📧','Email Delivery','Sends approved emails with daily cap & suppression'],
          ['💼','CRM Update','Updates pipeline status and contact history'],
        ].map(([icon, name, desc]) => `
          <div style="background:var(--bg-primary); border:1px solid var(--border); border-radius:8px; padding:14px">
            <div style="font-size:22px; margin-bottom:8px">${icon}</div>
            <div style="font-size:13px; font-weight:700; margin-bottom:4px">${name}</div>
            <div style="font-size:11px; color:var(--text-muted)">${desc}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  window.startSearch = async () => {
    const query    = document.getElementById('searchQuery').value.trim();
    const location = document.getElementById('searchLocation').value.trim();
    const radius   = parseInt(document.getElementById('searchRadius').value) || 10;
    const maxR     = parseInt(document.getElementById('searchMax').value) || 20;

    if (!query || !location) {
      toast('Please enter business type and location', 'error');
      return;
    }

    const searchBtn = document.getElementById('searchBtn');
    searchBtn.disabled = true;
    searchBtn.textContent = '⏳ Searching...';
    document.getElementById('progressPanel').style.display = 'block';
    document.getElementById('searchResult').style.display = 'none';

    try {
      const { job_id } = await api.post('/api/search', { query, location, radius_km: radius, max_results: maxR });
      pollJobProgress(job_id);
    } catch (err) {
      toast(`Search failed: ${err.message}`, 'error');
      searchBtn.disabled = false;
      searchBtn.textContent = '🚀 Find Leads';
    }
  };

  function pollJobProgress(jobId) {
    const logEl  = document.getElementById('progressLog');
    const fillEl = document.getElementById('progressFill');
    const pctEl  = document.getElementById('progressPct');

    api.streamSSE(
      `/api/search/${jobId}/stream`,
      (data) => {
        if (data.progress !== undefined) {
          fillEl.style.width = data.progress + '%';
          pctEl.textContent  = data.progress + '%';
        }
        if (data.message) {
          const div = document.createElement('div');
          div.className = 'log-entry';
          div.textContent = data.message;
          logEl.appendChild(div);
          logEl.scrollTop = logEl.scrollHeight;
        }
      },
      (done) => {
        const searchBtn = document.getElementById('searchBtn');
        if (searchBtn) {
          searchBtn.disabled = false;
          searchBtn.textContent = '🚀 Find Leads';
        }

        const result = document.getElementById('searchResult');
        if (result) {
          result.style.display = 'block';

          if (done.status === 'done') {
            document.getElementById('resultEmoji').textContent = '✅';
            document.getElementById('resultTitle').textContent = 'Search Complete!';
            document.getElementById('resultSub').textContent = `Pipeline finished successfully. Check Lead Database for newly qualified leads.`;
            toast('Lead discovery complete!', 'success');
          } else {
            document.getElementById('resultEmoji').textContent = '❌';
            document.getElementById('resultTitle').textContent = 'Search Failed';
            document.getElementById('resultSub').textContent = done.error || 'Unknown error occurred.';
            toast('Search encountered an error', 'error');
          }
        }
      }
    );
  }
}

