# # reporting/kpi.py

# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from sqlalchemy import text

# from database import SessionLocal
# from auth import get_current_user
# from models import User

# router = APIRouter(tags=["KPI Reporting"])


# # ==========================================
# # DB Dependency
# # ==========================================
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# # ==========================================
# # KPI API
# # ==========================================
# @router.get("/monthly")
# def get_monthly_kpis(
#     batch_id: int,
#     year: int,
#     month_start: int,
#     month_end: int,
#     lob: str | None = None,
#     assumed_wacc: float = 0.1,  # Default WACC assumption (10%)
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):

#     result = db.execute(text("""
#         SELECT

#             -- =====================================
#             -- PnL
#             -- =====================================
#             SUM(
#                 CASE
#                     WHEN lower(account_subclass) = 'sales'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS revenue,

#             SUM(
#                 CASE
#                     WHEN lower(account_subclass) = 'cost of sales'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS cogs,

#             SUM(
#                 CASE
#                     WHEN lower(account_subclass) = 'operating expenses'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS operating_expenses,

#             SUM(
#                 CASE
#                     WHEN lower(account_subclass) = 'depreciation & amortization'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS depreciation,

#             SUM(
#                 CASE
#                     WHEN lower(account_subclass) = 'taxation'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS tax,


#             -- =====================================
#             -- ASSETS
#             -- =====================================
#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'cash & cash equivalents'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS cash,

#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'receivables'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS receivables,

#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'inventory'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS inventory,

#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'property, plant & equipment'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS ppe,

#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'accumulated depreciation'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS acc_dep,


#             -- =====================================
#             -- LIABILITIES
#             -- =====================================
#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'trade payables'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS trade_payables,

#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'other payables'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS other_payables,


#             -- =====================================
#             -- EQUITY
#             -- =====================================
#             SUM(
#                 CASE
#                     WHEN lower(account_name) = 'share capital'
#                     THEN balance
#                     ELSE 0
#                 END
#             ) AS share_capital

#         FROM fact_gl_recon

#         WHERE company_id = :company_id
#           AND batch_id = :batch_id
#           AND year = :year
#           AND month BETWEEN :month_start AND :month_end
#           AND (:lob IS NULL OR lob = :lob)

#     """), {
#         "company_id": user.company_id,
#         "batch_id": batch_id,
#         "year": year,
#         "month_start": month_start,
#         "month_end": month_end,
#         "lob": lob
#     }).mappings().first()

#     if not result:
#         return {
#             "success": False,
#             "message": "No data found"
#         }

#     # ==========================================
#     # VALUES
#     # ==========================================
#     revenue = float(result["revenue"] or 0)
#     cogs = float(result["cogs"] or 0)

#     operating_expenses = float(
#         result["operating_expenses"] or 0
#     )

#     depreciation = float(
#         result["depreciation"] or 0
#     )

#     tax = float(result["tax"] or 0)

#     cash = float(result["cash"] or 0)

#     receivables = float(
#         result["receivables"] or 0
#     )

#     inventory = float(
#         result["inventory"] or 0
#     )

#     ppe = float(result["ppe"] or 0)

#     acc_dep = float(
#         result["acc_dep"] or 0
#     )

#     trade_payables = float(
#         result["trade_payables"] or 0
#     )

#     other_payables = float(
#         result["other_payables"] or 0
#     )

#     share_capital = float(
#         result["share_capital"] or 0
#     )

#     # ==========================================
#     # DERIVED VALUES
#     # ==========================================
#     gross_profit = revenue - cogs

#     ebit = (
#         revenue
#         - cogs
#         - operating_expenses
#         - depreciation
#     )

#     net_income = ebit - tax

#     nopat = ebit - tax

#     current_assets = (
#         cash
#         + receivables
#         + inventory
#     )

#     total_assets = (
#         current_assets
#         + ppe
#         + acc_dep
#     )

#     current_liabilities = (
#         trade_payables
#         + other_payables
#     )

#     total_liabilities = current_liabilities

#     retained_earnings = net_income

#     equity = (
#         share_capital
#         + retained_earnings
#     )

#     # ==========================================
#     # KPI CALCULATIONS
#     # ==========================================

#     # eva = nopat - (
#     #     (assumed_wacc / 100)
#     #     * total_assets
#     # )
#     eva = nopat - assumed_wacc*(total_assets - total_liabilities)

#     roa = (
#         (net_income / total_assets) * 100
#         if total_assets else 0
#     )

#     roe = (
#         (net_income / equity) * 100
#         if equity else 0
#     )

#     berry_ratio = (
#         gross_profit /
#         (operating_expenses + depreciation)
#         if (operating_expenses + depreciation)
#         else 0
#     )

#     debt_to_equity = (
#         total_liabilities / equity
#         if equity else 0
#     )

#     working_capital_ratio = (
#         current_assets / current_liabilities
#         if current_liabilities else 0
#     )

#     quick_ratio = (
#         (current_assets - inventory)
#         / current_liabilities
#         if current_liabilities else 0
#     )

#     dio = (
#         (inventory * 365) / cogs
#         if cogs and inventory else None
#     )

#     dpo = (
#         (trade_payables * 365) / cogs
#         if cogs else 0
#     )

#     # dso = (
#     #     (receivables * 365) / revenue
#     #     if revenue else 0
#     # )

#     dso = (
#         (receivables * 365) / cogs
#         if revenue else 0
#      )

#     ccc = (
#         dso + dio - dpo
#         if dio is not None
#         else None
#     )

#     # ==========================================
#     # FINAL RESPONSE
#     # ==========================================
#     data = {

#         "eva": {
#             "formula":
#                 "NOPAT - (WACC × Total Capital)",

#             "value": round(eva, 2),

#             "benchmark": "> 0 is good",

#             "status": (
#                 "Good"
#                 if eva > 0
#                 else "Poor"
#             ),

#             "details": {
#                 "ebit": round(ebit, 2),
#                 "taxes": round(tax, 2),
#                 "nopat": round(nopat, 2),
#                 "total_capital": round(total_assets, 2),
#                 "assumed_wacc_percent": assumed_wacc
#             }
#         },

#         "roa": {

#             "formula":
#                 "Net Income / Total Assets",

#             "value": round(roa, 2),

#             "unit": "%",

#             "benchmark": {
#                 "good": "> 5%",
#                 "excellent": "> 20%"
#             },

#             "status": (
#                 "Excellent"
#                 if roa > 20
#                 else "Good"
#                 if roa > 5
#                 else "Weak"
#             ),

#             "details": {
#                 "net_income": round(net_income, 2),
#                 "total_assets": round(total_assets, 2)
#             }
#         },

#         "roe": {

#             "formula":
#                 "Net Income / Shareholder Equity",

#             "value": round(roe, 2),

#             "unit": "%",

#             "benchmark":
#                 "12% - 17%; higher the better",

#             "status": (
#                 "Strong"
#                 if roe >= 12
#                 else "Weak"
#             ),

#             "details": {

#                 "net_income":
#                     round(net_income, 2),

#                 "share_capital":
#                     round(share_capital, 2),

#                 "retained_earnings":
#                     round(retained_earnings, 2),

#                 "shareholder_equity":
#                     round(equity, 2)
#             }
#         },

#         "berry_ratio": {

#             "formula":
#                 "Gross Profit / Operating Expenses",

#             "value":
#                 round(berry_ratio, 2),

#             "benchmark":
#                 "> 1 is good",

#             "status": (
#                 "Good"
#                 if berry_ratio > 1
#                 else "Poor"
#             ),

#             "details": {

#                 "gross_profit":
#                     round(gross_profit, 2),

#                 "operating_expenses":
#                     round(
#                         operating_expenses
#                         + depreciation,
#                         2
#                     ),

#                 "revenue":
#                     round(revenue, 2),

#                 "cogs":
#                     round(cogs, 2),

#                 "sg_and_a":
#                     round(
#                         operating_expenses,
#                         2
#                     ),

#                 "depreciation_and_amortization":
#                     round(depreciation, 2)
#             }
#         },

#         "debt_to_equity": {

#             "formula":
#                 "Total Liabilities / Shareholder Equity",

#             "value":
#                 round(debt_to_equity, 2),

#             "benchmark":
#                 "1 - 1.5; higher the riskier",

#             "status": (
#                 "Risky"
#                 if debt_to_equity > 1.5
#                 else "Healthy"
#             ),

#             "details": {

#                 "total_liabilities":
#                     round(total_liabilities, 2),

#                 "shareholder_equity":
#                     round(equity, 2)
#             }
#         },

#         "working_capital_ratio": {

#             "formula":
#                 "Current Assets / Current Liabilities",

#             "value":
#                 round(working_capital_ratio, 2),

#             "benchmark":
#                 "1.5 - 2 is considered good",

#             "status": (
#                 "Healthy"
#                 if working_capital_ratio >= 1.5
#                 else "Risky"
#             ),

#             "details": {

#                 "current_assets":
#                     round(current_assets, 2),

#                 "current_liabilities":
#                     round(current_liabilities, 2)
#             }
#         },

#         "quick_ratio": {

#             "formula":
#                 "(Current Assets - Inventory) / Current Liabilities",

#             "value":
#                 round(quick_ratio, 2),

#             "benchmark":
#                 "Industry ratio is 0.31; higher the better",

#             "status": (
#                 "Healthy"
#                 if quick_ratio >= 1
#                 else "Risky"
#             ),

#             "details": {

#                 "current_assets":
#                     round(current_assets, 2),

#                 "inventory":
#                     round(inventory, 2),

#                 "current_liabilities":
#                     round(current_liabilities, 2)
#             }
#         },

#         "dio": {

#             "formula":
#                 "Average Inventory × 365 / COGS",

#             "value":
#                 round(dio, 2)
#                 if dio is not None
#                 else None,

#             "benchmark":
#                 "40 - 60 days",

#             "status": (
#                 "Healthy"
#                 if dio and 40 <= dio <= 60
#                 else "Unavailable"
#             ),

#             "details": {

#                 "ending_inventory":
#                     round(inventory, 2),

#                 "average_inventory":
#                     round(inventory, 2)
#                     if inventory else None,

#                 "cogs":
#                     round(cogs, 2)
#             }
#         },

#         "dpo": {

#             "formula":
#                 "Average Accounts Payable × 365 / COGS",

#             "value":
#                 round(dpo, 2),

#             "benchmark":
#                 "30 - 45 days depending on payment terms",

#             "status": (
#                 "Healthy"
#                 if 30 <= dpo <= 45
#                 else "Risky"
#             ),

#             "details": {

#                 "ending_accounts_payable":
#                     round(trade_payables, 2),

#                 "average_accounts_payable":
#                     round(trade_payables, 2),

#                 "cogs":
#                     round(cogs, 2)
#             }
#         },

#         "dso": {

#             "formula":
#                 "Average Accounts Receivable × 365 / Revenue",

#             "value":
#                 round(dso, 2),

#             "benchmark":
#                 "7 for retail industry; lower the better",

#             "status": (
#                 "Healthy"
#                 if dso <= 45
#                 else "Risky"
#             ),

#             "details": {

#                 "ending_accounts_receivable":
#                     round(receivables, 2),

#                 "average_accounts_receivable":
#                     round(receivables, 2),

#                 "revenue":
#                     round(revenue, 2)
#             }
#         },

#         "ccc": {

#             "formula":
#                 "DSO + DIO - DPO",

#             "value":
#                 round(ccc, 2)
#                 if ccc is not None
#                 else None,

#             "benchmark":
#                 "Lower is better",

#             "status": (
#                 "Healthy"
#                 if ccc and ccc < 60
#                 else "Unavailable"
#             ),

#             "details": {

#                 "dso":
#                     round(dso, 2),

#                 "dio":
#                     round(dio, 2)
#                     if dio is not None
#                     else None,

#                 "dpo":
#                     round(dpo, 2)
#             }
#         }
#     }

#     return {
#         "success": True,
#         "data": data
#     }






# reporting/kpi.py

# reporting/kpi.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user
from models import User

router = APIRouter(tags=["KPI Reporting"])


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
# KPI API
# ==========================================
@router.get("/monthly")
def get_monthly_kpis(
    batch_id: int,
    year: int,
    month_start: int,
    month_end: int,
    lob: str | None = None,
    assumed_wacc: float = 0.1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # ==========================================
    # CURRENT PERIOD DATA
    # ==========================================
    result = db.execute(text("""
        SELECT

            -- =====================================
            -- PnL
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_subclass) = 'sales'
                    THEN balance
                    ELSE 0
                END
            ) AS revenue,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'cost of sales'
                    THEN balance
                    ELSE 0
                END
            ) AS cogs,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'operating expenses'
                    THEN balance
                    ELSE 0
                END
            ) AS operating_expenses,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'depreciation & amortization'
                    THEN balance
                    ELSE 0
                END
            ) AS depreciation,

            SUM(
                CASE
                    WHEN lower(account_subclass) = 'taxation'
                    THEN balance
                    ELSE 0
                END
            ) AS tax,

            -- =====================================
            -- ASSETS
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'cash & cash equivalents'
                    THEN balance
                    ELSE 0
                END
            ) AS cash,

            SUM(
                CASE
                    WHEN lower(account_name) = 'receivables'
                    THEN balance
                    ELSE 0
                END
            ) AS receivables,

            SUM(
                CASE
                    WHEN lower(account_name) = 'inventory'
                    THEN balance
                    ELSE 0
                END
            ) AS inventory,

            SUM(
                CASE
                    WHEN lower(account_name) = 'property, plant & equipment'
                    THEN balance
                    ELSE 0
                END
            ) AS ppe,

            SUM(
                CASE
                    WHEN lower(account_name) = 'accumulated depreciation'
                    THEN balance
                    ELSE 0
                END
            ) AS acc_dep,

            -- =====================================
            -- LIABILITIES
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'trade payables'
                    THEN balance
                    ELSE 0
                END
            ) AS trade_payables,

            SUM(
                CASE
                    WHEN lower(account_name) = 'other payables'
                    THEN balance
                    ELSE 0
                END
            ) AS other_payables,

            -- =====================================
            -- EQUITY
            -- =====================================
            SUM(
                CASE
                    WHEN lower(account_name) = 'share capital'
                    THEN balance
                    ELSE 0
                END
            ) AS share_capital

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

    if not result:
        return {
            "success": False,
            "message": "No data found"
        }

    # ==========================================
    # PREVIOUS PERIOD LOGIC
    # ==========================================
    if month_start == 1:
        prev_year = year - 1
        prev_month_start = 1
        prev_month_end = 12
    else:
        prev_year = year
        prev_month_start = 1
        prev_month_end = month_start - 1

    # ==========================================
    # PREVIOUS PERIOD DATA
    # ==========================================
    previous_result = db.execute(text("""
        SELECT

            SUM(
                CASE
                    WHEN lower(account_name) = 'inventory'
                    THEN balance
                    ELSE 0
                END
            ) AS beginning_inventory,

            SUM(
                CASE
                    WHEN lower(account_name) = 'trade payables'
                    THEN balance
                    ELSE 0
                END
            ) AS beginning_trade_payables,

            SUM(
                CASE
                    WHEN lower(account_name) = 'receivables'
                    THEN balance
                    ELSE 0
                END
            ) AS beginning_receivables

        FROM fact_gl_recon

        WHERE company_id = :company_id
          AND batch_id = :batch_id
          AND year = :prev_year
          AND month BETWEEN :prev_month_start AND :prev_month_end
          AND (:lob IS NULL OR lob = :lob)

    """), {
        "company_id": user.company_id,
        "batch_id": batch_id,
        "prev_year": prev_year,
        "prev_month_start": prev_month_start,
        "prev_month_end": prev_month_end,
        "lob": lob
    }).mappings().first()

    # ==========================================
    # CURRENT VALUES
    # ==========================================
    revenue = float(result["revenue"] or 0)
    cogs = float(result["cogs"] or 0)

    operating_expenses = float(
        result["operating_expenses"] or 0
    )

    depreciation = float(
        result["depreciation"] or 0
    )

    tax = float(result["tax"] or 0)

    cash = float(result["cash"] or 0)

    receivables = float(
        result["receivables"] or 0
    )

    inventory = float(
        result["inventory"] or 0
    )

    ppe = float(result["ppe"] or 0)

    acc_dep = float(
        result["acc_dep"] or 0
    )

    trade_payables = float(
        result["trade_payables"] or 0
    )

    other_payables = float(
        result["other_payables"] or 0
    )

    share_capital = float(
        result["share_capital"] or 0
    )

    # ==========================================
    # PREVIOUS VALUES
    # ==========================================
    beginning_inventory = float(
        previous_result["beginning_inventory"] or 0
    )

    beginning_trade_payables = float(
        previous_result["beginning_trade_payables"] or 0
    )

    beginning_receivables = float(
        previous_result["beginning_receivables"] or 0
    )

    # ==========================================
    # AVERAGE VALUES
    # ==========================================
    average_inventory = (
        (beginning_inventory + inventory) / 2
        if beginning_inventory > 0
        else inventory
    )

    average_trade_payables = (
        (beginning_trade_payables + trade_payables) / 2
        if beginning_trade_payables > 0
        else trade_payables
    )

    average_receivables = (
        (beginning_receivables + receivables) / 2
        if beginning_receivables > 0
        else receivables
    )

    # ==========================================
    # DERIVED VALUES
    # ==========================================
    gross_profit = revenue - cogs

    ebit = (
        revenue
        - cogs
        - operating_expenses
        - depreciation
    )

    net_income = ebit - tax

    nopat = ebit - tax

    current_assets = (
        cash
        + receivables
        + inventory
    )

    total_assets = (
        current_assets
        + ppe
        + acc_dep
    )

    current_liabilities = (
        trade_payables
        + other_payables
    )

    total_liabilities = current_liabilities

    retained_earnings = net_income

    equity = (
        share_capital
        + retained_earnings
    )

    # ==========================================
    # KPI CALCULATIONS
    # ==========================================
    eva = nopat - assumed_wacc * (
        total_assets - total_liabilities
    )

    roa = (
        (net_income / total_assets) * 100
        if total_assets else 0
    )

    roe = (
        (net_income / equity) * 100
        if equity else 0
    )

    berry_ratio = (
        gross_profit /
        (operating_expenses + depreciation)
        if (operating_expenses + depreciation)
        else 0
    )

    debt_to_equity = (
        total_liabilities / equity
        if equity else 0
    )

    working_capital_ratio = (
        current_assets / current_liabilities
        if current_liabilities else 0
    )

    quick_ratio = (
        (current_assets - inventory)
        / current_liabilities
        if current_liabilities else 0
    )

    # ==========================================
    # DIO
    # ==========================================
    dio = (
        (average_inventory * 365) / cogs
        if cogs else None
    )

    # ==========================================
    # DPO
    # ==========================================
    dpo = (
        (average_trade_payables * 365) / cogs
        if cogs else None
    )

    # ==========================================
    # DSO
    # ==========================================
    # dso = (
    #     (average_receivables * 365) / revenue
    #     if revenue else None
    # )

    dso = (
        (average_receivables * 365) / cogs
        if revenue else None
    )

    # ==========================================
    # CCC
    # ==========================================
    ccc = (
        dso + dio - dpo
        if (
            dio is not None
            and dpo is not None
            and dso is not None
        )
        else None
    )

    # ==========================================
    # FINAL RESPONSE
    # ==========================================
    data = {

        "eva": {
            "formula":
                "NOPAT - (WACC × Total Capital)",

            "value": round(eva, 2),

            "benchmark": "> 0 is good",

            "status": (
                "Good"
                if eva > 0
                else "Poor"
            ),

            "details": {
                "ebit": round(ebit, 2),
                "taxes": round(tax, 2),
                "nopat": round(nopat, 2),
                "total_capital": round(total_assets, 2),
                "assumed_wacc_percent": assumed_wacc
            }
        },

        "roa": {

            "formula":
                "Net Income / Total Assets",

            "value": round(roa, 2),

            "unit": "%",

            "benchmark": {
                "good": "> 5%",
                "excellent": "> 20%"
            },

            "status": (
                "Excellent"
                if roa > 20
                else "Good"
                if roa > 5
                else "Weak"
            ),

            "details": {
                "net_income": round(net_income, 2),
                "total_assets": round(total_assets, 2)
            }
        },

        "roe": {

            "formula":
                "Net Income / Shareholder Equity",

            "value": round(roe, 2),

            "unit": "%",

            "benchmark":
                "12% - 17%; higher the better",

            "status": (
                "Strong"
                if roe >= 12
                else "Weak"
            ),

            "details": {

                "net_income":
                    round(net_income, 2),

                "share_capital":
                    round(share_capital, 2),

                "retained_earnings":
                    round(retained_earnings, 2),

                "shareholder_equity":
                    round(equity, 2)
            }
        },

        "berry_ratio": {

            "formula":
                "Gross Profit / Operating Expenses",

            "value":
                round(berry_ratio, 2),

            "benchmark":
                "> 1 is good",

            "status": (
                "Good"
                if berry_ratio > 1
                else "Poor"
            ),

            "details": {

                "gross_profit":
                    round(gross_profit, 2),

                "operating_expenses":
                    round(
                        operating_expenses
                        + depreciation,
                        2
                    ),

                "revenue":
                    round(revenue, 2),

                "cogs":
                    round(cogs, 2),

                "sg_and_a":
                    round(
                        operating_expenses,
                        2
                    ),

                "depreciation_and_amortization":
                    round(depreciation, 2)
            }
        },

        "debt_to_equity": {

            "formula":
                "Total Liabilities / Shareholder Equity",

            "value":
                round(debt_to_equity, 2),

            "benchmark":
                "1 - 1.5; higher the riskier",

            "status": (
                "Risky"
                if debt_to_equity > 1.5
                else "Healthy"
            ),

            "details": {

                "total_liabilities":
                    round(total_liabilities, 2),

                "shareholder_equity":
                    round(equity, 2)
            }
        },

        "working_capital_ratio": {

            "formula":
                "Current Assets / Current Liabilities",

            "value":
                round(working_capital_ratio, 2),

            "benchmark":
                "1.5 - 2 is considered good",

            "status": (
                "Healthy"
                if working_capital_ratio >= 1.5
                else "Risky"
            ),

            "details": {

                "current_assets":
                    round(current_assets, 2),

                "current_liabilities":
                    round(current_liabilities, 2)
            }
        },

        "quick_ratio": {

            "formula":
                "(Current Assets - Inventory) / Current Liabilities",

            "value":
                round(quick_ratio, 2),

            "benchmark":
                "Industry ratio is 0.31; higher the better",

            "status": (
                "Healthy"
                if quick_ratio >= 1
                else "Risky"
            ),

            "details": {

                "current_assets":
                    round(current_assets, 2),

                "inventory":
                    round(inventory, 2),

                "current_liabilities":
                    round(current_liabilities, 2)
            }
        },

        "dio": {

            "formula":
                "Average Inventory × 365 / COGS",

            "value":
                round(dio, 2)
                if dio is not None
                else None,

            "benchmark":
                "40 - 60 days",

            "status": (
                "Healthy"
                if dio and 40 <= dio <= 60
                else "Unavailable"
            ),

            "details": {

                "beginning_inventory":
                    round(beginning_inventory, 2),

                "ending_inventory":
                    round(inventory, 2),

                "average_inventory":
                    round(average_inventory, 2),

                "cogs":
                    round(cogs, 2)
            }
        },

        "dpo": {

            "formula":
                "Average Accounts Payable × 365 / COGS",

            "value":
                round(dpo, 2)
                if dpo is not None
                else None,

            "benchmark":
                "30 - 45 days depending on payment terms",

            "status": (
                "Healthy"
                if dpo and 30 <= dpo <= 45
                else "Risky"
            ),

            "details": {

                "beginning_accounts_payable":
                    round(beginning_trade_payables, 2),

                "ending_accounts_payable":
                    round(trade_payables, 2),

                "average_accounts_payable":
                    round(average_trade_payables, 2),

                "cogs":
                    round(cogs, 2)
            }
        },

        "dso": {

            "formula":
                "Average Accounts Receivable × 365 / COGS",

            "value":
                round(dso, 2)
                if dso is not None
                else None,

            "benchmark":
                "7 for retail industry; lower the better",

            "status": (
                "Healthy"
                if dso and dso <= 45
                else "Risky"
            ),

            "details": {

                "beginning_accounts_receivable":
                    round(beginning_receivables, 2),

                "ending_accounts_receivable":
                    round(receivables, 2),

                "average_accounts_receivable":
                    round(average_receivables, 2),

                "revenue":
                    round(revenue, 2)
            }
        },

        "ccc": {

            "formula":
                "DSO + DIO - DPO",

            "value":
                round(ccc, 2)
                if ccc is not None
                else None,

            "benchmark":
                "Lower is better",

            "status": (
                "Healthy"
                if ccc and ccc < 60
                else "Unavailable"
            ),

            "details": {

                "dso":
                    round(dso, 2)
                    if dso is not None
                    else None,

                "dio":
                    round(dio, 2)
                    if dio is not None
                    else None,

                "dpo":
                    round(dpo, 2)
                    if dpo is not None
                    else None
            }
        }
    }

    return {
        "success": True,
        "data": data
    }