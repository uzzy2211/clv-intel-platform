# PRD — Customer Lifetime Value (CLV) Segmentation
> ML Subject Project | Version 1.0.0

---

## Changelog

| Version | Date       | Author     | Summary                              |
|---------|------------|------------|--------------------------------------|
| 1.0.0   | 2026-05-19 | Student    | Initial PRD draft — full scope       |

---

## Feature Log

| Feature ID | Feature Name                  | Status      | Version Added |
|------------|-------------------------------|-------------|---------------|
| F-001      | RFM Feature Engineering       | Planned     | 1.0.0         |
| F-002      | CLV Prediction (BG/NBD + GG)  | Planned     | 1.0.0         |
| F-003      | Customer Segmentation (K-Means / GMM) | Planned | 1.0.0      |
| F-004      | Segment Profiling & Labeling  | Planned     | 1.0.0         |
| F-005      | Churn Probability Score       | Planned     | 1.0.0         |
| F-006      | Streamlit Dashboard           | Planned     | 1.0.0         |
| F-007      | Model Evaluation & Reporting  | Planned     | 1.0.0         |
| F-008      | Export (CSV / PDF Report)     | Planned     | 1.0.0         |

---

## Project Context

### What Is This?
This is a machine learning project that segments customers based on their predicted **Customer Lifetime Value (CLV)**. The system uses transactional data to:
1. Engineer behavioral features (RFM)
2. Predict future CLV using probabilistic models
3. Cluster customers into actionable segments
4. Surface insights via an interactive dashboard

### Why It Matters
CLV segmentation helps businesses understand which customers are worth retaining, upselling, or re-engaging. This project demonstrates the full ML lifecycle: data wrangling → feature engineering → modeling → evaluation → visualization.

### Dataset
- **Primary**: [Online Retail II UCI Dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (real-world e-commerce transactions)
- **Fallback**: Synthetic transaction data generator (included in repo)
- Format: CSV with columns — `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`

### Scope Boundaries
- **In scope**: RFM feature engineering, CLV prediction, clustering, dashboard, model eval
- **Out of scope**: Real-time inference API, A/B testing framework, production deployment

---

## Tech Stack

### Language & Runtime
| Tool         | Version  | Purpose                        |
|--------------|----------|--------------------------------|
| Python       | 3.11+    | Primary language               |
| Jupyter      | Latest   | Exploration & EDA notebooks    |

### Data & Feature Engineering
| Library      | Version  | Purpose                        |
|--------------|----------|--------------------------------|
| pandas       | 2.x      | Data wrangling & RFM calc      |
| numpy        | 1.x      | Numerical ops                  |
| scikit-learn | 1.4+     | Preprocessing, clustering, eval|

### ML Models
| Library / Model     | Purpose                                        |
|---------------------|------------------------------------------------|
| `lifetimes` (PyPI)  | BG/NBD model (purchase frequency prediction)   |
| `lifetimes` (PyPI)  | Gamma-Gamma model (monetary value prediction)  |
| `scikit-learn`      | K-Means clustering, GMM, PCA for viz           |
| `xgboost` / `lgbm`  | Optional: supervised CLV regression baseline   |

### Visualization & Dashboard
| Library      | Purpose                                 |
|--------------|-----------------------------------------|
| matplotlib   | Static plots, EDA                       |
| seaborn      | Heatmaps, distribution plots            |
| plotly       | Interactive charts in dashboard         |
| streamlit    | Dashboard UI                            |

### Evaluation & Reporting
| Tool            | Purpose                               |
|-----------------|---------------------------------------|
| scikit-learn    | Silhouette score, Davies-Bouldin index|
| yellowbrick     | Cluster evaluation visualizations     |
| fpdf2 / reportlab | PDF report export                  |

### Dev Environment
| Tool         | Purpose                              |
|--------------|--------------------------------------|
| conda / venv | Environment management               |
| git          | Version control                      |
| black        | Code formatting                      |
| pytest       | Unit tests for feature engineering   |

---

## Architecture

```
clv-segmentation/
│
├── data/
│   ├── raw/                    # Original CSV (never modified)
│   ├── processed/              # Cleaned & feature-engineered data
│   └── synthetic/              # Synthetic data generator script
│
├── notebooks/
│   ├── 01_EDA.ipynb            # Exploratory data analysis
│   ├── 02_feature_engineering.ipynb
│   ├── 03_clv_modeling.ipynb   # BG/NBD + Gamma-Gamma
│   ├── 04_clustering.ipynb     # K-Means / GMM
│   └── 05_evaluation.ipynb     # Model and cluster evaluation
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Load, validate, clean raw data
│   ├── feature_engineering.py  # RFM + CLV feature pipeline
│   ├── clv_model.py            # BG/NBD + Gamma-Gamma wrapper
│   ├── clustering.py           # Clustering pipeline + label assignment
│   ├── evaluation.py           # Metrics computation
│   └── utils.py                # Shared helpers
│
├── dashboard/
│   └── app.py                  # Streamlit dashboard
│
├── reports/
│   └── generate_report.py      # PDF report generator
│
├── tests/
│   ├── test_feature_engineering.py
│   └── test_clv_model.py
│
├── requirements.txt
├── README.md
└── config.yaml                 # Central config (paths, hyperparams)
```

---

## ML Pipeline — Step by Step

### Step 1 — Data Ingestion & Cleaning (`data_loader.py`)
- Load CSV with `pandas`
- Drop rows with null `CustomerID`
- Remove cancelled invoices (InvoiceNo starting with 'C')
- Remove rows with `Quantity <= 0` or `UnitPrice <= 0`
- Parse `InvoiceDate` to datetime
- Add derived column: `TotalPrice = Quantity * UnitPrice`
- Filter to date range used as observation window

### Step 2 — RFM Feature Engineering (`feature_engineering.py`)
Compute per-customer metrics relative to a `snapshot_date` (max date + 1 day):

| Feature | Description |
|---------|-------------|
| **Recency** | Days since last purchase |
| **Frequency** | Number of unique purchase dates |
| **Monetary** | Average transaction value |
| `T` | Age of customer (days since first purchase) |

> Note: The `lifetimes` library uses a specific RFM summary format — use `summary_data_from_transaction_data()`.

### Step 3 — CLV Prediction (`clv_model.py`)
**Model A: BG/NBD (Beta-Geometric / Negative Binomial Distribution)**
- Predicts expected number of future transactions
- Inputs: frequency, recency, T
- Output: `predicted_purchases` over a future period (e.g. 90 days)

**Model B: Gamma-Gamma**
- Predicts expected average order value given alive customers
- Inputs: frequency, monetary
- Output: `expected_avg_profit`

**CLV = predicted_purchases × expected_avg_profit × margin × discount_factor**

### Step 4 — Clustering (`clustering.py`)
- Scale CLV + RFM features with `StandardScaler`
- Run K-Means for k = 2 to 8, pick optimal k via Elbow + Silhouette
- Optionally run GMM for soft assignment
- Apply PCA (2D) for scatter visualization
- Assign human-readable segment labels based on centroid analysis

**Segment Labels (example)**:
| Segment | Characteristics |
|---------|-----------------|
| Champions | High CLV, high frequency, recent |
| Loyal Customers | High frequency, moderate CLV |
| At Risk | Previously frequent, long lapse |
| Lost | Very low recency, low CLV |
| New Customers | Low T, moderate-high recent activity |
| Hibernating | Low recency, low frequency |

### Step 5 — Evaluation (`evaluation.py`)
- **Clustering**: Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz
- **CLV Model**: MAE / RMSE vs held-out actual revenue (if available), log-likelihood
- **Segment sanity check**: Revenue distribution, customer count per segment

---

## Dashboard Spec (`dashboard/app.py`)

### Pages
1. **Overview** — KPI cards: total customers, revenue, avg CLV, churn risk %
2. **Segments** — Donut chart (customer count), bar chart (CLV by segment), PCA scatter
3. **Customer Explorer** — Filter by segment, search by CustomerID, show individual profile
4. **Model Insights** — Frequency-recency heatmap, CLV distribution, alive probability matrix
5. **Export** — Download filtered CSV or generate PDF report

---

## Coding Rules

### General
- All source files live in `src/`. Notebooks are for exploration only — production logic must be in `src/`.
- Every function must have a docstring with: purpose, parameters, return value, and example.
- No magic numbers — all constants go in `config.yaml` and are loaded via a `Config` dataclass.
- Use type hints on all function signatures.
- Max function length: 40 lines. If longer, break it up.
- Never mutate input DataFrames — always return a copy.

### Naming Conventions
- Files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Notebook outputs (saved CSVs): `<step>_<description>.csv` e.g. `02_rfm_features.csv`

### Data Rules
- Raw data is read-only. Never write to `data/raw/`.
- Always validate schema on load (check required columns exist, dtypes match).
- Log dropped rows with counts and reason.
- Use `pd.Categorical` for segment labels for memory efficiency.

### Modeling Rules
- Fit models on `train` split, evaluate on `test` split (80/20 temporal split — earlier dates = train).
- Serialize fitted models with `joblib` into `models/` directory.
- Always log hyperparameters and metric results to a `runs.json` file.
- Never hardcode the number of clusters (k) — always determine programmatically via elbow/silhouette.

### Testing Rules
- All feature engineering functions must have a unit test.
- Tests use small synthetic DataFrames, not the real dataset.
- Run `pytest tests/` before every commit.

### Git Rules
- Branch naming: `feature/<name>`, `fix/<name>`, `notebook/<name>`
- Commit format: `[type] short description` — e.g. `[feat] add BG/NBD wrapper`, `[fix] remove cancelled invoices`
- Never commit raw data files or model binaries (add to `.gitignore`)

---

## Config Schema (`config.yaml`)

```yaml
data:
  raw_path: data/raw/online_retail_II.csv
  processed_path: data/processed/
  snapshot_date: null          # null = auto (max date + 1 day)
  observation_months: 12       # Training window
  prediction_days: 90          # CLV horizon

model:
  bgn_penalizer: 0.001
  gg_penalizer: 0.001
  clustering:
    k_range: [2, 8]
    algorithm: kmeans           # kmeans | gmm
    random_state: 42

dashboard:
  port: 8501
  theme: light

report:
  output_dir: reports/output/
  margin_rate: 0.10            # Assumed margin for CLV calc
  discount_rate: 0.01          # Monthly discount rate
```

---

## Evaluation Criteria (for ML Subject)

| Criterion                   | Weight | Notes |
|-----------------------------|--------|-------|
| Feature engineering quality | 20%    | RFM correctness, data cleaning rigor |
| Model selection & reasoning | 20%    | Why BG/NBD? Why K-Means vs GMM? |
| Clustering quality metrics  | 20%    | Silhouette, Davies-Bouldin reported |
| Visualization & insights    | 20%    | Dashboard, segment interpretation |
| Code quality & structure    | 20%    | Follows coding rules, tested, documented |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dataset too sparse (few repeat customers) | BG/NBD fails to converge | Use synthetic data fallback or different dataset |
| Optimal k is ambiguous | Weak segments | Use multiple metrics + business logic override |
| `lifetimes` library maintenance | Breaking changes | Pin version in requirements.txt |
| Streamlit version conflicts | Dashboard broken | Use virtual environment, pin all deps |

---

## Milestones

| Week | Milestone |
|------|-----------|
| 1    | Data loaded, cleaned, EDA complete, notebook 01 done |
| 2    | RFM features engineered, BG/NBD + GG fitted, CLV scores ready |
| 3    | Clustering complete, segments labeled, evaluation metrics computed |
| 4    | Dashboard built, report generator done, tests passing |
| 5    | Final cleanup, README updated, submission ready |

---

## References
- Fader, P.S., Hardie, B.G.S., Lee, K.L. (2005). "Counting Your Customers the Easy Way: An Alternative to the Pareto/NBD Model." *Marketing Science.*
- [`lifetimes` Python library docs](https://lifetimes.readthedocs.io/)
- [UCI Online Retail II Dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- Scikit-learn Clustering User Guide

---

*PRD maintained by the project owner. Update Changelog and Feature Log for every significant change.*
