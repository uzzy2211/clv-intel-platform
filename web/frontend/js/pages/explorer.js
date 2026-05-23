/**
 * explorer.js — Customer Explorer page (split-theme: white canvas)
 */

import { api } from '../api.js';
import { renderRadar } from '../charts.js';
import { showToast } from '../components/toast.js';

let _state = {
  page:1, pageSize:50, segment:'all', sortBy:'clv', sortDir:'desc',
  search:'', total:0, totalPages:1, maxVals:{},
};

export async function renderExplorer(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Customer Explorer</h1>
        <p class="page-subtitle">Search, filter, and inspect individual customer profiles and forecasts</p>
      </div>

      <div class="filter-bar">
        <div class="search-wrap">
          <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
          </svg>
          <input type="text" class="input search-input" id="search-input" placeholder="Search by Customer ID..." />
        </div>
        <select class="select" id="segment-filter">
          <option value="all">All Segments</option>
          <option value="Champions">Champions</option>
          <option value="Loyal Customers">Loyal Customers</option>
          <option value="At Risk">At Risk</option>
          <option value="Lost">Lost</option>
          <option value="New Customers">New Customers</option>
          <option value="Hibernating">Hibernating</option>
        </select>
        <select class="select" id="sort-select" style="min-width:170px">
          <option value="clv">Sort: CLV (High-Low)</option>
          <option value="recency">Sort: Recency</option>
          <option value="frequency">Sort: Frequency</option>
          <option value="monetary">Sort: Monetary</option>
          <option value="churn_probability">Sort: Churn Risk</option>
        </select>
        <span id="result-count" style="font-size:0.75rem;color:var(--cv-text-4);font-weight:600;margin-left:auto"></span>
      </div>

      <div class="card" id="customers-panel"><div class="skeleton skeleton-chart"></div></div>
      <div class="pagination" id="pagination"></div>
    </div>

    <div class="detail-panel-overlay" id="detail-overlay"></div>
    <div class="detail-panel" id="detail-panel">
      <button class="detail-close" id="detail-close">
        <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
        </svg>
      </button>
      <div id="detail-content">
        <p style="color:var(--cv-text-4);font-size:0.85rem">Select a customer row to view their full profile.</p>
      </div>
    </div>
  `;

  const searchInput = document.getElementById('search-input');
  const segFilter   = document.getElementById('segment-filter');
  const sortSelect  = document.getElementById('sort-select');
  const overlay     = document.getElementById('detail-overlay');
  const detailPanel = document.getElementById('detail-panel');
  const detailClose = document.getElementById('detail-close');

  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { _state.search = searchInput.value; _state.page = 1; loadCustomers(); }, 350);
  });
  segFilter.addEventListener('change',  () => { _state.segment = segFilter.value;  _state.page = 1; loadCustomers(); });
  sortSelect.addEventListener('change', () => { _state.sortBy  = sortSelect.value; _state.page = 1; loadCustomers(); });
  overlay.addEventListener('click',    closeDetail);
  detailClose.addEventListener('click', closeDetail);

  function closeDetail() {
    detailPanel.classList.remove('open');
    overlay.classList.remove('open');
  }

  // Pre-load max values for radar
  try {
    const segData = await api.segments();
    _state.maxVals = {
      recency:   Math.max(...segData.segments.map(s => s.avg_recency))   * 1.5,
      frequency: Math.max(...segData.segments.map(s => s.avg_frequency)) * 1.5,
      monetary:  Math.max(...segData.segments.map(s => s.avg_monetary))  * 1.5,
      tenure:    Math.max(...segData.segments.map(s => s.avg_tenure))    * 1.2,
      clv:       Math.max(...segData.segments.map(s => s.avg_clv))       * 2,
    };
  } catch (_) {}

  loadCustomers();

  async function loadCustomers() {
    const panel = document.getElementById('customers-panel');
    panel.innerHTML = '<div class="skeleton skeleton-chart"></div>';

    try {
      const params = { page:_state.page, page_size:_state.pageSize, sort_by:_state.sortBy, sort_dir:_state.sortDir };
      if (_state.segment !== 'all') params.segment = _state.segment;
      if (_state.search) params.search = _state.search;

      const data = await api.customers(params);
      _state.total = data.total;
      _state.totalPages = data.total_pages;

      document.getElementById('result-count').textContent =
        `${data.total.toLocaleString()} customers · page ${data.page} of ${data.total_pages}`;

      panel.innerHTML = `
        <div class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Customer ID</th><th>Segment</th><th>Recency</th><th>Frequency</th>
                <th>Monetary</th><th>Tenure</th><th>CLV (90d)</th><th>Churn Risk</th><th>Pred. Purchases</th>
              </tr>
            </thead>
            <tbody>
              ${data.customers.map(c => `
                <tr data-id="${c.customer_id}">
                  <td class="text-col mono" style="color:#00a85a">${c.customer_id}</td>
                  <td><span class="segment-badge ${segClass(c.segment)}">${c.segment}</span></td>
                  <td>${c.recency.toFixed(0)}d</td>
                  <td>${c.frequency}</td>
                  <td>$${c.monetary.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
                  <td>${c.tenure.toFixed(0)}d</td>
                  <td class="accent-col">$${c.clv.toFixed(2)}</td>
                  <td style="color:${churnColor(c.churn_probability)};font-weight:600">${(c.churn_probability*100).toFixed(1)}%</td>
                  <td>${c.predicted_purchases.toFixed(2)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      panel.querySelectorAll('tbody tr').forEach(row => {
        row.addEventListener('click', () => openDetail(parseInt(row.dataset.id)));
      });

      renderPagination();
    } catch (err) {
      showToast(`Failed to load customers: ${err.message}`, 'error');
      panel.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
    }
  }

  function renderPagination() {
    const pg = document.getElementById('pagination');
    if (_state.totalPages <= 1) { pg.innerHTML = ''; return; }

    const cur = _state.page, total = _state.totalPages;
    const pages = [1];
    if (cur > 3) pages.push('...');
    for (let i = Math.max(2, cur-1); i <= Math.min(total-1, cur+1); i++) pages.push(i);
    if (cur < total-2) pages.push('...');
    if (total > 1) pages.push(total);

    pg.innerHTML = `
      <button class="page-btn" id="pg-prev" ${cur===1?'disabled':''}>‹</button>
      ${pages.map(p => p === '...'
        ? `<span class="page-info">…</span>`
        : `<button class="page-btn ${p===cur?'active':''}" data-page="${p}">${p}</button>`
      ).join('')}
      <button class="page-btn" id="pg-next" ${cur===total?'disabled':''}>›</button>
    `;

    pg.querySelector('#pg-prev')?.addEventListener('click', () => { _state.page--; loadCustomers(); });
    pg.querySelector('#pg-next')?.addEventListener('click', () => { _state.page++; loadCustomers(); });
    pg.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => { _state.page = parseInt(btn.dataset.page); loadCustomers(); });
    });
  }

  async function openDetail(customerId) {
    const detailContent = document.getElementById('detail-content');
    detailContent.innerHTML = `<div style="display:flex;justify-content:center;padding:60px 0"><div class="loading-spinner"></div></div>`;
    detailPanel.classList.add('open');
    overlay.classList.add('open');

    try {
      const c = await api.customer(customerId);

      detailContent.innerHTML = `
        <div style="margin-bottom:22px">
          <div style="font-size:0.66rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:var(--cv-text-4);margin-bottom:6px">Customer Profile</div>
          <div style="font-size:1.55rem;font-weight:800;color:var(--cv-text);letter-spacing:-0.03em;margin-bottom:8px">#${c.customer_id}</div>
          <span class="segment-badge ${segClass(c.segment)}">${c.segment}</span>
        </div>

        <div class="stat-grid">
          <div class="stat-item">
            <div class="stat-item-label">CLV (90d)</div>
            <div class="stat-item-value" style="color:#00a85a">$${c.clv.toFixed(2)}</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Churn Risk</div>
            <div class="stat-item-value" style="color:${churnColor(c.churn_probability)}">${(c.churn_probability*100).toFixed(1)}%</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Recency</div>
            <div class="stat-item-value">${c.recency.toFixed(0)}d</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Frequency</div>
            <div class="stat-item-value">${c.frequency}</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Avg Order Value</div>
            <div class="stat-item-value">$${c.monetary.toFixed(2)}</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Tenure</div>
            <div class="stat-item-value">${c.tenure.toFixed(0)}d</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Pred. Purchases</div>
            <div class="stat-item-value">${c.predicted_purchases.toFixed(2)}</div>
          </div>
          <div class="stat-item">
            <div class="stat-item-label">Exp. Avg Profit</div>
            <div class="stat-item-value">$${c.expected_avg_profit.toFixed(2)}</div>
          </div>
        </div>

        <div class="divider"></div>

        <div style="font-size:0.66rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:var(--cv-text-4);margin-bottom:10px">RFM Radar</div>
        <div class="radar-wrap"><canvas id="radar-canvas" width="260" height="220"></canvas></div>

        <div class="divider"></div>

        <div style="font-size:0.66rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:var(--cv-text-4);margin-bottom:10px">Lifetimes Model Inputs</div>
        <div style="background:var(--cv-bg);border:1px solid var(--cv-border);border-radius:var(--radius-md);padding:14px">
          ${[
            ['frequency_lt', c.frequency_lifetimes],
            ['recency_lt',   c.recency_lifetimes + 'd'],
            ['T (age)',      c.T_lifetimes + 'd'],
            ['monetary_lt',  '$' + c.monetary_value_lifetimes.toFixed(2)],
          ].map(([k,v]) => `
            <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--cv-border);font-size:0.78rem">
              <span style="color:var(--cv-text-3);font-weight:500">${k}</span>
              <span style="color:var(--cv-text);font-weight:700;font-family:var(--font-mono)">${v}</span>
            </div>
          `).join('')}
        </div>
      `;

      const radarCanvas = document.getElementById('radar-canvas');
      if (radarCanvas && Object.keys(_state.maxVals).length > 0) {
        const { renderRadar: rr } = await import('../charts.js');
        rr(radarCanvas, c, _state.maxVals);
      }
    } catch (err) {
      detailContent.innerHTML = `<p style="color:var(--red);font-weight:600">${err.message}</p>`;
    }
  }
}

function segClass(name) {
  const m = {'Champions':'champions','Loyal Customers':'loyal','At Risk':'at-risk','Lost':'lost','New Customers':'new','Hibernating':'hibernating'};
  return m[name] || 'default';
}

function churnColor(p) {
  if (p > 0.5) return 'var(--red)';
  if (p > 0.2) return 'var(--amber)';
  return '#00a85a';
}
