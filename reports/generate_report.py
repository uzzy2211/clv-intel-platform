"""
generate_report.py — PDF Executive Summary Generator

White-canvas design: all text is high-contrast dark on white paper.
Strategic Recommendations are generated from actual segment data so
they are always populated regardless of cluster label names.

Usage:
    python reports/generate_report.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
from fpdf import FPDF, XPos, YPos

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# High-contrast colour palette — optimised for WHITE paper
# ---------------------------------------------------------------------------
# Primary text / headings
C_BLACK    = (0,   0,   0)       # pure black — headings, table values
C_CHARCOAL = (26,  26,  26)      # #1A1A1A — body paragraphs
C_DARK     = (51,  51,  51)      # #333333 — secondary body text
C_MID      = (80,  80,  80)      # #505050 — table sub-labels
C_MUTED    = (120, 120, 120)     # #787878 — footnotes, captions

# Accent / brand
C_ACCENT   = (0,   120, 90)      # dark teal — section titles, accent bars
C_ACCENT2  = (0,   90,  160)     # dark blue — alternate accent
C_GOLD     = (160, 100, 0)       # dark amber — recommendation labels

# Backgrounds (light fills for tables)
C_WHITE    = (255, 255, 255)
C_ROW_ALT  = (245, 247, 250)     # very light grey — alternating table rows
C_HEADER   = (30,  80,  60)      # dark teal fill — table header row
C_COVER_BG = (15,  17,  26)      # near-black — cover page only

# ---------------------------------------------------------------------------
# Recommendation playbook — keyed by tier, not by segment name
# ---------------------------------------------------------------------------
# Tiers are assigned dynamically from actual cluster stats so this always
# produces output regardless of what K-Means named the clusters.

_TIER_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "high": {
        "label":    "High Value Customers (Wholesale / VIP)",
        "headline": "Protect revenue concentration and deepen wholesale relationships",
        "paras": [
            "High-value customers -- often wholesale accounts or bulk buyers -- represent "
            "a disproportionate share of total revenue. A single account in this tier "
            "may generate more revenue than hundreds of retail customers combined. "
            "Losing even one is a material business risk.",
            "Strategic focus areas:",
            "  1. Dedicated account management: Assign a named account manager to each "
            "     wholesale relationship. Quarterly business reviews should cover volume "
            "     forecasts, pricing structures, and upcoming product roadmaps.",
            "  2. Tiered procurement pricing: Implement volume-based discount ladders "
            "     (e.g. 5% at 100 units, 12% at 500 units, 20% at 1,000+ units) to "
            "     incentivise larger order sizes and lock in forward commitments.",
            "  3. Exclusive early access: Offer pre-launch product access, private "
            "     inventory reservations, and priority fulfilment SLAs to reinforce "
            "     the premium nature of the wholesale relationship.",
            "  4. Retention monitoring: Flag any account whose order frequency drops "
            "     below its 90-day baseline. Trigger an outreach call within 48 hours "
            "     before the lapse becomes a churn event.",
        ],
    },
    "medium": {
        "label":    "Loyal / Regular Customers",
        "headline": "Convert consistent buyers into high-value champions",
        "paras": [
            "Loyal customers purchase regularly but have not yet reached the spending "
            "levels of the top tier. They represent the highest-potential growth cohort "
            "because the relationship is already established.",
            "Strategic focus areas:",
            "  1. Loyalty tier upgrade path: Show customers exactly how many points or "
            "     purchases separate them from the next reward tier. Progress visibility "
            "     drives incremental spend.",
            "  2. Cross-sell and bundle campaigns: Use purchase history to recommend "
            "     complementary product categories. Personalised bundles outperform "
            "     generic promotions by 3-5x in conversion rate.",
            "  3. Referral programme: Loyal customers are the most credible brand "
            "     advocates. A structured referral incentive (e.g. store credit per "
            "     successful referral) converts satisfaction into acquisition.",
        ],
    },
    "atrisk": {
        "label":    "At-Risk Customers",
        "headline": "Intervene before lapse becomes permanent churn",
        "paras": [
            "At-risk customers were previously active but their purchase recency has "
            "deteriorated. Without intervention, they will migrate to the lost segment "
            "within one to two purchase cycles.",
            "Strategic focus areas:",
            "  1. Triggered win-back sequence: Deploy a 3-email sequence -- "
            "     (a) 'We noticed you haven't visited recently', "
            "     (b) a time-limited 15% discount, "
            "     (c) a final 'last chance' offer -- spaced 5 days apart.",
            "  2. Churn reason survey: A short 2-question survey (product quality, "
            "     price, or service issue?) provides actionable data and signals to "
            "     the customer that their feedback is valued.",
            "  3. Reactivation incentive: Free shipping or a small gift-with-purchase "
            "     lowers the friction of a return visit without deep discounting.",
        ],
    },
    "lost": {
        "label":    "Low Value / Lost Customers (Retail Re-engagement)",
        "headline": "Programmatic re-engagement and win-back pipeline",
        "paras": [
            "Lost and low-value retail customers have either lapsed entirely or never "
            "developed a repeat-purchase habit. The cost of re-engagement must be "
            "weighed against the expected lifetime value of a recovered customer.",
            "Strategic focus areas:",
            "  1. Automated re-engagement pipeline: Configure a 4-step email automation "
            "     triggered at 60, 90, 120, and 180 days of inactivity. Each step "
            "     escalates the offer: content email, 10% discount, 20% discount, "
            "     final win-back with free shipping.",
            "  2. Cart and browse abandonment triggers: For customers who return to "
            "     the site but do not convert, deploy real-time abandonment emails "
            "     within 1 hour. These recover 5-15% of abandoned sessions.",
            "  3. Win-back promotional triggers: Seasonal moments (Black Friday, "
            "     end-of-year clearance) provide a natural re-entry point. Segment "
            "     this cohort into a dedicated promotional list for these events.",
            "  4. Budget reallocation: Customers who do not respond after 180 days "
            "     should be suppressed from standard campaigns. Reallocate that "
            "     marketing spend toward acquisition of new customers.",
        ],
    },
    "new": {
        "label":    "New Customers",
        "headline": "Drive a second purchase and establish the repeat habit",
        "paras": [
            "New customers have made their first purchase but have not yet demonstrated "
            "repeat behaviour. The critical window is the first 30 days -- customers "
            "who make a second purchase within this period have a 3x higher 12-month "
            "retention rate.",
            "Strategic focus areas:",
            "  1. Welcome series: A 3-email onboarding sequence covering brand story, "
            "     bestsellers, and a second-purchase incentive (e.g. 10% off next order).",
            "  2. Preference capture: Ask new customers about their interests and "
            "     purchase intent. Use this data to personalise all future communications.",
            "  3. Loyalty programme enrolment: Invite new customers to join the loyalty "
            "     programme at the point of first purchase to establish a long-term "
            "     engagement framework from day one.",
        ],
    },
    "hibernating": {
        "label":    "Hibernating / Dormant Customers",
        "headline": "Low-cost reactivation through seasonal and event triggers",
        "paras": [
            "Hibernating customers purchased in the past but have been inactive for "
            "an extended period. They are not yet lost -- they simply need a relevant "
            "reason to return.",
            "Strategic focus areas:",
            "  1. Seasonal reactivation: Map this segment to key retail calendar events "
            "     (January sales, summer clearance, Black Friday). A single well-timed "
            "     campaign can reactivate 8-15% of dormant customers.",
            "  2. Low-friction offers: Free shipping or a small gift-with-purchase "
            "     removes the psychological barrier to a return visit without "
            "     training customers to expect deep discounts.",
            "  3. Frequency capping: Limit email sends to this segment to 1-2 per "
            "     month to avoid list fatigue and unsubscribe spikes.",
        ],
    },
}


# ---------------------------------------------------------------------------
# Tier assignment — data-driven, works for any cluster label
# ---------------------------------------------------------------------------

def _safe(text: str) -> str:
    """Sanitise a string for Helvetica (Latin-1) rendering.

    Replaces common Unicode punctuation with ASCII equivalents so fpdf
    never raises FPDFUnicodeEncodingException on the recommendations page.
    """
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u00a0": " ",    # non-breaking space
        "\u2022": "-",    # bullet
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Final safety net: drop any remaining non-Latin-1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")

def _assign_tier(
    name: str,
    avg_clv: float,
    avg_recency: float,
    avg_frequency: float,
    all_clvs: List[float],
) -> str:
    """Assign a recommendation tier from actual segment statistics.

    Falls back to stat-based thresholds when the segment name does not
    match any known label, so recommendations are always generated.
    """
    n = name.lower()

    # Name-based shortcuts
    if any(k in n for k in ("champion", "high value", "vip", "wholesale", "premium")):
        return "high"
    if any(k in n for k in ("loyal", "regular", "active", "medium")):
        return "medium"
    if any(k in n for k in ("at risk", "at-risk", "atrisk", "risk")):
        return "atrisk"
    if any(k in n for k in ("lost", "churned", "inactive", "low value", "low-value")):
        return "lost"
    if any(k in n for k in ("new", "prospect", "first")):
        return "new"
    if any(k in n for k in ("hibernat", "dormant", "lapsed", "sleeping")):
        return "hibernating"

    # Stat-based fallback
    if not all_clvs:
        return "medium"
    sorted_clvs = sorted(all_clvs, reverse=True)
    n_segs = len(sorted_clvs)
    top_threshold    = sorted_clvs[max(0, int(n_segs * 0.25) - 1)]
    bottom_threshold = sorted_clvs[min(n_segs - 1, int(n_segs * 0.75))]

    if avg_clv >= top_threshold:
        return "high"
    if avg_recency > 180 and avg_frequency <= 2:
        return "lost"
    if avg_recency > 90:
        return "atrisk"
    if avg_frequency <= 1 and avg_recency < 60:
        return "new"
    if avg_clv <= bottom_threshold and avg_recency > 60:
        return "hibernating"
    return "medium"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_metrics(path: str = "models/evaluation_metrics.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning(f"Metrics file not found at {path}.")
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_segments(path: str = "data/processed/04_customer_segments.csv") -> pd.DataFrame:
    if not os.path.exists(path):
        logger.warning(f"Segments file not found at {path}.")
        return pd.DataFrame()
    return pd.read_csv(path, index_col="CustomerID")


# ---------------------------------------------------------------------------
# PDF class — white-canvas, high-contrast
# ---------------------------------------------------------------------------

class CLVReport(FPDF):
    """Custom FPDF subclass. All text is dark on white for print legibility."""

    def header(self) -> None:
        # Thin accent bar at top
        self.set_fill_color(*C_ACCENT)
        self.rect(0, 0, 210, 3, style="F")
        # White header band
        self.set_fill_color(*C_WHITE)
        self.rect(0, 3, 210, 16, style="F")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ACCENT)
        self.set_xy(10, 5)
        self.cell(0, 8, "CLV Segmentation - Executive Summary", align="L")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_MUTED)
        self.set_xy(0, 5)
        self.cell(200, 8, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="R")
        # Separator line
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.3)
        self.line(10, 19, 200, 19)
        self.ln(14)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    # ── Layout helpers ─────────────────────────────────────────────

    def section_title(self, title: str) -> None:
        self.ln(5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*C_ACCENT)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_fill_color(*C_ACCENT)
        self.rect(self.l_margin, self.get_y(), 190, 0.5, style="F")
        self.ln(4)

    def sub_heading(self, text: str) -> None:
        """Bold dark sub-heading inside a section."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_BLACK)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_text(self, text: str) -> None:
        """High-contrast body paragraph — dark charcoal on white."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*C_CHARCOAL)
        self.multi_cell(0, 5, _safe(text))
        self.ln(2)

    def indented_text(self, text: str, indent: float = 6.0) -> None:
        """Indented body text for bullet-style paragraphs."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*C_DARK)
        x = self.get_x() + indent
        self.set_x(x)
        self.multi_cell(190 - indent, 5, _safe(text))
        self.ln(1)

    def kpi_row(self, items: List[Tuple[str, str]]) -> None:
        """KPI cards — dark text on light grey fill."""
        card_w = 190 / len(items)
        start_x = self.l_margin
        y_top = self.get_y()

        for label, value in items:
            # Card background
            self.set_fill_color(*C_ROW_ALT)
            self.rect(start_x, y_top, card_w - 2, 22, style="F")
            # Accent left bar
            self.set_fill_color(*C_ACCENT)
            self.rect(start_x, y_top, 2, 22, style="F")
            # Label
            self.set_xy(start_x + 4, y_top + 3)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*C_MUTED)
            self.cell(card_w - 8, 5, label.upper(), align="L")
            # Value — solid black
            self.set_xy(start_x + 4, y_top + 9)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*C_BLACK)
            self.cell(card_w - 8, 8, str(value), align="L")
            start_x += card_w

        self.set_y(y_top + 26)

    def data_table(self, headers: List[str], rows: List[List[str]]) -> None:
        """Table with dark header, alternating light rows, dark text."""
        col_w = 190 / len(headers)

        # Header row — dark fill, white text
        self.set_fill_color(*C_HEADER)
        self.set_text_color(*C_WHITE)
        self.set_font("Helvetica", "B", 8)
        for h in headers:
            self.cell(col_w, 7, h, border=0, fill=True, align="C")
        self.ln()

        # Data rows — alternating white / light grey, BLACK text
        self.set_font("Helvetica", "", 8)
        for i, row in enumerate(rows):
            fill_color = C_ROW_ALT if i % 2 == 0 else C_WHITE
            self.set_fill_color(*fill_color)
            self.set_text_color(*C_BLACK)
            for cell in row:
                self.cell(col_w, 6, str(cell), border=0, fill=True, align="C")
            self.ln()
        self.ln(3)


# ---------------------------------------------------------------------------
# Report section builders
# ---------------------------------------------------------------------------

def build_cover(pdf: CLVReport) -> None:
    """Cover page — dark background, white/accent text."""
    pdf.set_fill_color(*C_COVER_BG)
    pdf.rect(0, 0, 210, 297, style="F")

    pdf.set_fill_color(*C_ACCENT)
    pdf.rect(0, 88, 6, 124, style="F")

    pdf.set_xy(20, 100)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 14, "Customer Lifetime Value", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(20, 116)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(29, 209, 161)   # teal accent
    pdf.cell(0, 14, "Segmentation Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(20, 142)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(140, 148, 170)
    pdf.multi_cell(
        170, 6,
        "An end-to-end machine learning analysis combining BG/NBD probabilistic "
        "purchase modelling, Gamma-Gamma monetary value estimation, and K-Means "
        "customer clustering to surface actionable segments and revenue forecasts.",
    )

    pdf.set_xy(20, 196)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 199, 44)
    pdf.cell(0, 6, f"Report Date: {datetime.now().strftime('%B %d, %Y')}")


def build_overview(pdf: CLVReport, metrics: Dict[str, Any], df_seg: pd.DataFrame) -> None:
    pdf.section_title("Executive Overview")
    pdf.body_text(
        "This report summarises the outputs of the CLV segmentation pipeline. "
        "Customers were grouped into behavioural segments using probabilistic "
        "purchase and monetary models. The key metrics below provide a high-level "
        "view of cohort health, predicted value, and model accuracy."
    )

    total_customers = len(df_seg) if not df_seg.empty else "N/A"
    avg_clv  = f"${df_seg['clv'].mean():,.2f}" if "clv" in df_seg.columns else "N/A"
    num_segs = df_seg["segment"].nunique() if "segment" in df_seg.columns else "N/A"
    sil      = metrics.get("clustering_evaluation", {}).get("silhouette_score")
    sil_str  = f"{sil:.3f}" if sil is not None else "N/A"

    pdf.kpi_row([
        ("Total Customers", f"{total_customers:,}" if isinstance(total_customers, int) else total_customers),
        ("Avg Predicted CLV", avg_clv),
        ("No. of Segments", str(num_segs)),
        ("Silhouette Score", sil_str),
    ])


def build_clv_metrics(pdf: CLVReport, metrics: Dict[str, Any]) -> None:
    pdf.section_title("CLV Model Evaluation")
    pdf.body_text(
        "The BG/NBD model was trained on an 80% temporal training window and evaluated "
        "on the remaining 20% holdout period. Predictions for expected purchases and "
        "revenue were compared against actual observed values."
    )
    clv_m = metrics.get("clv_model_evaluation", {})

    def _fmt(key: str, decimals: int = 4, prefix: str = "") -> str:
        v = clv_m.get(key)
        if v is None:
            return "N/A"
        return f"{prefix}{v:,.{decimals}f}"

    rows = [
        ["BG/NBD Log-Likelihood",       _fmt("bgnbd_log_likelihood")],
        ["Gamma-Gamma Log-Likelihood",   _fmt("gamma_gamma_log_likelihood")],
        ["Holdout Period (days)",         str(clv_m.get("test_holdout_days", "N/A"))],
        ["Purchases MAE",                _fmt("purchases_mae")],
        ["Purchases RMSE",               _fmt("purchases_rmse")],
        ["Revenue MAE",                  _fmt("revenue_mae", 2, "$")],
        ["Revenue RMSE",                 _fmt("revenue_rmse", 2, "$")],
    ]
    pdf.data_table(["Metric", "Value"], rows)


def build_clustering_metrics(pdf: CLVReport, metrics: Dict[str, Any]) -> None:
    pdf.section_title("Clustering Evaluation")
    pdf.body_text(
        "Internal clustering validity indices assess the quality of customer segments. "
        "A higher Silhouette Score and Calinski-Harabasz Index, along with a lower "
        "Davies-Bouldin Index, indicate well-separated, compact clusters."
    )
    cl_m = metrics.get("clustering_evaluation", {})
    rows = [
        ["Silhouette Score",        f"{cl_m.get('silhouette_score', 0):.4f}"],
        ["Davies-Bouldin Index",    f"{cl_m.get('davies_bouldin_index', 0):.4f}"],
        ["Calinski-Harabasz Index", f"{cl_m.get('calinski_harabasz_index', 0):.2f}"],
    ]
    pdf.data_table(["Index", "Score"], rows)


def build_segment_profiles(pdf: CLVReport, metrics: Dict[str, Any]) -> None:
    pdf.section_title("Segment Profiles")
    pdf.body_text(
        "Each customer segment is profiled by its average behavioural and financial "
        "characteristics. Recency = days since last purchase; Frequency = unique "
        "purchase dates; Monetary = average transaction value."
    )
    profiles = metrics.get("segment_profiles", {})
    if not profiles:
        pdf.body_text("No segment profiles available in evaluation_metrics.json.")
        return

    headers = ["Segment", "Customers", "Avg Recency", "Avg Freq", "Avg Monetary", "Avg CLV"]
    rows = [
        [
            name,
            str(p.get("customer_count", "N/A")),
            f"{p.get('average_recency', 0):.1f}d",
            f"{p.get('average_frequency', 0):.1f}",
            f"${p.get('average_monetary', 0):,.2f}",
            f"${p.get('average_clv', 0):,.2f}",
        ]
        for name, p in profiles.items()
    ]
    pdf.data_table(headers, rows)


def build_recommendations(pdf: CLVReport, metrics: Dict[str, Any]) -> None:
    """
    Build the Strategic Recommendations page.

    Generates a recommendation block for every segment found in the data.
    Uses data-driven tier assignment so it always produces content — even
    for unusual cluster shapes like 1 wholesale vs 4,337 retail customers.
    """
    pdf.section_title("Strategic Recommendations")
    pdf.body_text(
        "The following recommendations are derived from the actual cluster statistics "
        "of this dataset. Each segment is assigned a strategic tier based on its "
        "average CLV, recency, and purchase frequency relative to the other segments."
    )

    profiles = metrics.get("segment_profiles", {})

    # ── Build segment list from profiles ──────────────────────────
    # Fall back to generic two-segment recommendations if profiles is empty
    if not profiles:
        _render_fallback_recommendations(pdf)
        return

    # Compute tier for each segment
    all_clvs = [p.get("average_clv", 0.0) for p in profiles.values()]
    segment_tiers = []
    for seg_name, p in profiles.items():
        tier = _assign_tier(
            name=seg_name,
            avg_clv=p.get("average_clv", 0.0),
            avg_recency=p.get("average_recency", 0.0),
            avg_frequency=p.get("average_frequency", 0.0),
            all_clvs=all_clvs,
        )
        segment_tiers.append((seg_name, p, tier))

    # Sort: high → medium → new → atrisk → hibernating → lost
    tier_order = {"high": 0, "medium": 1, "new": 2, "atrisk": 3, "hibernating": 4, "lost": 5}
    segment_tiers.sort(key=lambda x: tier_order.get(x[2], 99))

    # ── Render one block per segment ──────────────────────────────
    for seg_name, p, tier in segment_tiers:
        playbook = _TIER_PLAYBOOK.get(tier, _TIER_PLAYBOOK["medium"])

        # Segment label bar
        pdf.ln(3)
        pdf.set_fill_color(*C_ROW_ALT)
        y = pdf.get_y()
        pdf.rect(pdf.l_margin, y, 190, 8, style="F")
        pdf.set_fill_color(*C_ACCENT)
        pdf.rect(pdf.l_margin, y, 3, 8, style="F")
        pdf.set_xy(pdf.l_margin + 5, y + 1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_BLACK)
        cust_count = p.get("customer_count", 0)
        avg_clv_val = p.get("average_clv", 0.0)
        pdf.cell(
            0, 6,
            _safe(f"{seg_name}  |  {cust_count:,} customers  |  Avg CLV: ${avg_clv_val:,.2f}"),
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.ln(2)

        # Headline
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*C_ACCENT)
        pdf.multi_cell(190, 6, _safe(playbook["headline"]))
        pdf.ln(1)

        # Paragraphs — wrapped safely within margins
        for para in playbook["paras"]:
            if para.startswith("  "):
                # Numbered action item — indented
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.multi_cell(185, 5, _safe(para.strip()))
            else:
                # Regular paragraph
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_CHARCOAL)
                pdf.multi_cell(190, 5, _safe(para))
            pdf.ln(1)

        pdf.ln(3)


def _render_fallback_recommendations(pdf: CLVReport) -> None:
    """
    Render hardcoded recommendations when no segment profiles exist.
    Covers the two most common cluster outcomes for retail datasets.
    """
    fallback_segments = [
        ("High Value Customers (Wholesale / VIP)", "high"),
        ("Low Value / Lost Customers (Retail)", "lost"),
    ]
    for seg_name, tier in fallback_segments:
        playbook = _TIER_PLAYBOOK[tier]

        pdf.ln(3)
        pdf.set_fill_color(*C_ROW_ALT)
        y = pdf.get_y()
        pdf.rect(pdf.l_margin, y, 190, 8, style="F")
        pdf.set_fill_color(*C_ACCENT)
        pdf.rect(pdf.l_margin, y, 3, 8, style="F")
        pdf.set_xy(pdf.l_margin + 5, y + 1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_BLACK)
        pdf.cell(0, 6, _safe(seg_name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*C_ACCENT)
        pdf.multi_cell(190, 6, _safe(playbook["headline"]))
        pdf.ln(1)

        for para in playbook["paras"]:
            if para.startswith("  "):
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.multi_cell(185, 5, _safe(para.strip()))
            else:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_CHARCOAL)
                pdf.multi_cell(190, 5, _safe(para))
            pdf.ln(1)
        pdf.ln(3)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_report(
    metrics_path: str = "models/evaluation_metrics.json",
    segments_path: str = "data/processed/04_customer_segments.csv",
    output_path: str = "reports/output/clv_segmentation_report.pdf",
) -> None:
    """Compile all pipeline outputs into a styled PDF executive summary.

    Args:
        metrics_path: Path to evaluation_metrics.json.
        segments_path: Path to 04_customer_segments.csv.
        output_path: Destination path for the generated PDF.

    Example:
        >>> generate_report()
    """
    logger.info("Loading data for report generation...")
    metrics = load_metrics(metrics_path)
    df_seg  = load_segments(segments_path)

    pdf = CLVReport(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(10, 22, 10)

    # Page 1 — Cover (no header/footer)
    pdf.add_page()
    build_cover(pdf)

    # Page 2 — Overview KPIs + CLV model metrics
    pdf.add_page()
    build_overview(pdf, metrics, df_seg)
    build_clv_metrics(pdf, metrics)

    # Page 3 — Clustering metrics + Segment profiles
    pdf.add_page()
    build_clustering_metrics(pdf, metrics)
    build_segment_profiles(pdf, metrics)

    # Page 4 — Strategic Recommendations (always populated)
    pdf.add_page()
    build_recommendations(pdf, metrics)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    logger.info(f"Report saved to {output_path}")
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_report()
