from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["Proforma Reporting Slide-11"])


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


# ==========================================
# PROFORMA CASH FLOW STATEMENT API (Wireframe 11)
# Current (actual) values only - no forecasting
# Indirect method (same layout as Excel tab '06 Projected Cash Flow Stmt')
#
# Uses signed movement: total_dr - total_cr  (balance is kept commented)
#   Sales (credit-normal)        -> value = -(Dr - Cr)
#   Expenses (debit-normal)      -> value =  (Dr - Cr)
#   Assets                       -> cash effect = -(Dr - Cr)
#   Liabilities / Share capital  -> cash effect = -(Dr - Cr)
#   Dividends paid               -> cash effect = -(Dr - Cr)
# ==========================================
@router.get("/proforma-cash-flow-statement")
def get_proforma_cash_flow_statement(
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
            -- INCOME STATEMENT (for Net Income)
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'sales'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS sales,

            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'cost of sales'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS cogs,

            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'depreciation & amortization'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS depreciation,

            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'operating expenses'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS operating_expenses,

            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'interest expense'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS interest_expense,

            SUM(
                CASE
                    WHEN lower(f.account_subclass) = 'taxation'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS income_tax,

            -- =====================================
            -- CASH
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_name) = 'cash & cash equivalents'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS cash,

            -- =====================================
            -- OPERATING - CURRENT ASSETS
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_name) = 'receivables'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS receivables,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'inventory'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS inventory,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'other current assets'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS other_current_assets,

            -- =====================================
            -- OPERATING - CURRENT LIABILITIES
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_name) = 'current installments of long term debt'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS short_term_debt,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'trade payables'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS trade_payables,

            SUM(
                CASE
                    WHEN lower(c.subaccount) = 'tax payable'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS taxes_payable,

            SUM(
                CASE
                    WHEN lower(f.account_name) IN ('other payables', 'other current liabilities')
                     AND lower(COALESCE(c.subaccount, '')) <> 'tax payable'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS other_current_liabilities,

            -- =====================================
            -- INVESTING
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_name) = 'property, plant & equipment'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS ppe,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'investments'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS investments,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'intangible assets'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS other_assets,

            -- =====================================
            -- FINANCING
            -- =====================================
            SUM(
                CASE
                    WHEN lower(f.account_name) = 'long term obligations'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS long_term_debt,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'other long term liabilities'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS other_liabilities,

            SUM(
                CASE
                    WHEN lower(f.account_name) IN ('share capital', 'share premium')
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS share_capital,

            SUM(
                CASE
                    WHEN lower(f.account_name) = 'dividends paid'
                    -- THEN f.balance
                    THEN f.total_dr - f.total_cr
                    ELSE 0
                END
            ) AS dividends

        FROM fact_gl_recon f

        LEFT JOIN dim_coa c
            ON c.id = f.coa_id

        WHERE f.company_id = :company_id
          AND f.batch_id = :batch_id
          AND f.year = :year
          AND f.month BETWEEN :month_start AND :month_end
          AND (:lob IS NULL OR f.lob = :lob)

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
    # PRIOR PERIODS DATA (for Beginning Cash)
    # Everything before the selected period:
    #   earlier years + earlier months of the same year
    # ==========================================
    previous_result = db.execute(text("""
        SELECT

            SUM(
                CASE
                    WHEN lower(account_name) = 'cash & cash equivalents'
                    -- THEN balance
                    THEN total_dr - total_cr
                    ELSE 0
                END
            ) AS beginning_cash

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
    def val(key):
        return float(result[key] or 0)

    # sales = val("sales")
    sales = -val("sales")  # credit-normal: Cr - Dr
    cogs = val("cogs")
    depreciation = val("depreciation")
    operating_expenses = val("operating_expenses")
    interest_expense = val("interest_expense")
    income_tax = val("income_tax")

    beginning_cash = float(
        previous_result["beginning_cash"] or 0
    )

    # ==========================================
    # CASH FLOW FROM OPERATING ACTIVITIES
    # ==========================================
    net_income = (
        sales
        - cogs
        - depreciation
        - operating_expenses
        - interest_expense
        - income_tax
    )

    depreciation_and_amortization = depreciation

    # Assets: increase -> cash outflow
    change_in_receivables = -val("receivables")
    change_in_inventory = -val("inventory")
    change_in_other_current_assets = -val("other_current_assets")

    # Liabilities: increase -> cash inflow
    # change_in_short_term_debt = val("short_term_debt")
    change_in_short_term_debt = -val("short_term_debt")
    # change_in_accounts_payable = val("trade_payables")
    change_in_accounts_payable = -val("trade_payables")
    # change_in_taxes_payable = val("taxes_payable")
    change_in_taxes_payable = -val("taxes_payable")
    # change_in_other_current_liabilities = val("other_current_liabilities")
    change_in_other_current_liabilities = -val("other_current_liabilities")

    changes_in_working_capital = (
        change_in_receivables
        + change_in_inventory
        + change_in_other_current_assets
        + change_in_short_term_debt
        + change_in_accounts_payable
        + change_in_taxes_payable
        + change_in_other_current_liabilities
    )

    cash_flow_from_operating_activities = (
        net_income
        + depreciation_and_amortization
        + changes_in_working_capital
    )

    # ==========================================
    # CASH FLOW FROM INVESTING ACTIVITIES
    # ==========================================
    purchase_of_ppe = -val("ppe")
    purchase_of_long_term_investments = -val("investments")
    other_assets = -val("other_assets")

    cash_flow_from_investing_activities = (
        purchase_of_ppe
        + purchase_of_long_term_investments
        + other_assets
    )

    # ==========================================
    # CASH FLOW FROM FINANCING ACTIVITIES
    # ==========================================
    # increase_in_long_term_debt = val("long_term_debt")
    increase_in_long_term_debt = -val("long_term_debt")
    # increase_in_other_liabilities = val("other_liabilities")
    increase_in_other_liabilities = -val("other_liabilities")
    # proceeds_from_share_issuance = val("share_capital")
    proceeds_from_share_issuance = -val("share_capital")
    dividends = -val("dividends")

    cash_flow_from_financing_activities = (
        increase_in_long_term_debt
        + increase_in_other_liabilities
        + proceeds_from_share_issuance
        + dividends
    )

    # ==========================================
    # CASH RECONCILIATION
    # ==========================================
    change_in_cash = (
        cash_flow_from_operating_activities
        + cash_flow_from_investing_activities
        + cash_flow_from_financing_activities
    )

    ending_cash = beginning_cash + change_in_cash

    # Check against the cash accounts
    actual_change_in_cash = val("cash")
    actual_ending_cash = beginning_cash + actual_change_in_cash
    reconciliation_difference = change_in_cash - actual_change_in_cash

    # ==========================================
    # FINAL RESPONSE
    # ==========================================
    data = {

        # ======================================
        # OPERATING ACTIVITIES
        # ======================================
        "net_income": {
            "formula":
                "Sales - COGS - Depreciation - Operating Expenses "
                "- Interest Expense - Income Tax",

            "value": r2(net_income),

            "details": {
                "sales": r2(sales),
                "cogs": r2(cogs),
                "depreciation": r2(depreciation),
                "operating_expenses": r2(operating_expenses),
                "interest_expense": r2(interest_expense),
                "income_tax": r2(income_tax)
            }
        },

        "depreciation_and_amortization": {
            "formula":
                "Add back non-cash Depreciation & Amortization",

            "value": r2(depreciation_and_amortization)
        },

        "changes_in_working_capital": {
            "formula":
                "- Increase in Current Assets + Increase in Current Liabilities",

            "value": r2(changes_in_working_capital),

            "details": {
                "change_in_receivables":
                    r2(change_in_receivables),

                "change_in_inventory":
                    r2(change_in_inventory),

                "change_in_other_current_assets":
                    r2(change_in_other_current_assets),

                "change_in_short_term_debt":
                    r2(change_in_short_term_debt),

                "change_in_accounts_payable":
                    r2(change_in_accounts_payable),

                "change_in_taxes_payable":
                    r2(change_in_taxes_payable),

                "change_in_other_current_liabilities":
                    r2(change_in_other_current_liabilities)
            }
        },

        "cash_flow_from_operating_activities": {
            "formula":
                "Net Income + D&A + Changes in Working Capital",

            "value": r2(cash_flow_from_operating_activities),

            "details": {
                "net_income": r2(net_income),
                "depreciation_and_amortization":
                    r2(depreciation_and_amortization),
                "changes_in_working_capital":
                    r2(changes_in_working_capital)
            }
        },

        # ======================================
        # INVESTING ACTIVITIES
        # ======================================
        "cash_flow_from_investing_activities": {
            "formula":
                "- Purchase of PP&E - Purchase of Long-term Investments - Other Assets",

            "value": r2(cash_flow_from_investing_activities),

            "details": {
                "purchase_of_ppe":
                    r2(purchase_of_ppe),

                "purchase_of_long_term_investments":
                    r2(purchase_of_long_term_investments),

                "other_assets":
                    r2(other_assets)
            }
        },

        # ======================================
        # FINANCING ACTIVITIES
        # ======================================
        "cash_flow_from_financing_activities": {
            "formula":
                "Increase in LT Debt + Increase in Other Liabilities "
                "+ Share Issuance - Dividends",

            "value": r2(cash_flow_from_financing_activities),

            "details": {
                "increase_in_long_term_debt":
                    r2(increase_in_long_term_debt),

                "increase_in_other_liabilities":
                    r2(increase_in_other_liabilities),

                "proceeds_from_share_issuance":
                    r2(proceeds_from_share_issuance),

                "dividends":
                    r2(dividends)
            }
        },

        # ======================================
        # CASH SUMMARY
        # ======================================
        "beginning_cash_balance": {
            "formula":
                "Cash balance before the selected period",

            "value": r2(beginning_cash)
        },

        "change_in_cash": {
            "formula":
                "CFO + CFI + CFF",

            "value": r2(change_in_cash),

            "details": {
                "cash_flow_from_operating_activities":
                    r2(cash_flow_from_operating_activities),

                "cash_flow_from_investing_activities":
                    r2(cash_flow_from_investing_activities),

                "cash_flow_from_financing_activities":
                    r2(cash_flow_from_financing_activities)
            }
        },

        "ending_cash_balance": {
            "formula":
                "Beginning Cash Balance + Change in Cash",

            "value": r2(ending_cash),

            "details": {
                "beginning_cash_balance": r2(beginning_cash),
                "change_in_cash": r2(change_in_cash)
            }
        },

        # ======================================
        # CHECK (should be 0)
        # ======================================
        "cash_reconciliation": {
            "formula":
                "Change in Cash (Cash Flow) - Change in Cash (Cash accounts)",

            "value": r2(reconciliation_difference),

            "status": (
                "Balanced"
                if abs(reconciliation_difference) < 0.01
                else "Not Balanced"
            ),

            "details": {
                "change_in_cash_per_cash_flow":
                    r2(change_in_cash),

                "change_in_cash_per_cash_accounts":
                    r2(actual_change_in_cash),

                "ending_cash_per_cash_accounts":
                    r2(actual_ending_cash)
            }
        }
    }

    return {
        "success": True,
        "data": data
    }