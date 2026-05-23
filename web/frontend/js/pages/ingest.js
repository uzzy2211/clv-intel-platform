/**
 * ingest.js — Data Ingest landing page
 *
 * Drag-and-drop upload zone for CSV/XLSX transaction files.
 * Polls /api/upload/status while the ML pipeline runs, then
 * unlocks the dashboard and navigates to Overview.
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

const PIPELINE_STEPS = [
  { label: 'Parsing uploaded file',       pct: 10 },
  { label: 'Validating schema',           pct: 25 },
  { label: 'Saving dataset',              pct: 40 },
  { label: 'Fitting BG/NBD model',        pct: 55 },
  { label: 'Fitting Gamma-Gamma model',   pct: 65 },
  { label: 'Running K-Means clustering',  pct: 75 },
  { label: 'Evaluating models',           pct: 85 },
  { label: 'Reloading data service',      pct: 95 },
];

let _pollTimer = null;

export async function renderIngest(container) {
  // Check if data already exists
  let hasData = false;
  try {
    const h = await api.health();
    hasData = h.pipeline_ready;
  } catch (_) {}

  container.innerHTML = `
    <div class="page-enter">
      <div class="page-header">
        <h1 class="page-title">Data Ingest</h1>
        <p class="page-subtitle">Upload your transactional dataset to compute CLV predictions and customer segments</p>
      </div>

      <!-- ── Upload zone ── -->
      <div class="section">
        <div class="section-title">Dataset Upload</div>
        <div id="upload-area"></div>
      </div>

      <!-- ── Existing data banner ── -->
      ${hasData ? `
      <div class="section">
        <div class="section-title">Existing Dataset</div>
        <div class="card ready-banner">
          <div class="ready-banner-icon">
            <svg viewBox="0 0 20 20" fill="currentColor" width="22" height="22">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="ready-banner-body">
            <div class="ready-banner-title">Pipeline data is ready</div>
            <div class="ready-banner-sub">A processed dataset already exists. View the dashboard or upload a new file to replace it.</div>
          </div>
          <button class="btn btn-primary" id="goto-overview-btn">
            View Dashboard
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
              <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>
      ` : ''}

      <!-- ── Schema reference ── -->
      <div class="section">
        <div class="section-title">Required Schema</div>
        <div class="card">
          <div class="panel-header">
            <div>
              <div class="panel-title">Expected Column Format</div>
              <div class="panel-subtitle">Compatible with the UCI Online Retail II dataset</div>
            </div>
            <span class="badge badge-green">Online Retail II</span>
          </div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Column</th><th>Type</th><th>Example</th><th>Notes</th>
                </tr>
              </thead>
              <tbody>
                ${[
                  ['InvoiceNo',   'string',   '536365',              'Cancellations start with "C"'],
                  ['StockCode',   'string',   '85123A',              'Product identifier'],
                  ['Description', 'string',   'WHITE HANGING HEART', 'Product name'],
                  ['Quantity',    'integer',  '6',                   'Negative = return/cancellation'],
                  ['InvoiceDate', 'datetime', '2010-12-01 08:26',    'ISO or common date formats'],
                  ['UnitPrice',   'float',    '2.55',                'In local currency'],
                  ['CustomerID',  'float',    '17850.0',             'Null rows are dropped'],
                  ['Country',     'string',   'United Kingdom',      'Optional — used for filtering'],
                ].map(([col, type, ex, note]) => `
                  <tr>
                    <td class="text-col" style="font-family:var(--font-mono);font-size:0.78rem">${col}</td>
                    <td><span class="badge badge-neutral">${type}</span></td>
                    <td style="font-family:var(--font-mono);font-size:0.75rem;color:var(--cv-text-3)">${ex}</td>
                    <td style="color:var(--cv-text-4);font-size:0.75rem">${note}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>
  `;

  // Wire "View Dashboard" button
  document.getElementById('goto-overview-btn')?.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'overview' }));
  });

  renderDropZone();
}

// ── Drop zone ──────────────────────────────────────────────────────────
function renderDropZone() {
  const area = document.getElementById('upload-area');
  if (!area) return;

  area.innerHTML = `
    <div class="drop-zone" id="drop-zone" tabindex="0" role="button"
         aria-label="Drop CSV or Excel file here to upload">

      <div class="drop-zone-inner">
        <div class="drop-zone-icon-wrap">
          <svg viewBox="0 0 48 48" fill="none" width="48" height="48">
            <circle cx="24" cy="24" r="23" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.3"/>
            <path d="M24 32V18M24 18L18 24M24 18L30 24" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <div class="drop-zone-title">
          Drag and drop your transactional logs here
        </div>
        <div class="drop-zone-sub">
          <span class="format-chip">.csv</span>
          <span class="format-chip">.xlsx</span>
          <span class="format-chip">.xls</span>
          <span style="color:var(--cv-text-4);font-size:0.75rem;margin-left:4px">· Max 50 MB</span>
        </div>
        <div class="drop-zone-or">or</div>
        <button class="btn btn-outline" id="browse-btn">Browse files</button>
      </div>

      <input type="file" id="file-input" accept=".csv,.xlsx,.xls" style="display:none" />
    </div>
  `;

  const dropZone  = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const browseBtn = document.getElementById('browse-btn');

  browseBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', e => {
    if (!dropZone.contains(e.relatedTarget)) dropZone.classList.remove('drag-over');
  });
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    if (file) handleFile(file);
  });
}

// ── Handle file ────────────────────────────────────────────────────────
async function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'xlsx', 'xls'].includes(ext)) {
    showToast(`Unsupported file type: .${ext}. Use .csv or .xlsx`, 'error');
    return;
  }

  renderProgressUI(file.name, file.size);

  const formData = new FormData();
  formData.append('file', file);

  try {
    await api.uploadFile(formData);
    startPolling();
  } catch (err) {
    showToast(`Upload failed: ${err.message}`, 'error');
    renderDropZone();
  }
}

// ── Progress UI ────────────────────────────────────────────────────────
function renderProgressUI(filename, filesize) {
  const area = document.getElementById('upload-area');
  if (!area) return;

  const sizeMB = (filesize / 1024 / 1024).toFixed(1);

  area.innerHTML = `
    <div class="upload-progress-card">

      <!-- File info header -->
      <div class="upload-file-header">
        <div class="upload-file-icon">
          <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="upload-file-meta">
          <div class="upload-filename">${filename}</div>
          <div class="upload-filesize">${sizeMB} MB</div>
        </div>
        <div class="upload-pct" id="upload-pct">0%</div>
      </div>

      <!-- Progress bar -->
      <div class="upload-bar-track">
        <div class="upload-bar-fill" id="upload-bar" style="width:0%"></div>
      </div>

      <!-- Status message -->
      <div class="upload-status-msg" id="upload-status-msg">
        Uploading file...
      </div>

      <!-- Pipeline steps -->
      <div class="pipeline-steps" id="pipeline-steps">
        ${PIPELINE_STEPS.map((s, i) => `
          <div class="pipeline-step" id="pstep-${i}">
            <div class="pstep-dot"></div>
            <span class="pstep-label">${s.label}</span>
          </div>
        `).join('')}
      </div>

    </div>
  `;
}

// ── Polling ────────────────────────────────────────────────────────────
function startPolling() {
  if (_pollTimer) clearInterval(_pollTimer);

  _pollTimer = setInterval(async () => {
    try {
      const s = await api.uploadStatus();
      syncProgressUI(s);

      if (s.status === 'done') {
        clearInterval(_pollTimer); _pollTimer = null;
        onDone(s);
      } else if (s.status === 'error') {
        clearInterval(_pollTimer); _pollTimer = null;
        onError(s.message);
      }
    } catch (_) { /* network hiccup — keep polling */ }
  }, 700);
}

function syncProgressUI(s) {
  const bar    = document.getElementById('upload-bar');
  const pct    = document.getElementById('upload-pct');
  const msg    = document.getElementById('upload-status-msg');

  if (bar) bar.style.width = `${s.progress}%`;
  if (pct) pct.textContent = `${s.progress}%`;
  if (msg) msg.textContent = s.message;

  // Activate steps
  const activeIdx = PIPELINE_STEPS.findIndex(step => s.progress < step.pct);
  const doneIdx   = activeIdx === -1 ? PIPELINE_STEPS.length : activeIdx;

  PIPELINE_STEPS.forEach((_, i) => {
    const el = document.getElementById(`pstep-${i}`);
    if (!el) return;
    if (i < doneIdx)      el.className = 'pipeline-step done';
    else if (i === doneIdx) el.className = 'pipeline-step active';
    else                  el.className = 'pipeline-step';
  });

  // Update sidebar pill
  syncSidebarPill(s);
}

function onDone(s) {
  // Final UI update
  const bar = document.getElementById('upload-bar');
  const pct = document.getElementById('upload-pct');
  const msg = document.getElementById('upload-status-msg');
  if (bar) { bar.style.width = '100%'; bar.classList.add('done'); }
  if (pct) pct.textContent = '100%';
  if (msg) msg.textContent = s.message;

  PIPELINE_STEPS.forEach((_, i) => {
    const el = document.getElementById(`pstep-${i}`);
    if (el) el.className = 'pipeline-step done';
  });

  syncSidebarPill({ status: 'done', filename: s.filename, rows: s.rows });

  // Notify app shell
  import('../app.js').then(m => m.onDataReady(s.rows)).catch(() => {});

  showToast(`Dataset ready — ${s.rows?.toLocaleString() ?? ''} customers processed`, 'success', 5000);

  // Auto-navigate to overview after 1.8s
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'overview' }));
  }, 1800);
}

function onError(message) {
  const bar = document.getElementById('upload-bar');
  const msg = document.getElementById('upload-status-msg');
  if (bar) { bar.classList.add('error'); }
  if (msg) msg.textContent = `Error: ${message}`;

  showToast(`Processing failed: ${message}`, 'error', 8000);

  const card = document.querySelector('.upload-progress-card');
  if (card) {
    card.insertAdjacentHTML('beforeend', `
      <div style="margin-top:16px;display:flex;gap:10px">
        <button class="btn btn-outline" id="retry-btn">Try another file</button>
      </div>
    `);
    document.getElementById('retry-btn')?.addEventListener('click', () => {
      api.uploadReset().catch(() => {});
      renderDropZone();
    });
  }
}

function syncSidebarPill(s) {
  const pill = document.getElementById('sidebar-upload-pill');
  const text = document.getElementById('upload-pill-text');
  if (!pill || !text) return;

  if (s.status === 'done') {
    pill.classList.add('ready');
    text.textContent = s.filename
      ? s.filename.length > 22 ? s.filename.substring(0, 20) + '…' : s.filename
      : 'Dataset ready';
  } else if (s.status === 'processing' || s.status === 'uploading') {
    pill.classList.remove('ready');
    text.textContent = 'Processing...';
  }
}
