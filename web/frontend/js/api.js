/**
 * api.js — Fetch wrapper for the CLV Intelligence backend API
 */

const BASE = '';  // Same origin — FastAPI serves both

/**
 * Core fetch wrapper for JSON endpoints.
 * Automatically sets Content-Type: application/json.
 * @param {string} path
 * @param {RequestInit} [opts]
 * @returns {Promise<any>}
 */
async function apiFetch(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res;
}

/**
 * Raw fetch for multipart/form-data uploads.
 * Does NOT set Content-Type — the browser sets it automatically
 * with the correct multipart boundary when body is a FormData object.
 * @param {string} path
 * @param {FormData} formData
 * @returns {Promise<any>}
 */
async function apiFetchMultipart(path, formData) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    body: formData,
    // ⚠ No Content-Type header — browser sets multipart/form-data + boundary automatically
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res;
}

// ── Endpoints ──────────────────────────────────────────────────────────

export const api = {
  health:          () => apiFetch('/api/health'),
  overview:        () => apiFetch('/api/overview'),
  segments:        () => apiFetch('/api/segments'),
  segment:         (name) => apiFetch(`/api/segments/${encodeURIComponent(name)}`),
  customers:       (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/api/customers${qs ? '?' + qs : ''}`);
  },
  customer:        (id) => apiFetch(`/api/customers/${id}`),
  metrics:         () => apiFetch('/api/models/metrics'),
  pca:             () => apiFetch('/api/models/pca'),
  aliveMatrix:     () => apiFetch('/api/models/alive-matrix'),
  clvDistribution: () => apiFetch('/api/models/clv-distribution'),
  pipelineRun:     () => apiFetch('/api/pipeline/run', { method: 'POST' }),
  pipelineStatus:  () => apiFetch('/api/pipeline/status'),
  exportCsv:       () => apiFetch('/api/export/csv'),
  exportPdf:       () => apiFetch('/api/export/pdf'),

  // ── Upload — uses raw multipart fetch (no Content-Type override) ──
  uploadFile:      (formData) => apiFetchMultipart('/api/upload/file', formData),
  uploadStatus:    ()         => apiFetch('/api/upload/status'),
  uploadReset:     ()         => apiFetch('/api/upload/reset', { method: 'POST' }),

  // ── Recommendations ───────────────────────────────────────────────
  recommendations: () => apiFetch('/api/segments/recommendations/all'),
};
