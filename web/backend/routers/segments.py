"""
segments.py — Segments API Router

Provides segment profiles, clustering metrics, individual segment details,
and data-driven strategic recommendations for every segment.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from schemas import (
    Recommendation,
    RecommendationsResponse,
    SegmentProfile,
    SegmentsResponse,
)
from services.data_service import get_data_service

router = APIRouter(prefix="/api/segments", tags=["segments"])

# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

# Playbook: maps a segment tier to headline + action list + visual tokens.
# Tiers are assigned dynamically from actual cluster stats, so this works
# regardless of how many clusters K-Means produces or how skewed they are.
_PLAYBOOK = {
    "high": {
        "headline": "Protect and grow your highest-value customers",
        "actions": [
            "Exclusive VIP loyalty programs and high-volume wholesale discounts.",
            "Dedicated account managers and priority customer support.",
            "Early access to new products and private sale events.",
            "Personalised upsell recommendations based on purchase history.",
            "Annual business review meetings for B2B / wholesale accounts.",
        ],
        "color": "#00a85a",
        "icon": "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    },
    "medium": {
        "headline": "Convert loyal buyers into high-value champions",
        "actions": [
            "Tiered loyalty rewards that unlock at the next spend threshold.",
            "Personalised cross-sell bundles based on category affinity.",
            "Subscription or auto-replenishment offers for repeat SKUs.",
            "Referral incentives -- reward customers who bring new buyers.",
            "Targeted email sequences highlighting premium product lines.",
        ],
        "color": "#0ea5e9",
        "icon": "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
    },
    "atrisk": {
        "headline": "Re-engage customers before they churn permanently",
        "actions": [
            "Time-sensitive win-back offers (e.g. 20% off, valid 7 days).",
            "Post-purchase satisfaction surveys to identify friction points.",
            "Triggered email sequence: 'We miss you' → discount → last chance.",
            "Investigate product or service issues driving the lapse.",
            "Offer flexible payment terms or instalment options for high-AOV items.",
        ],
        "color": "#f59e0b",
        "icon": "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
    },
    "lost": {
        "headline": "Final re-engagement push -- then reallocate budget",
        "actions": [
            "Re-engagement email campaigns with win-back incentives.",
            "Cart-abandonment and browse-abandonment discount triggers.",
            "One-time deep discount (30-40%) as a last-chance offer.",
            "Suppress from standard marketing to reduce unsubscribe rate.",
            "Reallocate acquisition budget toward high and medium tiers.",
        ],
        "color": "#ef4444",
        "icon": "M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1",
    },
    "new": {
        "headline": "Onboard new customers and drive a second purchase",
        "actions": [
            "Welcome series: brand story → bestsellers → first-purchase discount.",
            "Onboarding checklist or product guide to reduce time-to-value.",
            "Second-purchase incentive triggered 7 days after first order.",
            "Collect preference data early to personalise future campaigns.",
            "Invite to loyalty programme at the point of first purchase.",
        ],
        "color": "#7c3aed",
        "icon": "M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z",
    },
    "hibernating": {
        "headline": "Reactivate dormant customers with low-friction offers",
        "actions": [
            "Seasonal reactivation campaigns tied to key retail moments.",
            "Low-commitment offers: free shipping, small gift with purchase.",
            "Product update emails highlighting new arrivals since last visit.",
            "SMS or push notification for flash sales (higher open rates).",
            "Suppress from high-frequency email to avoid list fatigue.",
        ],
        "color": "#94a3b8",
        "icon": "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z",
    },
}


def _assign_tier(name: str, avg_clv: float, avg_recency: float,
                 avg_frequency: float, all_clvs: List[float]) -> str:
    """
    Assign a recommendation tier to a segment based on its actual stats.

    Uses percentile thresholds so the logic works for any number of clusters
    and any CLV distribution — including highly skewed datasets (e.g. 1
    wholesale customer vs 4,337 retail customers).

    Args:
        name: Segment label from K-Means.
        avg_clv: Average predicted CLV for this segment.
        avg_recency: Average days since last purchase.
        avg_frequency: Average purchase frequency.
        all_clvs: List of avg_clv values across all segments (for percentile).

    Returns:
        Tier string: "high" | "medium" | "atrisk" | "lost" | "new" | "hibernating"
    """
    name_lower = name.lower()

    # ── Name-based shortcuts (covers standard K-Means labels) ─────
    if any(k in name_lower for k in ("champion", "high value", "vip", "wholesale")):
        return "high"
    if any(k in name_lower for k in ("loyal", "regular", "active")):
        return "medium"
    if any(k in name_lower for k in ("at risk", "at-risk", "atrisk", "risk")):
        return "atrisk"
    if any(k in name_lower for k in ("lost", "churned", "inactive", "low value")):
        return "lost"
    if any(k in name_lower for k in ("new", "prospect", "first")):
        return "new"
    if any(k in name_lower for k in ("hibernat", "dormant", "lapsed", "sleeping")):
        return "hibernating"

    # ── Stat-based fallback (works for any custom cluster name) ───
    if not all_clvs:
        return "medium"

    sorted_clvs = sorted(all_clvs, reverse=True)
    n = len(sorted_clvs)
    top_25_threshold    = sorted_clvs[max(0, int(n * 0.25) - 1)]
    bottom_25_threshold = sorted_clvs[min(n - 1, int(n * 0.75))]

    if avg_clv >= top_25_threshold:
        return "high"
    if avg_recency > 180 and avg_frequency <= 2:
        return "lost"
    if avg_recency > 90:
        return "atrisk"
    if avg_frequency <= 1 and avg_recency < 60:
        return "new"
    if avg_clv <= bottom_25_threshold and avg_recency > 60:
        return "hibernating"
    return "medium"


def build_recommendations(profiles: List[SegmentProfile]) -> List[Recommendation]:
    """
    Generate a Recommendation for every segment profile.

    Always produces one recommendation per segment — never returns an empty
    list, even for unusual cluster shapes.

    Args:
        profiles: List of SegmentProfile objects sorted by avg_clv desc.

    Returns:
        List of Recommendation objects in the same order as profiles.
    """
    all_clvs = [p.avg_clv for p in profiles]
    recs = []

    for profile in profiles:
        tier = _assign_tier(
            name=profile.name,
            avg_clv=profile.avg_clv,
            avg_recency=profile.avg_recency,
            avg_frequency=profile.avg_frequency,
            all_clvs=all_clvs,
        )
        playbook = _PLAYBOOK[tier]

        recs.append(Recommendation(
            segment=profile.name,
            tier=tier,
            headline=playbook["headline"],
            actions=playbook["actions"],
            color=playbook["color"],
            icon=playbook["icon"],
        ))

    return recs


@router.get("", response_model=SegmentsResponse)
def get_segments() -> SegmentsResponse:
    """Return all segment profiles with clustering quality metrics."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    metrics = svc.evaluation_metrics
    runs = svc.runs_data

    profiles = []
    for seg_name, group in df.groupby("segment", observed=False):
        name = str(seg_name)
        profiles.append(
            SegmentProfile(
                name=name,
                customer_count=len(group),
                avg_recency=round(float(group["recency"].mean()), 1),
                avg_frequency=round(float(group["frequency"].mean()), 1),
                avg_monetary=round(float(group["monetary"].mean()), 2),
                avg_tenure=round(float(group["tenure"].mean()), 1),
                avg_clv=round(float(group["clv"].mean()), 2) if "clv" in group.columns else 0.0,
                avg_churn_probability=round(
                    float(group["churn_probability"].mean()), 4
                ) if "churn_probability" in group.columns else 0.0,
                total_clv=round(float(group["clv"].sum()), 2) if "clv" in group.columns else 0.0,
                color=svc.get_segment_color(name),
            )
        )

    # Sort by avg_clv descending
    profiles.sort(key=lambda x: x.avg_clv, reverse=True)

    cl_metrics = metrics.get("clustering_evaluation", {})
    clustering_metrics = {
        "silhouette_score": cl_metrics.get("silhouette_score", 0.0),
        "davies_bouldin_index": cl_metrics.get("davies_bouldin_index", 0.0),
        "calinski_harabasz_index": cl_metrics.get("calinski_harabasz_index", 0.0),
    }

    return SegmentsResponse(
        segments=profiles,
        clustering_metrics=clustering_metrics,
        algorithm=runs.get("algorithm", "kmeans"),
        optimal_k=runs.get("optimal_k", len(profiles)),
    )


@router.get("/{segment_name}", response_model=SegmentProfile)
def get_segment(segment_name: str) -> SegmentProfile:
    """Return profile for a single named segment."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    mask = df["segment"].astype(str).str.lower() == segment_name.lower()
    group = df[mask]

    if group.empty:
        raise HTTPException(status_code=404, detail=f"Segment '{segment_name}' not found.")

    name = str(group["segment"].iloc[0])
    return SegmentProfile(
        name=name,
        customer_count=len(group),
        avg_recency=round(float(group["recency"].mean()), 1),
        avg_frequency=round(float(group["frequency"].mean()), 1),
        avg_monetary=round(float(group["monetary"].mean()), 2),
        avg_tenure=round(float(group["tenure"].mean()), 1),
        avg_clv=round(float(group["clv"].mean()), 2) if "clv" in group.columns else 0.0,
        avg_churn_probability=round(
            float(group["churn_probability"].mean()), 4
        ) if "churn_probability" in group.columns else 0.0,
        total_clv=round(float(group["clv"].sum()), 2) if "clv" in group.columns else 0.0,
        color=svc.get_segment_color(name),
    )


@router.get("/recommendations/all", response_model=RecommendationsResponse)
def get_recommendations() -> RecommendationsResponse:
    """
    Return data-driven strategic recommendations for every segment.

    Recommendations are generated from actual cluster statistics so they
    are always populated — even for unusual cluster shapes like a single
    wholesale customer vs thousands of retail customers.
    """
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    runs = svc.runs_data

    # Build profiles (same logic as get_segments)
    profiles: List[SegmentProfile] = []
    for seg_name, group in df.groupby("segment", observed=False):
        name = str(seg_name)
        profiles.append(
            SegmentProfile(
                name=name,
                customer_count=len(group),
                avg_recency=round(float(group["recency"].mean()), 1),
                avg_frequency=round(float(group["frequency"].mean()), 1),
                avg_monetary=round(float(group["monetary"].mean()), 2),
                avg_tenure=round(float(group["tenure"].mean()), 1),
                avg_clv=round(float(group["clv"].mean()), 2) if "clv" in group.columns else 0.0,
                avg_churn_probability=round(
                    float(group["churn_probability"].mean()), 4
                ) if "churn_probability" in group.columns else 0.0,
                total_clv=round(float(group["clv"].sum()), 2) if "clv" in group.columns else 0.0,
                color=svc.get_segment_color(name),
            )
        )

    # Sort by avg_clv descending so highest-value segment comes first
    profiles.sort(key=lambda x: x.avg_clv, reverse=True)

    recs = build_recommendations(profiles)

    algo    = runs.get("algorithm", "kmeans")
    opt_k   = runs.get("optimal_k", len(profiles))
    summary = f"{len(profiles)} segment{'s' if len(profiles) != 1 else ''} - {algo.upper()} k={opt_k}"

    return RecommendationsResponse(
        recommendations=recs,
        generated_from=summary,
    )
