from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["Expense Breakdown"])


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
# EXPENSE BREAKDOWN API
# ==========================================
@router.get("/expense-breakdown-monthly")
def get_expense_breakdown(
    batch_id: int,
    year: int,
    month_start: int,
    month_end: int,
    lob: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    result = db.execute(text("""

        WITH expense_data AS (

            SELECT

                CASE

                    WHEN lower(account_subclass) = 'cost of sales'
                        THEN 'COGS'

                    WHEN lower(account_subclass) = 'depreciation & amortization'
                        THEN 'D&A'

                    WHEN lower(account_subclass) = 'operating expenses'
                        THEN 'SG&A'

                    WHEN lower(account_subclass) = 'interest expense'
                        THEN 'Interest Expense'

                    WHEN lower(account_subclass) = 'taxation'
                        THEN 'Income Tax'

                    ELSE 'Other'

                END AS expense_head,

                SUM(balance) AS net_expense

            FROM fact_gl_recon

            WHERE company_id = :company_id
              AND batch_id = :batch_id
              AND year = :year
              AND month BETWEEN :month_start AND :month_end
              AND (:lob IS NULL OR lob = :lob)

              AND lower(account_subclass) IN (
                    'cost of sales',
                    'depreciation & amortization',
                    'operating expenses',
                    'interest expense',
                    'taxation'
              )

            GROUP BY 1
        ),

        total_expense AS (

            SELECT
                SUM(net_expense) AS total
            FROM expense_data
        )

        SELECT

            e.expense_head,

            ROUND(
                (
                    e.net_expense
                    /
                    NULLIF(t.total, 0)
                ) * 100,
                2
            ) AS percent_expense,

            ROUND(e.net_expense, 2) AS net_expense

        FROM expense_data e
        CROSS JOIN total_expense t

        ORDER BY net_expense DESC

    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "year": year,
        "month_start": month_start,
        "month_end": month_end,
        "lob": lob
    }).mappings().all()

    if not result:
        return {
            "success": False,
            "message": "No expense data found"
        }

    total_expense = sum(
        float(row["net_expense"])
        for row in result
    )

    return {
        "success": True,
        "data": result,
        "total_expense": round(total_expense, 2)
    }