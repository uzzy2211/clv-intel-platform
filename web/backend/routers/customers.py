"""
customers.py — Customers API Router

Provides paginated customer list and individual customer detail endpoints.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from web.backend.schemas import CustomerDetail, CustomerRow, CustomersResponse
from web.backend.services.data_service import get_data_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=CustomersResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    segment: Optional[str] = Query(None),
    sort_by: str = Query("clv"),
    sort_dir: str = Query("desc"),
    search: Optional[str] = Query(None),
) -> CustomersResponse:
    """Return a paginated, filterable list of customers.

    Args:
        page: Page number (1-indexed).
        page_size: Number of records per page.
        segment: Optional segment name filter.
        sort_by: Column to sort by (clv, recency, frequency, monetary).
        sort_dir: Sort direction (asc | desc).
        search: Optional CustomerID search string.
    """
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments.copy()

    # Apply segment filter
    if segment and segment.lower() != "all":
        df = df[df["segment"].astype(str).str.lower() == segment.lower()]

    # Apply search filter
    if search:
        df = df[df.index.astype(str).str.contains(search, case=False)]

    # Apply sort
    valid_sort_cols = {"clv", "recency", "frequency", "monetary", "tenure", "churn_probability"}
    if sort_by not in valid_sort_cols:
        sort_by = "clv"
    ascending = sort_dir.lower() == "asc"
    df = df.sort_values(sort_by, ascending=ascending)

    total = len(df)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end]

    customers = []
    for cid, row in page_df.iterrows():
        customers.append(
            CustomerRow(
                customer_id=int(cid),
                segment=str(row.get("segment", "")),
                recency=round(float(row.get("recency", 0)), 1),
                frequency=int(row.get("frequency", 0)),
                monetary=round(float(row.get("monetary", 0)), 2),
                tenure=round(float(row.get("tenure", 0)), 1),
                clv=round(float(row.get("clv", 0)), 2),
                churn_probability=round(float(row.get("churn_probability", 0)), 4),
                predicted_purchases=round(float(row.get("predicted_purchases", 0)), 2),
            )
        )

    return CustomersResponse(
        customers=customers,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: int) -> CustomerDetail:
    """Return full profile for a single customer by ID."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    if customer_id not in df.index:
        # Try float index (CustomerID stored as float in some CSVs)
        float_id = float(customer_id)
        if float_id not in df.index:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")
        row = df.loc[float_id]
    else:
        row = df.loc[customer_id]

    def _f(col: str, default: float = 0.0) -> float:
        val = row.get(col, default)
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    return CustomerDetail(
        customer_id=customer_id,
        segment=str(row.get("segment", "")),
        recency=round(_f("recency"), 1),
        frequency=int(_f("frequency")),
        monetary=round(_f("monetary"), 2),
        tenure=round(_f("tenure"), 1),
        clv=round(_f("clv"), 2),
        churn_probability=round(_f("churn_probability"), 4),
        predicted_purchases=round(_f("predicted_purchases"), 2),
        expected_avg_profit=round(_f("expected_avg_profit"), 2),
        pca_1=round(_f("pca_1"), 4),
        pca_2=round(_f("pca_2"), 4),
        frequency_lifetimes=round(_f("frequency_lifetimes"), 1),
        recency_lifetimes=round(_f("recency_lifetimes"), 1),
        T_lifetimes=round(_f("T_lifetimes"), 1),
        monetary_value_lifetimes=round(_f("monetary_value_lifetimes"), 2),
    )
