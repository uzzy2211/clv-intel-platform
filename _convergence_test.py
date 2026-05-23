"""Verify BG/NBD and Gamma-Gamma both converge on the current dataset."""
import sys
sys.path.insert(0, ".")

import logging
import pandas as pd

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

from src.config import load_config
from src.data_loader import load_transaction_data, clean_data
from src.feature_engineering import compute_lifetimes_rfm, compute_standard_rfm
from src.clv_model import fit_bgnd_model, fit_gg_model

cfg = load_config()
print(f"Config  bgn_penalizer={cfg.model.bgn_penalizer}  gg_penalizer={cfg.model.gg_penalizer}")

df  = load_transaction_data(cfg)
df  = clean_data(df)
snap = df["InvoiceDate"].max() + pd.Timedelta(days=1)
std  = compute_standard_rfm(df, snap)
lt   = compute_lifetimes_rfm(df, snap)
rfm  = std.join(lt, how="inner")
print(f"Dataset {len(df):,} transactions  →  {len(rfm):,} customers")

# BG/NBD
bgf = fit_bgnd_model(rfm, cfg.model.bgn_penalizer)
p   = bgf.params_
print(f"BG/NBD  OK  r={p['r']:.4f}  alpha={p['alpha']:.4f}  a={p['a']:.4f}  b={p['b']:.4f}")

# Gamma-Gamma
ggf = fit_gg_model(rfm, cfg.model.gg_penalizer)
p   = ggf.params_
print(f"GG      OK  p={p['p']:.4f}  q={p['q']:.4f}  v={p['v']:.4f}")

print("\nBOTH MODELS CONVERGED — pipeline is ready.")
