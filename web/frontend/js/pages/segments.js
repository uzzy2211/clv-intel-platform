/**
 * segments.js — Customer Segments page (split-theme: white canvas)
 */

import { api } from '../api.js';
import { renderPcaScatter, renderSegmentRings } from '../charts.js';
import { showToast } from '../components/toast.js';

export async function renderSegments(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Customer Segments</h1>
        <p class="page-subtitle">Behavioral cohort analysis, cluster visualization, and RFM composition</p>
      </div>

      <div class="section">
        <div class="section-title">Segment Profiles</div>
        <div class="grid-2-1">
          <div class="card" id="seg-table-panel"><div class="skeleton skeleton-chart"></div></div>
          <div class="card" id="rings-panel">
            <div class="panel-header">
              <div>
                <div class="panel-title">Segment Rings</div>
                <div class="panel-subtitle">Arc = count · thickness = CLV</div>
              </div>
            </div>
            <div id="rings-container" style="display:flex;justify-content:center;padding:8px 0;"></div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">PCA Customer Map</div>
        <div class="card">
          <div class="panel-header">
            <div>
              <div class="panel-title">2D PCA Projection</div>
              <div class="panel-subtitle">Customers projected from scaled RFM + CLV features</div>
            </div>
            <div id="pca-hover-info" style="font-size:0.75rem;color:var(--cv-text-3);font-weight:500"></div>
          </div>
          <div id="pca-container" style="position:relative;"></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">RFM DNA Composition</div>
        <div class="card" id="dna-panel"><div class="skeleton skeleton-chart"></div></div>
      </div>

      <div class="section">
        <div class="section-title">Clustering Quality Metrics</div>
        <div class="grid-3" id="metrics-grid">
          ${[0,1,2].map(() => `<div class="skeleton skeleton-kpi"></div>`).join('')}
        </div>
      </div>

      <div class="section">
        <div class="section-title">Strategic Recommendations</div>
        <div id="recommendations-grid" class="grid-2">
          ${[0,1].map(() => `<div class="skeleton skeleton-chart" style="height:180px"></div>`).join('')}
        </div>
      </div>
    </div>
  `;

  try {
    const [segData, pcaData, recsData] = await Promise.all([
      api.segments(),
      api.pca(),
      api.recommendations().catch(() => null),  // graceful — never blocks page load
    ]);
    const { segments, clustering_metrics, algorithm, optimal_k } = segData;

    // ── Segment table ──────────────────────────────────────────────
    document.getElementById('seg-table-panel').innerHTML = `
      <div class="panel-header">
        <div>
          <div class="panel-title">Segment Profiles</div>
          <div class="panel-subtitle">${algorithm.toUpperCase()} · k = ${optimal_k} clusters</div>
        </div>
      </div>
      <div class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>Segment</th><th>Customers</th><th>Avg Recency</th><th>Avg Frequency</th><th>Avg Monetary</th><th>Avg CLV</th><th>Churn Risk</th></tr>
          </thead>
          <tbody>
            ${segments.map(s => `
              <tr>
                <td class="text-col"><span class="segment-badge ${segClass(s.name)}">${s.name}</span></td>
                <td>${s.customer_count.toLocaleString()}</td>
                <td>${s.avg_recency.toFixed(0)}d</td>
                <td>${s.avg_frequency.toFixed(1)}</td>
                <td>$${s.avg_monetary.toLocaleString(undefined,{maximumFractionDigits:0})}</td>
                <td class="accent-col">$${s.avg_clv.toFixed(2)}</td>
                <td style="color:${churnColor(s.avg_churn_probability)};font-weight:600">${(s.avg_churn_probability*100).toFixed(1)}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    // ── Rings ──────────────────────────────────────────────────────
    renderSegmentRings(document.getElementById('rings-container'), segments);

    // ── PCA scatter ────────────────────────────────────────────────
    const hoverInfo = document.getElementById('pca-hover-info');
    renderPcaScatter(document.getElementById('pca-container'), pcaData.points, d => {
      hoverInfo.textContent = `ID: ${d.customer_id} · ${d.segment} · CLV: $${d.clv.toFixed(2)}`;
    });

    // ── DNA bars ───────────────────────────────────────────────────
    const maxVals = {
      recency:   Math.max(...segments.map(s => s.avg_recency)),
      frequency: Math.max(...segments.map(s => s.avg_frequency)),
      monetary:  Math.max(...segments.map(s => s.avg_monetary)),
      tenure:    Math.max(...segments.map(s => s.avg_tenure)),
    };

    document.getElementById('dna-panel').innerHTML = `
      <div class="panel-header">
        <div class="panel-title">RFM Feature Composition per Segment</div>
        <div style="display:flex;gap:14px;font-size:0.7rem;color:var(--cv-text-4);font-weight:600">
          <span><span style="color:#00a85a">■</span> Frequency</span>
          <span><span style="color:#7c3aed">■</span> Monetary</span>
          <span><span style="color:#0ea5e9">■</span> Tenure</span>
          <span><span style="color:#f59e0b">■</span> Activity</span>
        </div>
      </div>
      <div class="dna-bar-wrap">
        ${segments.map(s => {
          const f = s.avg_frequency / maxVals.frequency;
          const m = s.avg_monetary  / maxVals.monetary;
          const t = s.avg_tenure    / maxVals.tenure;
          const r = 1 - (s.avg_recency / maxVals.recency);
          const total = f + m + t + r || 1;
          const pct = v => ((v / total) * 100).toFixed(1) + '%';
          return `
            <div class="dna-bar-row">
              <div class="dna-bar-label">${s.name}</div>
              <div class="dna-bar-track">
                <div class="dna-bar-segment" style="width:${pct(f)};background:#00a85a;opacity:0.85"></div>
                <div class="dna-bar-segment" style="width:${pct(m)};background:#7c3aed;opacity:0.85"></div>
                <div class="dna-bar-segment" style="width:${pct(t)};background:#0ea5e9;opacity:0.85"></div>
                <div class="dna-bar-segment" style="width:${pct(r)};background:#f59e0b;opacity:0.85"></div>
              </div>
              <div class="dna-bar-value">$${s.avg_clv.toFixed(0)}</div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    // ── Clustering metrics ─────────────────────────────────────────
    const metricItems = [
      { label:'Silhouette Score',    value:clustering_metrics.silhouette_score,       fmt:v=>v.toFixed(4), pct:Math.min(clustering_metrics.silhouette_score*100,100), desc:'Closer to 1.0 = well-separated clusters', target:'Target > 0.5', barClass:'' },
      { label:'Davies-Bouldin Index',value:clustering_metrics.davies_bouldin_index,   fmt:v=>v.toFixed(4), pct:Math.max(0,100-clustering_metrics.davies_bouldin_index*33), desc:'Lower = better cluster separation', target:'Target < 1.0', barClass:'amber' },
      { label:'Calinski-Harabász',   value:clustering_metrics.calinski_harabasz_index,fmt:v=>v.toLocaleString(undefined,{maximumFractionDigits:1}), pct:70, desc:'Higher = denser, better-separated clusters', target:'Higher is better', barClass:'blue' },
    ];

    document.getElementById('metrics-grid').innerHTML = metricItems.map(m => `
      <div class="card hover-lift">
        <div class="kpi-label">${m.label}</div>
        <div style="font-size:1.55rem;font-weight:800;color:var(--cv-text);letter-spacing:-0.03em;margin:8px 0 10px">${m.fmt(m.value)}</div>
        <div class="progress-bar-wrap" style="margin-bottom:10px">
          <div class="progress-bar-fill ${m.barClass}" style="width:${m.pct}%"></div>
        </div>
        <div style="font-size:0.75rem;color:var(--cv-text-3);line-height:1.55;margin-bottom:6px">${m.desc}</div>
        <div style="font-size:0.7rem;color:#00a85a;font-weight:700">${m.target}</div>
      </div>
    `).join('');

    // ── Strategic Recommendations ──────────────────────────────────
    const recsGrid = document.getElementById('recommendations-grid');
    if (recsGrid) {
      const recs = recsData?.recommendations ?? [];

      if (recs.length === 0) {
        // Fallback: render hardcoded cards for the two known segment types
        recsGrid.innerHTML = _fallbackRecommendations();
      } else {
        recsGrid.innerHTML = recs.map(r => _recCard(r)).join('');
      }
    }

  } catch (err) {
    showToast(`Failed to load segments: ${err.message}`, 'error');
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

// ── Recommendation card renderer ──────────────────────────────────────

/**
 * Render a single recommendation card from the API response.
 * @param {object} r - Recommendation object from /api/segments/recommendations/all
 */
function _recCard(r) {
  const tierBg = {
    high:        'rgba(0,168,90,0.07)',
    medium:      'rgba(14,165,233,0.07)',
    atrisk:      'rgba(245,158,11,0.07)',
    lost:        'rgba(239,68,68,0.07)',
    new:         'rgba(124,58,237,0.07)',
    hibernating: 'rgba(148,163,184,0.07)',
  };
  const bg = tierBg[r.tier] || 'rgba(0,0,0,0.04)';

  return `
    <div class="card hover-lift" style="border-left:3px solid ${r.color};background:${bg}">
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px">
        <div style="
          width:36px;height:36px;border-radius:8px;flex-shrink:0;
          background:${r.color}22;display:flex;align-items:center;justify-content:center">
          <svg viewBox="0 0 24 24" fill="none" stroke="${r.color}"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               width="18" height="18">
            <path d="${r.icon}"/>
          </svg>
        </div>
        <div style="min-width:0">
          <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.1em;color:${r.color};margin-bottom:3px">
            ${r.segment}
          </div>
          <div style="font-size:0.88rem;font-weight:700;color:var(--cv-text);
                      line-height:1.35;letter-spacing:-0.01em">
            ${r.headline}
          </div>
        </div>
      </div>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:7px">
        ${r.actions.map(action => `
          <li style="display:flex;align-items:flex-start;gap:8px;font-size:0.78rem;
                     color:var(--cv-text-3);line-height:1.5">
            <span style="color:${r.color};font-weight:700;flex-shrink:0;margin-top:1px">›</span>
            <span>${action}</span>
          </li>
        `).join('')}
      </ul>
    </div>
  `;
}

/**
 * Hardcoded fallback cards shown when the recommendations API is unavailable.
 * Always covers the two active dataset segment types.
 */
function _fallbackRecommendations() {
  const cards = [
    {
      segment:  'High Value Customers',
      color:    '#00a85a',
      icon:     'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
      headline: 'Protect revenue concentration and deepen wholesale relationships',
      actions: [
        'Exclusive VIP loyalty programs and high-volume wholesale discounts.',
        'Dedicated account managers and priority customer support.',
        'Tiered procurement pricing: volume-based discount ladders to lock in forward commitments.',
        'Early access to new products and private inventory reservations.',
        'Quarterly business reviews covering volume forecasts and pricing structures.',
      ],
      tier: 'high',
    },
    {
      segment:  'Low Value / Lost',
      color:    '#ef4444',
      icon:     'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
      headline: 'Programmatic re-engagement and win-back pipeline',
      actions: [
        'Re-engagement email campaigns with win-back incentives.',
        'Cart-abandonment and browse-abandonment discount triggers.',
        'Automated 4-step sequence: 60, 90, 120, 180 days of inactivity.',
        'One-time deep discount (30-40%) as a last-chance offer.',
        'Suppress non-responders after 180 days and reallocate budget.',
      ],
      tier: 'lost',
    },
  ];
  return cards.map(r => _recCard(r)).join('');
}
