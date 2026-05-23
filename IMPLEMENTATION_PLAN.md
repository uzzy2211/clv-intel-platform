# Implementation Plan — CLV Segmentation Web Platform
> Full-Stack Web Application | Version 1.0.0

---

## Overview

This document outlines the phase-by-phase plan to build a production-grade web platform for the CLV Segmentation ML project. The frontend uses a unique **dark glassmorphism + data-terminal aesthetic** (not the typical Streamlit/Gradio/generic AI dashboard look). The backend is a FastAPI REST API that wraps the existing ML pipeline.

---

## Architecture

```
Antigravity/
│
├── web/                          ← NEW: Full web application
│   ├── backend/
│   │   ├── main.py               ← FastAPI app entry point
│   │   ├── routers/
│   │   │   ├── overview.py       ← /api/overview endpoints
│   │   │   ├── segments.py       ← /api/segments endpoints
│   │   │   ├── customers.py      ← /api/customers endpoints
│   │   │   ├── models.py         ← /api/models endpoints
│   │   │   └── pipeline.py       ← /api/pipeline run endpoints
│   │   ├── services/
│   │   │   ├── data_service.py   ← Loads & caches processed data
│   │   │   ├── ml_service.py     ← Wraps src/ ML pipeline
│   │   │   └── report_service.py ← PDF generation wrapper
│   │   └── schemas.py            ← Pydantic response models
│   │
│   └── frontend/
│       ├── index.html            ← Single-page app shell
│       ├── css/
│       │   ├── main.css          ← Core design system (glassmorphism + terminal)
│       │   ├── components.css    ← Reusable UI components
│       │   └── animations.css    ← Micro-animations & transitions
│       ├── js/
│       │   ├── app.js            ← SPA router & state management
│       │   ├── api.js            ← Fetch wrapper for backend API
│       │   ├── charts.js         ← Chart.js + D3 visualizations
│       │   ├── pages/
│       │   │   ├── overview.js   ← Overview page logic
│       │   │   ├── segments.js   ← Segments page logic
│       │   │   ├── explorer.js   ← Customer explorer logic
│       │   │   ├── insights.js   ← Model insights logic
│       │   │   └── export.js     ← Export page logic
│       │   └── components/
│       │       ├── kpi-card.js   ← KPI card web component
│       │       ├── data-table.js ← Sortable/filterable table
│       │       └── toast.js      ← Notification system
│       └── assets/
│           └── logo.svg
│
├── src/                          ← EXISTING: ML pipeline (unchanged)
├── data/                         ← EXISTING: Data files
├── models/                       ← EXISTING: Trained model artifacts
├── reports/                      ← EXISTING: PDF generator
├── config.yaml                   ← EXISTING: Config
└── requirements.txt              ← UPDATED: + fastapi, uvicorn, websockets
```

---

## Design Language

### Visual Identity: "Neural Terminal"
- **NOT** a generic AI dashboard (no blue gradients, no floating cards on white)
- **IS** a dark-mode data terminal with glassmorphism panels
- Color palette:
  - Background: `#0a0b0f` (near-black)
  - Surface: `rgba(255,255,255,0.04)` (glass panels)
  - Accent: `#00ff88` (terminal green — primary actions)
  - Secondary: `#7c3aed` (violet — segments/clusters)
  - Warning: `#f59e0b` (amber — churn/at-risk)
  - Danger: `#ef4444` (red — lost customers)
  - Text: `#e2e8f0` (cool white)
  - Subtext: `#64748b` (slate)
- Typography: `JetBrains Mono` for data/numbers, `Inter` for prose
- Borders: `1px solid rgba(255,255,255,0.08)` with subtle glow on hover
- Charts: Dark-themed Chart.js + custom D3 scatter plot

### Unique UI Elements
1. **Animated segment rings** — concentric SVG rings that pulse based on CLV value
2. **Terminal-style KPI counters** — numbers count up with a typewriter cursor
3. **Hexagonal customer grid** — customers displayed as hex cells colored by segment
4. **Live probability heatmap** — D3-rendered BG/NBD alive probability matrix
5. **Segment DNA bars** — horizontal stacked bars showing RFM composition per segment
6. **Pipeline status ticker** — scrolling ticker showing last pipeline run stats

---

## Phase 1 — Backend API (FastAPI)

### Goals
- Wrap all existing ML pipeline outputs into REST endpoints
- Serve processed data from `data/processed/` and `models/`
- Provide pipeline trigger endpoint to re-run ML steps
- Enable PDF report download

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/overview` | KPI summary (total customers, revenue, avg CLV, churn %) |
| GET | `/api/segments` | All segment stats + profiles |
| GET | `/api/segments/{name}` | Single segment detail |
| GET | `/api/customers` | Paginated customer list with filters |
| GET | `/api/customers/{id}` | Single customer profile |
| GET | `/api/models/metrics` | Evaluation metrics (MAE, RMSE, silhouette) |
| GET | `/api/models/pca` | PCA scatter data |
| GET | `/api/models/alive-matrix` | BG/NBD probability alive matrix |
| GET | `/api/models/clv-distribution` | CLV histogram bins |
| POST | `/api/pipeline/run` | Trigger full ML pipeline re-run |
| GET | `/api/pipeline/status` | Last pipeline run status |
| GET | `/api/export/csv` | Download customer segments CSV |
| GET | `/api/export/pdf` | Generate and download PDF report |

### Files to Create
- `web/backend/main.py`
- `web/backend/schemas.py`
- `web/backend/routers/overview.py`
- `web/backend/routers/segments.py`
- `web/backend/routers/customers.py`
- `web/backend/routers/models.py`
- `web/backend/routers/pipeline.py`
- `web/backend/services/data_service.py`
- `web/backend/services/ml_service.py`
- `web/backend/services/report_service.py`

---

## Phase 2 — Frontend Shell & Design System

### Goals
- Build the SPA shell with client-side routing (no framework, vanilla JS)
- Implement the full CSS design system
- Create reusable web components

### Files to Create
- `web/frontend/index.html` — App shell with nav, sidebar, main content area
- `web/frontend/css/main.css` — Design tokens, layout, typography
- `web/frontend/css/components.css` — Cards, tables, badges, buttons
- `web/frontend/css/animations.css` — Keyframes, transitions, loading states
- `web/frontend/js/app.js` — Router, state, page loader
- `web/frontend/js/api.js` — Fetch wrapper with error handling
- `web/frontend/js/components/kpi-card.js` — Animated KPI counter component
- `web/frontend/js/components/data-table.js` — Sortable table component
- `web/frontend/js/components/toast.js` — Toast notification system

---

## Phase 3 — Overview Page

### Goals
- Display 4 animated KPI cards (customers, revenue, avg CLV, churn %)
- Segment distribution donut chart (Chart.js)
- CLV contribution bar chart per segment
- Revenue timeline sparkline
- Pipeline status ticker

### Files to Create
- `web/frontend/js/pages/overview.js`

---

## Phase 4 — Segments Page

### Goals
- Segment summary table with color-coded badges
- PCA scatter plot (D3.js — custom, not Chart.js)
- Segment DNA bars (RFM composition per segment)
- Animated segment rings visualization
- Segment detail modal on click

### Files to Create
- `web/frontend/js/pages/segments.js`
- `web/frontend/js/charts.js` (D3 scatter + segment rings)

---

## Phase 5 — Customer Explorer Page

### Goals
- Search bar with live filtering by CustomerID
- Segment filter dropdown
- Paginated customer table (sortable by CLV, recency, frequency)
- Customer detail panel (slide-in from right)
- Individual customer RFM radar chart
- Transaction history table

### Files to Create
- `web/frontend/js/pages/explorer.js`

---

## Phase 6 — Model Insights Page

### Goals
- BG/NBD probability alive heatmap (D3 — custom color scale)
- CLV distribution histogram
- Model evaluation metrics table (MAE, RMSE, log-likelihood)
- Clustering quality metrics with visual gauges
- Silhouette score gauge chart

### Files to Create
- `web/frontend/js/pages/insights.js`

---

## Phase 7 — Export Page

### Goals
- CSV download button (streams from `/api/export/csv`)
- PDF report generation with progress indicator
- Pipeline re-run trigger with live status updates
- Last run metadata display

### Files to Create
- `web/frontend/js/pages/export.js`

---

## Phase 8 — Integration & Polish

### Goals
- Wire all pages to live API
- Add loading skeletons for all data-fetching states
- Add error states and empty states
- Responsive layout (tablet + desktop)
- Final CSS polish and animation tuning
- Update `requirements.txt` with new dependencies
- Create `run.py` convenience launcher

### Files to Create/Update
- `web/run.py` — Starts FastAPI server
- `requirements.txt` — Add fastapi, uvicorn, python-multipart
- `README.md` — Updated setup and run instructions

---

## ML Models Used

| Model | Library | Purpose |
|-------|---------|---------|
| BG/NBD (Beta-Geometric/NBD) | `lifetimes` | Predicts expected future purchase count per customer |
| Gamma-Gamma | `lifetimes` | Predicts expected average monetary value per customer |
| K-Means | `scikit-learn` | Clusters customers into behavioral segments |
| PCA (2-component) | `scikit-learn` | Reduces feature space for 2D scatter visualization |
| StandardScaler | `scikit-learn` | Normalizes RFM + CLV features before clustering |

All models are pre-trained and serialized in `models/`. The web API loads them at startup and serves predictions without re-training on every request.

---

## Tech Stack Summary

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend | FastAPI + Uvicorn | Fast async Python API, auto OpenAPI docs |
| Data | Pandas + existing pipeline | Reuse all existing ML work |
| Frontend | Vanilla JS (ES6 modules) | No framework bloat, full control over UI |
| Charts | Chart.js + D3.js | Chart.js for standard charts, D3 for custom viz |
| Styling | Pure CSS (custom design system) | Unique look, no Tailwind/Bootstrap defaults |
| PDF | fpdf2 (existing) | Already implemented in reports/ |

---

## Running the Application

```bash
# Install new dependencies
pip install fastapi uvicorn python-multipart

# Start the backend API server
python web/run.py

# Open browser
# http://localhost:8000
```

---

## Milestones

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | FastAPI backend with all endpoints | ✅ Planned |
| 2 | Frontend shell + design system | ✅ Planned |
| 3 | Overview page | ✅ Planned |
| 4 | Segments page | ✅ Planned |
| 5 | Customer Explorer page | ✅ Planned |
| 6 | Model Insights page | ✅ Planned |
| 7 | Export page | ✅ Planned |
| 8 | Integration & polish | ✅ Planned |
