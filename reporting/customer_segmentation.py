from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["Customer Segmentation"])


# ==========================================
# DB Dependency
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# CUSTOMER SEGMENTATION
# ==========================================
@router.get("/customer-segmentation")
def get_customer_segmentation(
    batch_id: int,
    year: int,
    month_start: int,
    month_end: int,
    lob: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            WITH customer_rev AS (
                SELECT
                    customer_name,
                    SUM(total_revenue) AS revenue
                FROM fact_slaccounting_wide
                WHERE batch_id = :batch_id
                  AND country = :country
                  AND year = :year
                  AND month BETWEEN :month_start AND :month_end
                GROUP BY customer_name
            ),
            ranked AS (
                SELECT
                    customer_name,
                    revenue,
                    NTILE(3) OVER (ORDER BY revenue DESC) AS segment
                FROM customer_rev
            )

            SELECT
                customer_name,
                ROUND(revenue, 2) AS revenue,
                CASE segment
                    WHEN 1 THEN 'Segment 1'
                    WHEN 2 THEN 'Segment 2'
                    ELSE 'Segment 3'
                END AS customer_segment
            FROM ranked
            ORDER BY revenue DESC;
        """),
        {
            "batch_id": batch_id,
            "country": lob,
            "year": year,
            "month_start": month_start,
            "month_end": month_end,
        }
    )

    rows = [dict(row) for row in result.mappings()]

    return {
        "year": year,
        "month_start": month_start,
        "month_end": month_end,
        "country": lob,
        "total_customers": len(rows),
        "data": rows
    }