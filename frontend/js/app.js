/**
 * LeadPilot AI — SPA Router & App Shell
 */
import { api } from './api.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderFindLeads } from './pages/find-leads.js';
import { renderLeads } from './pages/leads.js';
import { renderVerification } from './pages/verification.js';
import { renderOutreach } from './pages/outreach.js';
import { renderCRM } from './pages/crm.js';
import { renderReports } from './pages/reports.js';
import { renderSettings } from './pages/settings.js';

// ─── Page registry ────────────────────────────────────────────────────────────
const PAGES = {
  dashboard:    { title: 'Dashboard',       render: renderDashboard },
  'find-leads': { title: 'Find Leads',      render: renderFindLeads },
  leads:        { title: 'Lead Database',   render: renderLeads },
  verification: { title: 'Verification Hub',render: renderVerification },
  outreach:     { title: 'Email Outreach',  render: renderOutreach },
  crm:          { title: 'CRM Pipeline',    render: renderCRM },
  reports:      { title: 'Reports',         render: renderReports },
  settings:     { title: 'Settings',        render: renderSettings },
};

// ─── Router ───────────────────────────────────────────────────────────────────
class Router {
  constructor() {
    this.current = null;
    this.container = document.getElementById('pageContainer');
    this.titleEl   = document.getElementById('pageTitle');
    window.addEventListener('hashchange', () => this._onHash());
    window.addEventListener('DOMContentLoaded', () => this._init());
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      setTimeout(() => this._init(), 0);
    }
  }

  _init() {
    if (this._initialized) return;
    this._initialized = true;
    this._bindNav();
    this._onHash();
    this._updateBadges();
    this._checkDemoMode();
    setInterval(() => this._updateBadges(), 30000);
  }

  _onHash() {
    const hash = location.hash.replace('#', '') || 'dashboard';
    this.navigate(hash);
  }

  navigate(page) {
    if (!PAGES[page]) page = 'dashboard';
    if (this.current === page && this.container.children.length > 0) return;
    this.current = page;

    // Update hash without triggering hashchange
    history.replaceState(null, '', `#${page}`);

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.page === page);
    });

    // Update page title
    if (this.titleEl) {
      this.titleEl.textContent = PAGES[page].title;
    }

    // Render page
    this.container.innerHTML = '<div class="spinner"></div>';
    Promise.resolve(PAGES[page].render(this.container)).catch(err => {
      this.container.innerHTML = `<div class="table-empty"><div class="table-empty-icon">⚠️</div><div class="table-empty-text">Error loading page</div><div class="table-empty-sub">${err.message}</div></div>`;
    });
  }

  _bindNav() {
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        const page = el.dataset.page;
        if (page) this.navigate(page);
      });
    });

    // Mobile sidebar toggle
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
      toggle.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
      });
    }
  }

  async _updateBadges() {
    try {
      const metrics = await api.get('/api/metrics');
      const el = document.getElementById('leadsCount');
      if (el) el.textContent = metrics.total_leads || 0;
    } catch {}
    try {
      const { drafts } = await api.get('/api/drafts?status=pending');
      const el = document.getElementById('draftsCount');
      if (el) {
        el.textContent = drafts.length;
        el.style.display = drafts.length ? '' : 'none';
      }
    } catch {}
  }

  async _checkDemoMode() {
    try {
      const cfg = await api.get('/api/settings');
      const badge = document.getElementById('demoBadge');
      if (badge) badge.style.display = cfg.demo_mode ? 'flex' : 'none';
    } catch {}
  }
}

// ─── Toast helper ─────────────────────────────────────────────────────────────
export function toast(msg, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || '💡'}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ─── Modal helpers ────────────────────────────────────────────────────────────
export function openModal(html) {
  const content = document.getElementById('modalContent');
  const overlay = document.getElementById('modalOverlay');
  if (content && overlay) {
    content.innerHTML = html;
    overlay.style.display = 'flex';
  }
}

export function closeModal() {
  const overlay = document.getElementById('modalOverlay');
  if (overlay) {
    overlay.style.display = 'none';
  }
}

// Close modal on overlay click
document.getElementById('modalOverlay')?.addEventListener('click', e => {
  if (e.target === document.getElementById('modalOverlay')) closeModal();
});

// Make router and helpers global
export const router = new Router();
window.router = router;
window.closeModal = closeModal;
window.toast = toast;
window.openModal = openModal;

