/**
 * insights.js — Model Insights page (split-theme: white canvas)
 */

import { api } from '../api.js';
import { renderAliveHeatmap, renderClvHistogram } from '../charts.js';
import { showToast } from '../components/toast.js';

export async function renderInsights(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Model Insights</h1>
        <p class="page-subtitle">BG/NBD + Gamma-Gamma evaluation, alive probability matrix, and cluster diagnostics</p>
      </div>

      <div class="section">
        <div class="section-title">CLV Model Evaluation</div>
        <div class="grid-2">
          <div class="card" id="clv-metrics-panel"><div class="skeleton skeleton-chart"></div></div>
          <div class="card" id="model-arch-panel">
            <div class="panel-header">
              <div class="panel-title">Model Architecture</div>
              <div class="panel-subtitle">How CLV is computed end-to-end</div>
            </div>
            <div id="model-arch-content"></div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">BG/NBD Probability Alive Matrix</div>
        <div class="card">
          <div class="panel-header">
            <div>
              <div class="panel-title">P(alive | frequency, recency)</div>
              <div class="panel-subtitle">Probability a customer is still active given their purchase history</div>
            </div>
          </div>
          <div id="heatmap-container" style="position:relative;min-height:360px;">
            <div class="page-loading"><div class="loading-spinner"></div></div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">CLV Distribution</div>
        <div class="card">
          <div class="panel-header">
            <div>
              <div class="panel-title">Customer Lifetime Value Distribution</div>
              <div class="panel-subtitle">Log-scale histogram of predicted 90-day CLV</div>
            </div>
            <div id="clv-dist-stats" style="display:flex;gap:18px;font-size:0.75rem;color:var(--cv-text-3);font-weight:600"></div>
          </div>
          <div style="height:280px;position:relative;"><canvas id="clv-hist-canvas"></canvas></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Clustering Diagnostics</div>
        <div class="grid-3" id="cluster-metrics-grid">
          ${[0,1,2].map(() => `<div class="skeleton skeleton-kpi"></div>`).join('')}
        </div>
      </div>
    </div>
  `;

  try {
    const [metricsData, distData, matrixData] = await Promise.all([
      api.metrics(), api.clvDistribution(), api.aliveMatrix(),
    ]);
    renderClvMetrics(metricsData);
    renderModelArch();
    renderHeatmap(matrixData);
    renderDistribution(distData);
    renderClusterMetrics(metricsData.clustering);
  } catch (err) {
    showToast(`Failed to load insights: ${err.message}`, 'error');
  }
}

function renderClvMetrics(data) {
  const m = data.clv_model;
  const rows = [
    { name:'BG/NBD Log-Likelihood',       val:m.bgnbd_log_likelihood.toFixed(4),       note:'Higher = better fit' },
    { name:'Gamma-Gamma Log-Likelihood',   val:m.gamma_gamma_log_likelihood.toFixed(4), note:'Higher = better fit' },
    { name:'Holdout Period',               val:`${m.test_holdout_days} days`,            note:'20% temporal split' },
    { name:'Purchases MAE',                val:m.purchases_mae.toFixed(4),               note:'Mean absolute error' },
    { name:'Purchases RMSE',               val:m.purchases_rmse.toFixed(4),              note:'Root mean squared error' },
    { name:'Revenue MAE',                  val:`$${m.revenue_mae.toLocaleString(undefined,{maximumFractionDigits:2})}`, note:'Mean absolute error' },
    { name:'Revenue RMSE',                 val:`$${m.revenue_rmse.toLocaleString(undefined,{maximumFractionDigits:2})}`, note:'Root mean squared error' },
  ];

  document.getElementById('clv-metrics-panel').innerHTML = `
    <div class="panel-header">
      <div>
        <div class="panel-title">BG/NBD + Gamma-Gamma Metrics</div>
        <div class="panel-subtitle">Evaluated on 80/20 temporal holdout split</div>
      </div>
    </div>
    ${rows.map(r => `
      <div class="metric-row">
        <div>
          <div class="metric-name">${r.name}</div>
          <div style="font-size:0.68rem;color:var(--cv-text-4)">${r.note}</div>
        </div>
        <div class="metric-val">${r.val}</div>
      </div>
    `).join('')}
  `;
}

function renderModelArch() {
  const cards = [
    { title:'BG/NBD Model',       cls:'',       body:'Models repeat transactions while "alive" and the probability of becoming inactive after each purchase.', meta:'Inputs: frequency · recency · T\nOutput: E[purchases in N days]' },
    { title:'Gamma-Gamma Model',  cls:'violet', body:'Estimates expected average monetary value per transaction, conditional on the customer being alive.', meta:'Inputs: frequency · monetary_value\nOutput: E[avg order value]' },
    { title:'CLV Formula',        cls:'blue',   body:'CLV = E[purchases] × E[avg profit] × margin × discount_factor. Discount rate applied monthly over the 90-day horizon.', meta:'margin: 10% · discount: 1%/month' },
    { title:'K-Means Clustering', cls:'amber',  body:'Optimal k selected via Silhouette Score across k=2..8. Features: recency, frequency, monetary, tenure, CLV — all StandardScaler normalized.', meta:'PCA (2D) applied for visualization only' },
  ];

  document.getElementById('model-arch-content').innerHTML = cards.map(c => `
    <div class="model-card ${c.cls}">
      <div class="model-card-title">${c.title}</div>
      <div class="model-card-body">${c.body}</div>
      <div class="model-card-meta">${c.meta}</div>
    </div>
  `).join('');
}

function renderHeatmap(data) {
  const container = document.getElementById('heatmap-container');
  container.innerHTML = '';
  if (!data.matrix || data.matrix.length === 0) {
    container.innerHTML = `<div class="empty-state"><p>Alive matrix not available. Ensure bgf_model.pkl exists.</p></div>`;
    return;
  }
  renderAliveHeatmap(container, data);
}

function renderDistribution(data) {
  const canvas = document.getElementById('clv-hist-canvas');
  if (!canvas) return;
  renderClvHistogram(canvas, data.bins);

  document.getElementById('clv-dist-stats').innerHTML = `
    <span>Mean: <strong style="color:var(--cv-text)">$${data.mean.toFixed(2)}</strong></span>
    <span>Median: <strong style="color:var(--cv-text)">$${data.median.toFixed(2)}</strong></span>
    <span>P90: <strong style="color:#00a85a">$${data.p90.toFixed(2)}</strong></span>
  `;
}

function renderClusterMetrics(cl) {
  const items = [
    { label:'Silhouette Score',    value:cl.silhouette_score,        fmt:v=>v.toFixed(4), pct:Math.min(cl.silhouette_score*100,100), desc:'Measures how similar a point is to its own cluster vs others. Range: -1 to 1.', target:'Target > 0.5', barClass:'' },
    { label:'Davies-Bouldin Index',value:cl.davies_bouldin_index,    fmt:v=>v.toFixed(4), pct:Math.max(0,100-cl.davies_bouldin_index*33), desc:'Average similarity between each cluster and its most similar cluster. Lower is better.', target:'Target < 1.0', barClass:'amber' },
    { label:'Calinski-Harabász',   value:cl.calinski_harabasz_index, fmt:v=>v.toLocaleString(undefined,{maximumFractionDigits:1}), pct:70, desc:'Ratio of between-cluster to within-cluster dispersion. Higher is better.', target:'Higher is better', barClass:'blue' },
  ];

  document.getElementById('cluster-metrics-grid').innerHTML = items.map(item => `
    <div class="card hover-lift">
      <div class="kpi-label">${item.label}</div>
      <div style="font-size:1.5rem;font-weight:800;color:var(--cv-text);letter-spacing:-0.03em;margin:8px 0 10px">${item.fmt(item.value)}</div>
      <div class="progress-bar-wrap" style="margin-bottom:10px">
        <div class="progress-bar-fill ${item.barClass}" style="width:${item.pct}%"></div>
      </div>
      <div style="font-size:0.75rem;color:var(--cv-text-3);line-height:1.55;margin-bottom:6px">${item.desc}</div>
      <div style="font-size:0.7rem;color:#00a85a;font-weight:700">${item.target}</div>
    </div>
  `).join('');
}
