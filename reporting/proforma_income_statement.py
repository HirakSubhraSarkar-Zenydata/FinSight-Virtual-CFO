from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["Proforma Reporting Slide-9"])


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
# PROFORMA INCOME STATEMENT API (Wireframe 9)
# Current (actual) values only - no forecasting
# ==========================================
@router.get("/proforma-income-statement")
def get_proforma_income_statement(
    batch_id: int,
    year: int,
    month_start: int,
    month_end: int,
    lob: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # ==========================================
    # CURRENT PERIOD DATA
    # ==========================================
    result = db.execute(text("""
        SELECT

            -- =====================================
            -- INCOME STATEMENT
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_subclass) = 'sales'
                    THEN balance
                    ELSE 0
                END
            ) AS sales,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'cost of sales'
                    THEN balance
                    ELSE 0
                END
            ) AS cogs,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'depreciation & amortization'
                    THEN balance
                    ELSE 0
                END
            ) AS depreciation,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'operating expenses'
                    THEN balance
                    ELSE 0
                END
            ) AS operating_expenses,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'interest expense'
                    THEN balance
                    ELSE 0
                END
            ) AS interest_expense,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'taxation'
                    THEN balance
                    ELSE 0
                END
            ) AS income_tax,

            -- =====================================
            -- STATEMENT OF RETAINED EARNINGS
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'dividends paid'
                    THEN balance
                    ELSE 0
                END
            ) AS dividends

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
        "month_start": month_start,
        "month_end": month_end,
        "lob": lob
    }).mappings().first()

    if not result or result["sales"] is None:
        return {
            "success": False,
            "message": "No data found"
        }

    # ==========================================
    # PRIOR PERIODS DATA (for Beginning RE)
    # Everything before the selected period:
    #   earlier years + earlier months of the same year
    # ==========================================
    previous_result = db.execute(text("""
        SELECT

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'sales'
                    THEN balance
                    ELSE 0
                END
            ) AS sales,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'cost of sales'
                    THEN balance
                    ELSE 0
                END
            ) AS cogs,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'depreciation & amortization'
                    THEN balance
                    ELSE 0
                END
            ) AS depreciation,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'operating expenses'
                    THEN balance
                    ELSE 0
                END
            ) AS operating_expenses,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'interest expense'
                    THEN balance
                    ELSE 0
                END
            ) AS interest_expense,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'taxation'
                    THEN balance
                    ELSE 0
                END
            ) AS income_tax,

            SUM(
                CASE
                    WHEN lower(account_name) = 'dividends paid'
                    THEN balance
                    ELSE 0
                END
            ) AS dividends

        FROM fact_gl_recon

        WHERE company_id = :company_id
          AND batch_id = :batch_id
          AND (
                year < :year
                OR (year = :year AND month < :month_start)
          )
          AND (:lob IS NULL OR lob = :lob)

    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "year": year,
        "month_start": month_start,
        "lob": lob
    }).mappings().first()

    # ==========================================
    # CURRENT VALUES
    # ==========================================
    sales = float(result["sales"] or 0)
    cogs = float(result["cogs"] or 0)

    depreciation = float(
        result["depreciation"] or 0
    )

    operating_expenses = float(
        result["operating_expenses"] or 0
    )

    interest_expense = float(
        result["interest_expense"] or 0
    )

    income_tax = float(
        result["income_tax"] or 0
    )

    dividends = float(
        result["dividends"] or 0
    )

    # ==========================================
    # PREVIOUS VALUES
    # ==========================================
    prev_sales = float(previous_result["sales"] or 0)
    prev_cogs = float(previous_result["cogs"] or 0)

    prev_depreciation = float(
        previous_result["depreciation"] or 0
    )

    prev_operating_expenses = float(
        previous_result["operating_expenses"] or 0
    )

    prev_interest_expense = float(
        previous_result["interest_expense"] or 0
    )

    prev_income_tax = float(
        previous_result["income_tax"] or 0
    )

    prev_dividends = float(
        previous_result["dividends"] or 0
    )

    # ==========================================
    # DERIVED VALUES - INCOME STATEMENT
    # ==========================================
    gross_profit = sales - cogs

    operating_profit = (
        gross_profit
        - depreciation
        - operating_expenses
    )

    income_before_taxes = (
        operating_profit
        - interest_expense
    )

    net_income = (
        income_before_taxes
        - income_tax
    )

    # ==========================================
    # DERIVED VALUES - RETAINED EARNINGS
    # ==========================================
    prev_net_income = (
        prev_sales
        - prev_cogs
        - prev_depreciation
        - prev_operating_expenses
        - prev_interest_expense
        - prev_income_tax
    )

    beginning_re = (
        prev_net_income
        - prev_dividends
    )

    ending_re = (
        beginning_re
        + net_income
        - dividends
    )

    # ==========================================
    # FINAL RESPONSE
    # ==========================================
    data = {

        # ======================================
        # INCOME STATEMENT
        # ======================================
        "sales": {
            "formula":
                "Sum of Sales accounts",

            "value": round(sales, 2)
        },

        "cogs": {
            "formula":
                "Sum of Cost of Sales accounts",

            "value": round(cogs, 2)
        },

        "gross_profit": {
            "formula":
                "Sales - COGS",

            "value": round(gross_profit, 2),

            "details": {
                "sales": round(sales, 2),
                "cogs": round(cogs, 2)
            }
        },

        "depreciation": {
            "formula":
                "Sum of Depreciation & Amortization accounts",

            "value": round(depreciation, 2)
        },

        "other_operating_expenses": {
            "formula":
                "Sum of Operating Expenses (SG&A) accounts",

            "value": round(operating_expenses, 2)
        },

        "operating_profit": {
            "formula":
                "Gross Profit - Depreciation - Other Operating Expenses",

            "value": round(operating_profit, 2),

            "details": {
                "gross_profit": round(gross_profit, 2),
                "depreciation": round(depreciation, 2),
                "other_operating_expenses":
                    round(operating_expenses, 2)
            }
        },

        "interest_expense": {
            "formula":
                "Sum of Interest Expense accounts",

            "value": round(interest_expense, 2)
        },

        "income_before_taxes": {
            "formula":
                "Operating Profit - Interest Expense",

            "value": round(income_before_taxes, 2),

            "details": {
                "operating_profit": round(operating_profit, 2),
                "interest_expense": round(interest_expense, 2)
            }
        },

        "income_tax": {
            "formula":
                "Sum of Taxation accounts",

            "value": round(income_tax, 2),

            "details": {
                "effective_tax_rate_percent": (
                    round(
                        (income_tax / income_before_taxes) * 100,
                        2
                    )
                    if income_before_taxes > 0
                    else 0
                )
            }
        },

        "net_income": {
            "formula":
                "Income Before Taxes - Income Tax",

            "value": round(net_income, 2),

            "details": {
                "income_before_taxes":
                    round(income_before_taxes, 2),
                "income_tax": round(income_tax, 2)
            }
        },

        # ======================================
        # STATEMENT OF RETAINED EARNINGS
        # ======================================
        "beginning_re": {
            "formula":
                "Previous period's Ending RE "
                "(Cumulative Net Income - Dividends before selected period)",

            "value": round(beginning_re, 2),

            "details": {
                "prior_net_income": round(prev_net_income, 2),
                "prior_dividends": round(prev_dividends, 2)
            }
        },

        "re_net_income": {
            "formula":
                "Flows from Income Statement",

            "value": round(net_income, 2)
        },

        "dividends": {
            "formula":
                "Sum of Dividends Paid accounts",

            "value": round(dividends, 2)
        },

        "ending_re": {
            "formula":
                "Beginning RE + Net Income - Dividends",

            "value": round(ending_re, 2),

            "details": {
                "beginning_re": round(beginning_re, 2),
                "net_income": round(net_income, 2),
                "dividends": round(dividends, 2)
            }
        }
    }

    return {
        "success": True,
        "data": data
    }