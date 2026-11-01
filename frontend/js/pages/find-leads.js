import { api } from '../api.js';
import { toast } from '../app.js';

export function renderFindLeads(container) {
  container.innerHTML = `
    <div class="search-hero">
      <h2>&#128269; AI-Powered Lead Discovery</h2>
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
          <label class="form-label">Provider</label>
          <select class="form-control" id="searchProvider">
            <option value="google_maps">&#127757; Google Maps (Browser)</option>
            <option value="auto">Auto (Google API &rarr; OSM Fallback)</option>
            <option value="osm">OpenStreetMap (Free)</option>
            <option value="google">Google Places API</option>
          </select>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">Max Results</label>
          <input class="form-control" id="searchMax" type="number" value="20" min="5" max="100" />
        </div>
        <div class="form-group" style="margin:0; justify-content:flex-end">
          <label class="form-label">&nbsp;</label>
          <button class="btn btn-primary btn-lg" id="searchBtn" onclick="startSearch()">
            &#128640; Find Leads
          </button>
        </div>
      </div>

      <!-- Google Maps Browser Info Banner -->
      <div id="gmapsBanner" class="gmaps-banner" style="margin-top:14px">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px">
          <span style="font-size:20px">&#127760;</span>
          <strong style="color:var(--cyan-400)">Google Maps Browser Mode</strong>
          <span class="badge-live">LIVE</span>
        </div>
        <p style="margin:0; font-size:12px; color:var(--text-secondary)">
          The AI agent will open a Chrome browser, navigate to Google Maps, search for businesses,
          scroll through results, and extract lead data automatically. <strong>No API key needed!</strong>
          You can watch the browser in real-time.
        </p>
      </div>

      <div style="font-size:12px; color:var(--text-muted); margin-top:10px; display:flex; align-items:center; gap:6px; flex-wrap:wrap">
        <span>&#128506;&#65039; Discovery: Google Maps Browser, Google Places API &amp; OpenStreetMap Overpass.</span>
        <span>Map data &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" style="color:var(--blue-400)">OpenStreetMap contributors</a> (ODbL).</span>
      </div>
    </div>

    <div id="progressPanel" style="display:none">
      <div class="progress-panel">
        <div class="progress-header">
          <span class="progress-title" id="progressTitle">&#129302; AI Agents Running...</span>
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
        <div id="resultEmoji" style="font-size:48px; margin-bottom:12px">&#9989;</div>
        <div id="resultTitle" style="font-size:22px; font-weight:700; margin-bottom:8px">Search Complete!</div>
        <div id="resultSub" style="color:var(--text-muted); margin-bottom:20px"></div>
        <button class="btn btn-primary" onclick="router.navigate('leads')">View Leads &rarr;</button>
      </div>
    </div>

    <div class="card" style="margin-top:24px">
      <div class="section-title" style="margin-bottom:16px">&#129302; How It Works</div>
      <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px,1fr)); gap:16px">
        ${[
          ['\u{1F3AF}','Search Planning','Analyzes your query and optimizes search parameters'],
          ['\u{1F4CD}','Business Discovery','Finds businesses via Google Maps, Places API, or OSM'],
          ['\u{1F310}','Website Verification','Checks if each business has a live website'],
          ['\u{1F50E}','Business Enrichment','Extracts contact info, social links, details'],
          ['\u2B50','Lead Scoring','Scores 0\u2013100 based on 15+ quality signals'],
          ['\u{1F9F9}','Data Quality','Deduplicates and validates all records'],
          ['\u{1F4CA}','Excel Report','Generates formatted multi-sheet Excel workbook'],
          ['\u270D\uFE0F','Outreach Personalization','Writes personalized email drafts per lead'],
          ['\u{1F4E7}','Email Delivery','Sends approved emails with daily cap & suppression'],
          ['\u{1F4BC}','CRM Update','Updates pipeline status and contact history'],
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

  // Toggle banner visibility based on provider selection
  const providerSelect = document.getElementById('searchProvider');
  const banner = document.getElementById('gmapsBanner');

  function updateBanner() {
    if (providerSelect.value === 'google_maps') {
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
  }
  providerSelect.addEventListener('change', updateBanner);
  updateBanner();

  window.startSearch = async () => {
    const query    = document.getElementById('searchQuery').value.trim();
    const location = document.getElementById('searchLocation').value.trim();
    const provider = document.getElementById('searchProvider').value;
    const maxR     = parseInt(document.getElementById('searchMax').value) || 20;

    if (!query || !location) {
      toast('Please enter business type and location', 'error');
      return;
    }

    const searchBtn = document.getElementById('searchBtn');
    searchBtn.disabled = true;
    searchBtn.innerHTML = '&#9203; Searching...';
    document.getElementById('progressPanel').style.display = 'block';
    document.getElementById('searchResult').style.display = 'none';
    document.getElementById('progressLog').innerHTML = '';

    // Update progress title based on provider
    const titleEl = document.getElementById('progressTitle');
    if (provider === 'google_maps') {
      titleEl.innerHTML = '&#127760; Google Maps Browser Agent Running...';
    } else {
      titleEl.innerHTML = '&#129302; AI Agents Running...';
    }

    try {
      if (provider === 'google_maps') {
        // Use the Google Maps browser scraper endpoint
        const { job_id } = await api.post('/api/scrape/google-maps', {
          query,
          location,
          max_results: maxR,
          headless: false
        });
        pollScrapeProgress(job_id);
      } else {
        // Use the regular AI pipeline
        const { job_id } = await api.post('/api/search', {
          query,
          location,
          radius_km: 10,
          max_results: maxR,
          provider
        });
        pollJobProgress(job_id);
      }
    } catch (err) {
      toast(`Search failed: ${err.message}`, 'error');
      searchBtn.disabled = false;
      searchBtn.innerHTML = '&#128640; Find Leads';
    }
  };

  function pollScrapeProgress(jobId) {
    const logEl  = document.getElementById('progressLog');
    const fillEl = document.getElementById('progressFill');
    const pctEl  = document.getElementById('progressPct');

    api.streamSSE(
      `/api/scrape/${jobId}/stream`,
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
          searchBtn.innerHTML = '&#128640; Find Leads';
        }

        const result = document.getElementById('searchResult');
        if (result) {
          result.style.display = 'block';

          if (done.status === 'done') {
            const r = done.result || {};
            document.getElementById('resultEmoji').textContent = '\u2705';
            document.getElementById('resultTitle').textContent = 'Google Maps Scraping Complete!';
            document.getElementById('resultSub').textContent =
              `Found ${r.leads_found || 0} businesses, saved ${r.leads_saved || 0} leads to database.`;
            toast('Google Maps scraping complete!', 'success');
          } else {
            document.getElementById('resultEmoji').textContent = '\u274C';
            document.getElementById('resultTitle').textContent = 'Scraping Failed';
            document.getElementById('resultSub').textContent = done.error || 'Unknown error occurred.';
            toast('Scraping encountered an error', 'error');
          }
        }
      }
    );
  }

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
          searchBtn.innerHTML = '&#128640; Find Leads';
        }

        const result = document.getElementById('searchResult');
        if (result) {
          result.style.display = 'block';

          if (done.status === 'done') {
            document.getElementById('resultEmoji').textContent = '\u2705';
            document.getElementById('resultTitle').textContent = 'Search Complete!';
            document.getElementById('resultSub').textContent =
              'Pipeline finished successfully. Check Lead Database for newly qualified leads.';
            toast('Lead discovery complete!', 'success');
          } else {
            document.getElementById('resultEmoji').textContent = '\u274C';
            document.getElementById('resultTitle').textContent = 'Search Failed';
            document.getElementById('resultSub').textContent = done.error || 'Unknown error occurred.';
            toast('Search encountered an error', 'error');
          }
        }
      }
    );
  }
}
