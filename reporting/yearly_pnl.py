from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["PnL Reporting"])


# =========================
# DB Dependency
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# 1. GET DISTINCT YEARS
# =========================
# @router.get("/years")
# def get_years(
#     batch_id: int,
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     result = db.execute(text("""
#         SELECT DISTINCT year
#         FROM fact_yearly_pnl_report
#         WHERE company_id = :company_id
#           AND batch_id = :batch_id
#         ORDER BY year DESC
#     """), {
#         "company_id": user.company_id,
#         "batch_id": batch_id
#     }).fetchall()

#     data = [
#         {
#             "label": f"{row[0]}",
#             "value": row[0]
#         }
#         for row in result
#     ]

#     return {
#         "success": True,
#         "data": data
#     }

@router.get("/years")
def get_years(
    batch_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    years = db.execute(text("""
        SELECT year
        FROM fact_yearly_pnl_report
        WHERE company_id = :company_id
          AND batch_id = :batch_id
        GROUP BY year
        ORDER BY year DESC
    """), {
        "company_id": user.company_id,
        "batch_id": batch_id
    }).scalars().all()

    if not years:
        return {
            "success": True,
            "data": [],
            "message": "No data found"
        }

    return {
        "success": True,
        "data": [{"label": str(y), "value": y} for y in years]
    }


# =========================
# 2. GET DISTINCT LOBS
# =========================
@router.get("/lobs")
def get_lobs(
    batch_id: int,
    year: int | None = None,   # 👈 make optional
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lobs = db.execute(text("""
        SELECT lob
        FROM fact_yearly_pnl_report
        WHERE company_id = :company_id
          AND batch_id = :batch_id
          AND (:year IS NULL OR year = :year)   -- 👈 key change
        GROUP BY lob
        ORDER BY lob
    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "year": year
    }).scalars().all()

    if not lobs:
        return {
            "success": True,
            "data": [],
            "message": "No data found"
        }

    return {
        "success": True,
        "data": [
            # {"label": "All LOBs", "value": None},  # 👈 always include
            *[{"label": lob, "value": lob} for lob in lobs]
        ]
    }


# =========================
# 3. YEARLY SUMMARY
# =========================
@router.get("/yearly-summary")
def get_yearly_summary(
    batch_id: int,
    year: int | None = None,
    lob: str | None = None,
    month_start: int | None = None,
    month_end: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # =====================================================
    # 🔥 CASE 1: Month range → use fact_gl_recon (FAST SQL)
    # =====================================================
    if year and month_start and month_end:

        result = db.execute(text("""
            SELECT
                :year AS year,

                -- Revenue
                SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                    THEN balance ELSE 0 END) AS revenue,

                -- Gross Profit
                SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                    THEN balance ELSE 0 END)
                -
                SUM(CASE WHEN LOWER(account_subclass) = 'cost of sales'
                    THEN balance ELSE 0 END) AS gross_profit,

                -- EBIT
                SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                    THEN balance ELSE 0 END)
                -
                SUM(CASE WHEN LOWER(account_subclass) = 'cost of sales'
                    THEN balance ELSE 0 END)
                -
                SUM(CASE WHEN LOWER(account_subclass) = 'operating expenses'
                    THEN balance ELSE 0 END)
                -
                SUM(CASE WHEN LOWER(account_subclass) = 'depreciation & amortization'
                    THEN balance ELSE 0 END) AS ebit,

                -- OpEx
                SUM(CASE WHEN LOWER(account_subclass) = 'operating expenses'
                    THEN balance ELSE 0 END) AS opex,

                -- Net Income
                (
                    SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                        THEN balance ELSE 0 END)
                    -
                    SUM(CASE WHEN LOWER(account_subclass) = 'cost of sales'
                        THEN balance ELSE 0 END)
                    -
                    SUM(CASE WHEN LOWER(account_subclass) = 'operating expenses'
                        THEN balance ELSE 0 END)
                    -
                    SUM(CASE WHEN LOWER(account_subclass) = 'depreciation & amortization'
                        THEN balance ELSE 0 END)
                    -
                    SUM(CASE WHEN LOWER(account_subclass) = 'taxation'
                        THEN balance ELSE 0 END)
                ) AS net_income,

                -- EBIT %
                CASE 
                    WHEN SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                            THEN balance ELSE 0 END) = 0 THEN 0
                    ELSE
                        (
                            (
                                SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                                    THEN balance ELSE 0 END)
                                -
                                SUM(CASE WHEN LOWER(account_subclass) = 'cost of sales'
                                    THEN balance ELSE 0 END)
                                -
                                SUM(CASE WHEN LOWER(account_subclass) = 'operating expenses'
                                    THEN balance ELSE 0 END)
                                -
                                SUM(CASE WHEN LOWER(account_subclass) = 'depreciation & amortization'
                                    THEN balance ELSE 0 END)
                            )::numeric
                            /
                            SUM(CASE WHEN LOWER(account_subclass) = 'sales'
                                THEN balance ELSE 0 END)::numeric
                        ) * 100
                END AS ebit_percent

            FROM fact_gl_recon
            WHERE company_id = :company_id
              AND batch_id = :batch_id
              AND year = :year
              AND month BETWEEN :month_start AND :month_end
              AND (:lob IS NULL OR lob = :lob)
        """), {
            "company_id": user.company_id,
            "batch_id": batch_id,
            "year": year,
            "lob": lob,
            "month_start": month_start,
            "month_end": month_end
        }).mappings().first()

        if not result or result["revenue"] is None:
            return {"success": True, "data": None, "message": "No data found"}

        return {"success": True, "data": result}

    # =====================================================
    # 🔹 CASE 2: Single Year (fact_yearly_pnl_report)
    # =====================================================
    if year:

        result = db.execute(text("""
            SELECT
                :year AS year,

                SUM(CASE WHEN metric_name = 'Sales' THEN amount ELSE 0 END) AS revenue,
                SUM(CASE WHEN metric_name = 'Gross Income' THEN amount ELSE 0 END) AS gross_profit,
                SUM(CASE WHEN metric_name = 'EBIT' THEN amount ELSE 0 END) AS ebit,
                SUM(CASE WHEN metric_name = 'Operating Expenses' THEN amount ELSE 0 END) AS opex,
                SUM(CASE WHEN metric_name = 'Net Income' THEN amount ELSE 0 END) AS net_income,

                CASE 
                    WHEN SUM(CASE WHEN metric_name = 'Sales' THEN amount ELSE 0 END) = 0 THEN 0
                    ELSE
                        (SUM(CASE WHEN metric_name = 'EBIT' THEN amount ELSE 0 END)::numeric /
                         SUM(CASE WHEN metric_name = 'Sales' THEN amount ELSE 0 END)::numeric) * 100
                END AS ebit_percent

            FROM fact_yearly_pnl_report
            WHERE company_id = :company_id
              AND batch_id = :batch_id
              AND year = :year
              AND (:lob IS NULL OR lob = :lob)
        """), {
            "company_id": user.company_id,
            "batch_id": batch_id,
            "year": year,
            "lob": lob
        }).mappings().first()

        if not result or result["revenue"] is None:
            return {"success": True, "data": None, "message": "No data found"}

        return {"success": True, "data": result}

    # =====================================================
    # 🔹 CASE 3: Trend (No year)
    # =====================================================
    results = db.execute(text("""
        SELECT
            year,

            SUM(CASE WHEN metric_name = 'Sales' THEN amount ELSE 0 END) AS revenue,
            SUM(CASE WHEN metric_name = 'Gross Income' THEN amount ELSE 0 END) AS gross_profit,
            SUM(CASE WHEN metric_name = 'EBIT' THEN amount ELSE 0 END) AS ebit,
            SUM(CASE WHEN metric_name = 'Operating Expenses' THEN amount ELSE 0 END) AS opex,
            SUM(CASE WHEN metric_name = 'Net Income' THEN amount ELSE 0 END) AS net_income

        FROM fact_yearly_pnl_report
        WHERE company_id = :company_id
          AND batch_id = :batch_id
          AND (:lob IS NULL OR lob = :lob)

        GROUP BY year
        ORDER BY year
    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "lob": lob
    }).mappings().all()

    if not results:
        return {"success": True, "data": [], "message": "No data found"}

    return {"success": True, "data": results}