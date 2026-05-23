# CLV Intelligence Platform

> Customer Lifetime Value Segmentation — Full-Stack ML Web Application

A production-grade web platform that combines probabilistic ML models (BG/NBD + Gamma-Gamma) with K-Means clustering to segment customers by predicted lifetime value, served through a custom dark-terminal web UI.

---

## Quick Start

```bash
# 1. Activate the virtual environment
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the platform
python web/run.py

# 4. Open in browser
#    http://localhost:8000
#    API docs: http://localhost:8000/api/docs
```

---

## Architecture

```
Antigravity/
├── web/
│   ├── backend/              FastAPI REST API
│   │   ├── main.py           App entry point + lifespan
│   │   ├── schemas.py        Pydantic response models
│   │   ├── routers/          One file per API domain
│   │   └── services/         Data loading, ML, PDF
│   ├── frontend/             Vanilla JS SPA
│   │   ├── index.html        App shell
│   │   ├── css/              Design system (Neural Terminal)
│   │   └── js/               Router, charts, pages
│   └── run.py                Server launcher
│
├── src/                      ML pipeline (Python)
│   ├── data_loader.py        Ingestion & cleaning
│   ├── feature_engineering.py  RFM features
│   ├── clv_model.py          BG/NBD + Gamma-Gamma
│   ├── clustering.py         K-Means / GMM
│   └── evaluation.py         Metrics
│
├── data/
│   ├── processed/            Pipeline outputs (CSV)
│   └── synthetic/            Synthetic data generator
│
├── models/                   Serialized model artifacts
├── reports/                  PDF report generator
├── config.yaml               Central configuration
└── IMPLEMENTATION_PLAN.md    Phase-by-phase build plan
```

---

## ML Models

| Model | Library | Purpose |
|-------|---------|---------|
| **BG/NBD** | `lifetimes` | Predicts expected future purchase count per customer |
| **Gamma-Gamma** | `lifetimes` | Predicts expected average monetary value |
| **K-Means** | `scikit-learn` | Clusters customers into behavioral segments |
| **PCA (2D)** | `scikit-learn` | Dimensionality reduction for scatter visualization |
| **StandardScaler** | `scikit-learn` | Normalizes RFM + CLV features before clustering |

---

## Web Platform Pages

| Page | URL | Description |
|------|-----|-------------|
| Overview | `/#overview` | KPI cards, segment donut, CLV bar chart |
| Segments | `/#segments` | Segment table, PCA scatter, DNA bars, rings |
| Explorer | `/#explorer` | Paginated customer table, detail panel, radar chart |
| Model Insights | `/#insights` | BG/NBD heatmap, CLV histogram, clustering metrics |
| Export | `/#export` | CSV/PDF download, pipeline re-run control |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/overview` | KPIs + segment shares |
| GET | `/api/segments` | All segment profiles + clustering metrics |
| GET | `/api/segments/{name}` | Single segment detail |
| GET | `/api/customers` | Paginated customer list (filter, sort, search) |
| GET | `/api/customers/{id}` | Single customer full profile |
| GET | `/api/models/metrics` | MAE, RMSE, log-likelihood, silhouette |
| GET | `/api/models/pca` | PCA scatter data (992 points) |
| GET | `/api/models/alive-matrix` | BG/NBD P(alive) heatmap matrix |
| GET | `/api/models/clv-distribution` | CLV histogram bins |
| POST | `/api/pipeline/run` | Trigger full ML pipeline re-run |
| GET | `/api/pipeline/status` | Last run metadata |
| GET | `/api/export/csv` | Download customer segments CSV |
| GET | `/api/export/pdf` | Generate + download PDF report |

---

## Running the ML Pipeline Manually

```bash
# Generate synthetic data (if no real dataset)
python data/synthetic/generate_synthetic_data.py

# Run each step individually
python -m src.feature_engineering    # → data/processed/02_rfm_features.csv
python -m src.clv_model              # → data/processed/03_clv_predictions.csv
python -m src.clustering             # → data/processed/04_customer_segments.csv
python -m src.evaluation             # → models/evaluation_metrics.json

# Or trigger via the web UI: Export page → Run Pipeline
```

---

## Design System

The frontend uses a **Neural Terminal** aesthetic — not a generic AI dashboard:

- Background: `#0a0b0f` near-black
- Accent: `#00ff88` terminal green
- Typography: `JetBrains Mono` for data, `Inter` for prose
- Glass panels with `rgba(255,255,255,0.03)` surfaces
- Unique visualizations: segment rings, DNA bars, D3 PCA scatter, D3 heatmap

---

## Configuration

All ML hyperparameters and paths live in `config.yaml`:

```yaml
data:
  prediction_days: 90        # CLV horizon
  observation_months: 12     # Training window

model:
  bgn_penalizer: 0.001       # BG/NBD regularization
  gg_penalizer: 0.001        # Gamma-Gamma regularization
  clustering:
    k_range: [2, 8]          # Optimal k search range
    algorithm: kmeans         # kmeans | gmm

report:
  margin_rate: 0.10          # Gross margin for CLV calc
  discount_rate: 0.01        # Monthly discount rate
```
