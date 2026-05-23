/**
 * export.js — Export & Pipeline page (split-theme: white canvas)
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

export async function renderExport(container) {
  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Export & Pipeline</h1>
        <p class="page-subtitle">Download data, generate reports, and manage the ML pipeline</p>
      </div>

      <div class="section">
        <div class="section-title">Data Export</div>
        <div class="grid-2">

          <div class="card hover-lift">
            <div class="panel-header">
              <div>
                <div class="panel-title">Customer Segments CSV</div>
                <div class="panel-subtitle">Full dataset with RFM, CLV, and segment labels</div>
              </div>
              <div class="kpi-icon-wrap green">
                <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
            <p style="font-size:0.82rem;color:var(--cv-text-3);margin-bottom:14px;line-height:1.65">
              Exports all customer records including recency, frequency, monetary value, tenure, predicted CLV, churn probability, predicted purchases, and segment assignment.
            </p>
            <div style="background:var(--cv-bg);border:1px solid var(--cv-border);border-radius:var(--radius-sm);padding:10px 12px;margin-bottom:16px;font-size:0.7rem;color:var(--cv-text-4);font-family:var(--font-mono);line-height:1.8">
              CustomerID · recency · frequency · monetary · tenure · clv · churn_probability · predicted_purchases · segment
            </div>
            <button class="btn btn-primary" id="csv-btn">
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
              Download CSV
            </button>
          </div>

          <div class="card hover-lift">
            <div class="panel-header">
              <div>
                <div class="panel-title">Executive PDF Report</div>
                <div class="panel-subtitle">Branded summary with metrics and recommendations</div>
              </div>
              <div class="kpi-icon-wrap violet">
                <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
            <p style="font-size:0.82rem;color:var(--cv-text-3);margin-bottom:14px;line-height:1.65">
              Generates a multi-page PDF including executive overview, CLV model evaluation, clustering metrics, segment profiles, and strategic recommendations per segment.
            </p>
            <div style="background:var(--cv-bg);border:1px solid var(--cv-border);border-radius:var(--radius-sm);padding:10px 12px;margin-bottom:16px;font-size:0.7rem;color:var(--cv-text-4);font-family:var(--font-mono);line-height:1.8">
              Cover · Overview KPIs · CLV Metrics · Clustering · Segment Profiles · Recommendations
            </div>
            <button class="btn btn-ghost" id="pdf-btn">
              <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
              </svg>
              Generate & Download PDF
            </button>
          </div>

        </div>
      </div>

      <div class="section">
        <div class="section-title">ML Pipeline Control</div>
        <div class="card">
          <div class="panel-header">
            <div>
              <div class="panel-title">Re-run Full Pipeline</div>
              <div class="panel-subtitle">Feature engineering → CLV modeling → Clustering → Evaluation</div>
            </div>
          </div>
          <div class="grid-2" style="margin-bottom:18px">
            <div>
              <p style="font-size:0.82rem;color:var(--cv-text-3);line-height:1.7;margin-bottom:14px">
                Triggers the complete ML pipeline on the current dataset. Re-computes RFM features, re-fits BG/NBD and Gamma-Gamma models, re-clusters customers, and updates all evaluation metrics.
              </p>
              <div style="background:var(--cv-bg);border:1px solid var(--cv-border);border-radius:var(--radius-sm);padding:12px 14px;margin-bottom:16px;font-size:0.7rem;color:var(--cv-text-4);font-family:var(--font-mono);line-height:2">
                1. feature_engineering.py → 02_rfm_features.csv<br/>
                2. clv_model.py → 03_clv_predictions.csv<br/>
                3. clustering.py → 04_customer_segments.csv<br/>
                4. evaluation.py → evaluation_metrics.json
              </div>
              <button class="btn btn-primary" id="pipeline-btn">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/>
                </svg>
                Run Pipeline
              </button>
            </div>
            <div id="pipeline-status-panel">
              <div class="skeleton skeleton-chart" style="height:200px"></div>
            </div>
          </div>
          <div class="pipeline-log" id="pipeline-log"></div>
        </div>
      </div>

    </div>
  `;

  loadPipelineStatus();

  document.getElementById('csv-btn').addEventListener('click', async () => {
    const btn = document.getElementById('csv-btn');
    btn.disabled = true; btn.textContent = 'Downloading...';
    try {
      const res = await api.exportCsv();
      const blob = await res.blob();
      triggerDownload(blob, 'clv_customer_segments.csv', 'text/csv');
      showToast('CSV downloaded successfully', 'success');
    } catch (err) {
      showToast(`CSV download failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/></svg> Download CSV`;
    }
  });

  document.getElementById('pdf-btn').addEventListener('click', async () => {
    const btn = document.getElementById('pdf-btn');
    btn.disabled = true; btn.textContent = 'Generating PDF...';
    showToast('Generating PDF report, please wait...', 'info', 6000);
    try {
      const res = await api.exportPdf();
      const blob = await res.blob();
      triggerDownload(blob, 'clv_segmentation_report.pdf', 'application/pdf');
      showToast('PDF report downloaded', 'success');
    } catch (err) {
      showToast(`PDF generation failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg> Generate & Download PDF`;
    }
  });

  document.getElementById('pipeline-btn').addEventListener('click', async () => {
    const btn    = document.getElementById('pipeline-btn');
    const logEl  = document.getElementById('pipeline-log');
    btn.disabled = true; btn.textContent = 'Running...';
    logEl.style.display = 'block'; logEl.innerHTML = '';

    const steps = [
      '> Loading transaction data...',
      '> Engineering RFM features...',
      '> Fitting BG/NBD model...',
      '> Fitting Gamma-Gamma model...',
      '> Predicting CLV scores...',
      '> Running K-Means clustering...',
      '> Evaluating models...',
      '> Saving artifacts...',
    ];

    let idx = 0;
    const interval = setInterval(() => {
      if (idx < steps.length) { logEl.innerHTML += steps[idx] + '\n'; logEl.scrollTop = logEl.scrollHeight; idx++; }
    }, 800);

    try {
      const result = await api.pipelineRun();
      clearInterval(interval);
      logEl.innerHTML += `\n[OK] ${result.message}\n`;
      showToast('Pipeline started. Data will refresh shortly.', 'success', 6000);
      setTimeout(() => loadPipelineStatus(), 15000);
    } catch (err) {
      clearInterval(interval);
      logEl.innerHTML += `\n[ERR] ${err.message}\n`;
      showToast(`Pipeline failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/></svg> Run Pipeline`;
    }
  });
}

async function loadPipelineStatus() {
  const panel = document.getElementById('pipeline-status-panel');
  if (!panel) return;
  try {
    const status = await api.pipelineStatus();
    const segCounts = status.segment_counts || {};
    const metrics   = status.metrics || {};

    panel.innerHTML = `
      <div style="background:var(--cv-bg);border:1px solid var(--cv-border);border-radius:var(--radius-md);padding:16px">
        <div style="font-size:0.66rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:var(--cv-text-4);margin-bottom:12px">Last Run Status</div>
        <div class="metric-row">
          <span class="metric-name">Algorithm</span>
          <span class="metric-val" style="color:#00a85a">${status.algorithm.toUpperCase()}</span>
        </div>
        <div class="metric-row">
          <span class="metric-name">Optimal k</span>
          <span class="metric-val">${status.optimal_k}</span>
        </div>
        ${metrics.silhouette_score !== undefined ? `
        <div class="metric-row">
          <span class="metric-name">Silhouette Score</span>
          <span class="metric-val">${metrics.silhouette_score.toFixed(4)}</span>
        </div>` : ''}
        <div style="margin-top:12px;font-size:0.66rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:var(--cv-text-4);margin-bottom:8px">Segment Counts</div>
        ${Object.entries(segCounts).map(([seg, count]) => `
          <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--cv-border);font-size:0.8rem">
            <span style="color:var(--cv-text-3);font-weight:500">${seg}</span>
            <span style="color:var(--cv-text);font-weight:700">${count.toLocaleString()}</span>
          </div>
        `).join('')}
      </div>
    `;
  } catch (_) {
    panel.innerHTML = `<div class="empty-state"><p>Could not load pipeline status</p></div>`;
  }
}

function triggerDownload(blob, filename, mimeType) {
  const url = URL.createObjectURL(new Blob([blob], { type: mimeType }));
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}
