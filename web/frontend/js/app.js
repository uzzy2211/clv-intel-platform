/**
 * app.js — SPA Router & Application Shell
 *
 * Split-theme: dark sidebar (Neural Terminal) + white canvas.
 * Ingest page is the landing state. All other pages are locked
 * until a dataset is loaded (pipeline_ready = true).
 */

import { api } from './api.js';
import { showToast } from './components/toast.js';
import { renderIngest }   from './pages/ingest.js';
import { renderOverview } from './pages/overview.js';
import { renderSegments } from './pages/segments.js';
import { renderExplorer } from './pages/explorer.js';
import { renderInsights } from './pages/insights.js';
import { renderExport }   from './pages/export.js';

// ── Page registry ──────────────────────────────────────────────────────
const PAGES = {
  ingest:   { render: renderIngest,   title: 'Data Ingest',    requiresData: false },
  overview: { render: renderOverview, title: 'Overview',       requiresData: true  },
  segments: { render: renderSegments, title: 'Segments',       requiresData: true  },
  explorer: { render: renderExplorer, title: 'Explorer',       requiresData: true  },
  insights: { render: renderInsights, title: 'Model Insights', requiresData: true  },
  export:   { render: renderExport,   title: 'Export',         requiresData: true  },
};

// ── App state ──────────────────────────────────────────────────────────
let _currentPage  = null;
let _dataReady    = false;

// ── DOM refs ───────────────────────────────────────────────────────────
const pageContainer  = document.getElementById('page-container');
const breadcrumbPage = document.getElementById('breadcrumb-page');
const statusDot      = document.getElementById('status-dot');
const statusText     = document.getElementById('status-text');
const ticker         = document.getElementById('ticker');
const sidebarToggle  = document.getElementById('sidebar-toggle');
const sidebar        = document.getElementById('sidebar');
const datasetBadge   = document.getElementById('dataset-badge');
const datasetBadgeTx = document.getElementById('dataset-badge-text');

// ── Unlock nav items when data is ready ───────────────────────────────
function setNavLocked(locked) {
  ['overview','segments','explorer','insights','export'].forEach(page => {
    const el = document.getElementById(`nav-${page}`);
    if (el) el.classList.toggle('locked', locked);
  });
}

// ── Router ─────────────────────────────────────────────────────────────
async function navigate(page) {
  if (!PAGES[page]) page = 'ingest';

  // Block locked pages if no data
  if (PAGES[page].requiresData && !_dataReady) {
    showToast('Upload a dataset first to unlock this page.', 'warning', 3000);
    return;
  }

  if (_currentPage === page) return;
  _currentPage = page;

  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  // Update breadcrumb
  if (breadcrumbPage) breadcrumbPage.textContent = PAGES[page].title;

  // Update URL hash
  if (location.hash !== `#${page}`) history.replaceState(null, '', `#${page}`);

  // Show spinner
  pageContainer.innerHTML = `
    <div class="page-loading">
      <div class="loading-spinner"></div>
    </div>
  `;

  // Close sidebar on mobile
  if (window.innerWidth <= 768) sidebar.classList.remove('open');

  try {
    await PAGES[page].render(pageContainer);
  } catch (err) {
    console.error(`Page render error [${page}]:`, err);
    pageContainer.innerHTML = `
      <div class="card" style="border-left:3px solid var(--red);margin-top:24px">
        <div style="color:var(--red);font-weight:700;margin-bottom:6px">Failed to render page</div>
        <div style="color:var(--cv-text-3);font-size:0.8rem">${err.message}</div>
      </div>
    `;
  }
}

// ── Hash routing ───────────────────────────────────────────────────────
function pageFromHash() {
  const h = location.hash.replace('#', '').trim();
  return PAGES[h] ? h : 'ingest';
}

window.addEventListener('hashchange', () => navigate(pageFromHash()));

// ── Custom navigate event (from ingest page) ───────────────────────────
window.addEventListener('navigate', (e) => navigate(e.detail));

// ── Nav click handlers ─────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', e => { e.preventDefault(); navigate(el.dataset.page); });
});

// ── Sidebar toggle ─────────────────────────────────────────────────────
sidebarToggle?.addEventListener('click', () => sidebar.classList.toggle('open'));
document.addEventListener('click', e => {
  if (window.innerWidth <= 768
    && sidebar.classList.contains('open')
    && !sidebar.contains(e.target)
    && e.target !== sidebarToggle) {
    sidebar.classList.remove('open');
  }
});

// ── Health check ───────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const health = await api.health();
    _dataReady = health.pipeline_ready;

    if (_dataReady) {
      statusDot.className = 'status-dot';
      statusText.textContent = 'Pipeline ready';
      setNavLocked(false);
      if (datasetBadge) datasetBadge.style.display = 'flex';
    } else {
      statusDot.className = 'status-dot warning';
      statusText.textContent = 'Awaiting dataset';
      setNavLocked(true);
    }
  } catch (_) {
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'API offline';
    showToast('Cannot reach the backend API. Is the server running?', 'error', 8000);
  }
}

// ── Ticker ─────────────────────────────────────────────────────────────
async function updateTicker() {
  try {
    if (!_dataReady) {
      ticker.innerHTML = `
        <span class="ticker-item">Awaiting customer dataset transaction upload...</span>
        <span class="ticker-item">Drop a .csv or .xlsx file to begin</span>
        <span class="ticker-item">BG/NBD + Gamma-Gamma · K-Means Clustering</span>
        <span class="ticker-item">Awaiting customer dataset transaction upload...</span>
        <span class="ticker-item">Drop a .csv or .xlsx file to begin</span>
        <span class="ticker-item">BG/NBD + Gamma-Gamma · K-Means Clustering</span>
      `;
      return;
    }

    const [overview, status] = await Promise.all([
      api.overview().catch(() => null),
      api.pipelineStatus().catch(() => null),
    ]);

    const items = [];
    if (overview) {
      const k = overview.kpis;
      items.push(
        `CUSTOMERS: ${k.total_customers.toLocaleString()}`,
        `AVG CLV: $${k.avg_clv.toFixed(2)}`,
        `CHURN RISK: ${k.avg_churn_pct.toFixed(1)}%`,
        `SEGMENTS: ${k.num_segments}`,
        `REVENUE: $${(k.total_revenue / 1000).toFixed(0)}K`,
      );
    }
    if (status) {
      items.push(`ALGO: ${status.algorithm.toUpperCase()}`, `K: ${status.optimal_k} clusters`);
      if (status.metrics?.silhouette_score) items.push(`SILHOUETTE: ${status.metrics.silhouette_score.toFixed(3)}`);
      Object.entries(status.segment_counts || {}).forEach(([seg, cnt]) => items.push(`${seg.toUpperCase()}: ${cnt}`));
    }
    if (!items.length) items.push('CLV Intelligence · BG/NBD + Gamma-Gamma · K-Means');

    const all = [...items, ...items];
    ticker.innerHTML = all.map(t => `<span class="ticker-item live">${t}</span>`).join('');
  } catch (_) {
    ticker.innerHTML = `<span class="ticker-item">CLV Intelligence Platform · BG/NBD + Gamma-Gamma · K-Means</span>`;
  }
}

// ── Data-ready callback (called by ingest page after upload) ───────────
export function onDataReady(rows) {
  _dataReady = true;
  setNavLocked(false);
  statusDot.className = 'status-dot';
  statusText.textContent = 'Pipeline ready';
  if (datasetBadge) datasetBadge.style.display = 'flex';
  if (datasetBadgeTx) datasetBadgeTx.textContent = `${rows?.toLocaleString() ?? '?'} rows loaded`;
  updateTicker();
}

// ── Boot ───────────────────────────────────────────────────────────────
async function boot() {
  await Promise.all([checkHealth(), updateTicker()]);

  // If data already exists, go to overview; otherwise land on ingest
  const startPage = _dataReady ? pageFromHash() : 'ingest';
  navigate(startPage);

  setInterval(updateTicker, 60_000);
}

boot();
