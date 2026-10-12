from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["Proforma Reporting Slide-10"])


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
# HELPER: round to 2 decimals and avoid "-0.0"
# ==========================================
def r2(value):
    return round(value, 2) + 0.0


def pct_of_sales(value, sales):
    return r2((value / sales) * 100) if sales else 0.0


# ==========================================
# PROFORMA BALANCE SHEET API (Wireframe 10)
# Current (actual) values only - no forecasting
#
# Balance sheet = position AS AT the end of the selected period
#   -> cumulative postings up to (year, month_end)
#
# Uses signed movement (balance column kept commented):
#   Assets               -> total_dr - total_cr
#   Liabilities / Equity -> total_cr - total_dr
# ==========================================
@router.get("/proforma-balance-sheet")
def get_proforma_balance_sheet(
    batch_id: int,
    year: int,
    month_start: int,
    month_end: int,
    lob: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # ==========================================
    # CUMULATIVE BALANCES UP TO END OF PERIOD
    # ==========================================
    result = db.execute(text("""
        SELECT

            -- =====================================
            -- SALES (selected period only, for % of sales)
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_subclass) = 'sales'
                     AND year = :year
                     AND month BETWEEN :month_start AND :month_end
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS sales,

            -- =====================================
            -- CURRENT ASSETS
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'cash & cash equivalents'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS cash,

            SUM(
                CASE
                    WHEN lower(account_name) = 'receivables'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS receivables,

            SUM(
                CASE
                    WHEN lower(account_name) = 'inventory'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS inventory,

            SUM(
                CASE
                    WHEN lower(account_name) IN ('other current assets', 'investments')
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS other_current_assets,

            -- =====================================
            -- NON-CURRENT ASSETS
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'property, plant & equipment'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS gross_ppe,

            SUM(
                CASE
                    WHEN lower(account_name) = 'accumulated depreciation'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS accumulated_depreciation,

            SUM(
                CASE
                    WHEN lower(account_name) = 'intangible assets'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS intangible_assets,

            -- =====================================
            -- CURRENT LIABILITIES
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'trade payables'
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS trade_payables,

            SUM(
                CASE
                    WHEN lower(account_name) IN ('other payables', 'other current liabilities')
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS other_payables,

            SUM(
                CASE
                    WHEN lower(account_name) = 'current installments of long term debt'
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS short_term_debt,

            -- =====================================
            -- NON-CURRENT LIABILITIES
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'long term obligations'
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS long_term_debt,

            SUM(
                CASE
                    WHEN lower(account_name) = 'other long term liabilities'
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS other_long_term_liabilities,

            -- =====================================
            -- EQUITY
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) IN ('share capital', 'share premium')
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS paid_in_capital,

            SUM(
                CASE
                    WHEN account_type IN ('Income', 'Expense')
                    -- THEN balance
                    THEN total_cr - total_dr
                    ELSE 0
                END
            ) AS cumulative_net_income,

            SUM(
                CASE
                    WHEN lower(account_name) = 'dividends paid'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS cumulative_dividends

        FROM fact_gl_recon

        WHERE company_id = :company_id
          AND batch_id = :batch_id
          AND (
                year < :year
                OR (year = :year AND month <= :month_end)
          )
          AND (:lob IS NULL OR lob = :lob)

    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "year": year,
        "month_start": month_start,
        "month_end": month_end,
        "lob": lob
    }).mappings().first()

    if not result or result["cash"] is None:
        return {
            "success": False,
            "message": "No data found"
        }

    # ==========================================
    # CURRENT VALUES
    # ==========================================
    def val(key):
        return float(result[key] or 0)

    sales = val("sales")

    cash = val("cash")
    receivables = val("receivables")
    inventory = val("inventory")
    other_current_assets = val("other_current_assets")

    gross_ppe = val("gross_ppe")
    accumulated_depreciation = val("accumulated_depreciation")  # negative (credit)
    intangible_assets = val("intangible_assets")

    trade_payables = val("trade_payables")
    other_payables = val("other_payables")
    short_term_debt = val("short_term_debt")

    long_term_debt = val("long_term_debt")
    other_long_term_liabilities = val("other_long_term_liabilities")

    paid_in_capital = val("paid_in_capital")
    cumulative_net_income = val("cumulative_net_income")
    cumulative_dividends = val("cumulative_dividends")

    # ==========================================
    # DERIVED VALUES - ASSETS
    # ==========================================
    total_current_assets = (
        cash
        + receivables
        + inventory
        + other_current_assets
    )

    net_ppe = gross_ppe + accumulated_depreciation

    total_assets = (
        total_current_assets
        + net_ppe
        + intangible_assets
    )

    # ==========================================
    # DERIVED VALUES - LIABILITIES
    # ==========================================
    payables = trade_payables + other_payables

    total_current_liabilities = (
        payables
        + short_term_debt
    )

    debt_payable = short_term_debt + long_term_debt

    total_liabilities = (
        total_current_liabilities
        + long_term_debt
        + other_long_term_liabilities
    )

    # ==========================================
    # DERIVED VALUES - EQUITY
    # ==========================================
    retained_earnings = (
        cumulative_net_income
        - cumulative_dividends
    )

    total_equity = (
        paid_in_capital
        + retained_earnings
    )

    total_liabilities_and_equity = (
        total_liabilities
        + total_equity
    )

    balance_difference = (
        total_assets
        - total_liabilities_and_equity
    )

    # ==========================================
    # FINAL RESPONSE
    # ==========================================
    data = {

        # ======================================
        # ASSETS
        # ======================================
        "cash": {
            "formula":
                "Cumulative Cash & Cash Equivalents balance",

            "value": r2(cash),

            "details": {
                "percent_of_sales": pct_of_sales(cash, sales)
            }
        },

        "receivables": {
            "formula":
                "Cumulative Receivables balance",

            "value": r2(receivables),

            "details": {
                "percent_of_sales": pct_of_sales(receivables, sales)
            }
        },

        "inventory": {
            "formula":
                "Cumulative Inventory balance",

            "value": r2(inventory),

            "details": {
                "percent_of_sales": pct_of_sales(inventory, sales)
            }
        },

        "total_current_assets": {
            "formula":
                "Cash + Receivables + Inventory + Other Current Assets",

            "value": r2(total_current_assets),

            "details": {
                "cash": r2(cash),
                "receivables": r2(receivables),
                "inventory": r2(inventory),
                "other_current_assets": r2(other_current_assets)
            }
        },

        "ppe": {
            "formula":
                "Gross PP&E - Accumulated Depreciation",

            "value": r2(net_ppe),

            "details": {
                "gross_ppe": r2(gross_ppe),
                "accumulated_depreciation": r2(accumulated_depreciation)
            }
        },

        "total_assets": {
            "formula":
                "Total Current Assets + Net PP&E + Intangible Assets",

            "value": r2(total_assets),

            "details": {
                "total_current_assets": r2(total_current_assets),
                "net_ppe": r2(net_ppe),
                "intangible_assets": r2(intangible_assets)
            }
        },

        # ======================================
        # LIABILITIES
        # ======================================
        "payables": {
            "formula":
                "Trade Payables + Other Payables",

            "value": r2(payables),

            "details": {
                "trade_payables": r2(trade_payables),
                "other_payables": r2(other_payables),
                "percent_of_sales": pct_of_sales(payables, sales)
            }
        },

        "total_current_liabilities": {
            "formula":
                "Payables + Current Installments of Long Term Debt",

            "value": r2(total_current_liabilities),

            "details": {
                "payables": r2(payables),
                "short_term_debt": r2(short_term_debt)
            }
        },

        "debt_payable": {
            "formula":
                "Current Installments of LT Debt + Long Term Obligations",

            "value": r2(debt_payable),

            "details": {
                "short_term_debt": r2(short_term_debt),
                "long_term_debt": r2(long_term_debt)
            }
        },

        "total_liabilities": {
            "formula":
                "Total Current Liabilities + Long Term Debt "
                "+ Other Long Term Liabilities",

            "value": r2(total_liabilities),

            "details": {
                "total_current_liabilities": r2(total_current_liabilities),
                "long_term_debt": r2(long_term_debt),
                "other_long_term_liabilities":
                    r2(other_long_term_liabilities)
            }
        },

        # ======================================
        # EQUITY
        # ======================================
        "paid_in_capital": {
            "formula":
                "Share Capital + Share Premium",

            "value": r2(paid_in_capital)
        },

        "retained_earnings": {
            "formula":
                "Cumulative Net Income - Cumulative Dividends "
                "(Statement of RE ending balance)",

            "value": r2(retained_earnings),

            "details": {
                "cumulative_net_income": r2(cumulative_net_income),
                "cumulative_dividends": r2(cumulative_dividends)
            }
        },

        "total_equity": {
            "formula":
                "Paid in Capital + Retained Earnings",

            "value": r2(total_equity),

            "details": {
                "paid_in_capital": r2(paid_in_capital),
                "retained_earnings": r2(retained_earnings)
            }
        },

        "total_liabilities_and_equity": {
            "formula":
                "Total Liabilities + Total Equity",

            "value": r2(total_liabilities_and_equity),

            "details": {
                "total_liabilities": r2(total_liabilities),
                "total_equity": r2(total_equity)
            }
        },

        # ======================================
        # CHECK (should be 0)
        # ======================================
        "balance_check": {
            "formula":
                "Total Assets - (Total Liabilities + Total Equity)",

            "value": r2(balance_difference),

            "status": (
                "Balanced"
                if abs(balance_difference) < 0.01
                else "Not Balanced"
            ),

            "details": {
                "total_assets": r2(total_assets),
                "total_liabilities_and_equity":
                    r2(total_liabilities_and_equity),
                "sales_for_selected_period": r2(sales)
            }
        }
    }

    return {
        "success": True,
        "data": data
    }