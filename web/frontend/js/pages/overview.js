/**
 * overview.js — Overview page (split-theme: white canvas)
 */

import { api } from '../api.js';
import { renderDonut, renderClvBar } from '../charts.js';
import { showToast } from '../components/toast.js';
import { animateCounter } from '../components/kpi-card.js';

const ICONS = {
  customers: `<svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/></svg>`,
  revenue:   `<svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd"/></svg>`,
  clv:       `<svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>`,
  churn:     `<svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>`,
};

const KPI_CONFIGS = [
  { label: 'Total Customers',    prefix: '',  suffix: '',  decimals: 0, sub: 'Unique active buyers',       iconClass: 'green',  kpiColor: '#00a85a' },
  { label: 'Historical Revenue', prefix: '$', suffix: '',  decimals: 0, sub: 'Sum of all invoices',        iconClass: 'violet', kpiColor: '#7c3aed' },
  { label: 'Avg Projected CLV',  prefix: '$', suffix: '',  decimals: 2, sub: 'Next 90-day projection',     iconClass: 'blue',   kpiColor: '#0ea5e9' },
  { label: 'Avg Churn Risk',     prefix: '',  suffix: '%', decimals: 1, sub: 'Probability of inactivity',  iconClass: 'amber',  kpiColor: '#f59e0b' },
];

export async function renderOverview(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Overview</h1>
        <p class="page-subtitle">Top-level KPIs and customer value distribution across all segments</p>
      </div>

      <div class="section">
        <div class="section-title">Key Performance Indicators</div>
        <div class="grid-4 stagger-children" id="kpi-grid">
          ${[0,1,2,3].map(() => `<div class="skeleton skeleton-kpi"></div>`).join('')}
        </div>
      </div>

      <div class="section">
        <div class="section-title">Segment Distribution</div>
        <div class="grid-2">
          <div class="card">
            <div class="panel-header">
              <div>
                <div class="panel-title">Customer Count by Segment</div>
                <div class="panel-subtitle">Share of total customer base</div>
              </div>
            </div>
            <div style="height:260px;position:relative;"><canvas id="donut-chart"></canvas></div>
          </div>
          <div class="card">
            <div class="panel-header">
              <div>
                <div class="panel-title">Total CLV Contribution</div>
                <div class="panel-subtitle">Projected 90-day value per segment</div>
              </div>
            </div>
            <div style="height:260px;position:relative;"><canvas id="clv-bar-chart"></canvas></div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Segment Breakdown</div>
        <div class="card" id="seg-table-panel">
          <div class="skeleton skeleton-chart"></div>
        </div>
      </div>
    </div>
  `;

  try {
    const data = await api.overview();
    const { kpis, segment_shares } = data;

    // ── KPI cards ──────────────────────────────────────────────────
    const kpiGrid = document.getElementById('kpi-grid');
    kpiGrid.innerHTML = '';

    const values = [
      kpis.total_customers,
      kpis.total_revenue,
      kpis.avg_clv,
      kpis.avg_churn_pct,
    ];

    KPI_CONFIGS.forEach((cfg, i) => {
      const el = document.createElement('div');
      el.className = 'kpi-card hover-lift';
      el.style.setProperty('--kpi-color', cfg.kpiColor);
      el.innerHTML = `
        <div class="kpi-icon-wrap ${cfg.iconClass}">${ICONS[Object.keys(ICONS)[i]]}</div>
        <div class="kpi-label">${cfg.label}</div>
        <div class="kpi-value" id="kv-${i}">0</div>
        <div class="kpi-sub">${cfg.sub}</div>
      `;
      kpiGrid.appendChild(el);
      const valEl = el.querySelector('.kpi-value');
      setTimeout(() => animateCounter(valEl, values[i], cfg.prefix, cfg.suffix, cfg.decimals), 100 + i * 60);
    });

    // ── Charts ─────────────────────────────────────────────────────
    const donutCanvas = document.getElementById('donut-chart');
    if (donutCanvas) renderDonut(donutCanvas, segment_shares);

    const barCanvas = document.getElementById('clv-bar-chart');
    if (barCanvas) renderClvBar(barCanvas, segment_shares);

    // ── Segment table ──────────────────────────────────────────────
    document.getElementById('seg-table-panel').innerHTML = `
      <div class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>Segment</th><th>Customers</th><th>% of Base</th><th>Total CLV</th></tr>
          </thead>
          <tbody>
            ${segment_shares.map(s => `
              <tr>
                <td class="text-col"><span class="segment-badge ${segClass(s.segment)}">${s.segment}</span></td>
                <td>${s.count.toLocaleString()}</td>
                <td>${s.pct_customers.toFixed(1)}%</td>
                <td class="accent-col">$${s.total_clv.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

  } catch (err) {
    showToast(`Failed to load overview: ${err.message}`, 'error');
    container.querySelector('.page-enter').insertAdjacentHTML('beforeend', `
      <div class="card" style="border-left:3px solid var(--red)">
        <p style="color:var(--red);font-weight:700">Pipeline data not found</p>
        <p style="color:var(--cv-text-3);margin-top:6px;font-size:0.8rem">${err.message}</p>
      </div>
    `);
  }
}

function segClass(name) {
  const m = {'Champions':'champions','Loyal Customers':'loyal','At Risk':'at-risk','Lost':'lost','New Customers':'new','Hibernating':'hibernating'};
  return m[name] || 'default';
}
