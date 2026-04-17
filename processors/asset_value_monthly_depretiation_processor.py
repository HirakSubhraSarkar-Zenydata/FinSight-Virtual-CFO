
# from decimal import Decimal
# from datetime import datetime
# from models import FactAssetYearlyDepreciation, FactAssetMonthlyDepreciation


# def process_asset_monthly_depreciation(db, company_id, batch_id):
#     try:
#         yearly_query = db.query(FactAssetYearlyDepreciation).filter(
#             FactAssetYearlyDepreciation.company_id == company_id,
#             FactAssetYearlyDepreciation.batch_id == batch_id
#         )

#         existing = {
#             (d.asset_id, d.year, d.month): True
#             for d in db.query(FactAssetMonthlyDepreciation).filter(
#                 FactAssetMonthlyDepreciation.company_id == company_id,
#                 FactAssetMonthlyDepreciation.batch_id == batch_id
#             )
#         }

#         new_records = []

#         for record in yearly_query.yield_per(500):

#             if not record.depreciation_amount:
#                 continue

#             monthly = Decimal(str(record.depreciation_amount)) / Decimal(12)

#             for m in range(1, 13):

#                 if (record.asset_id, record.year, m) in existing:
#                     continue

#                 new_records.append(FactAssetMonthlyDepreciation(
#                     company_id=company_id,
#                     asset_id=record.asset_id,
#                     asset_name=record.asset_name,
#                     year=record.year,
#                     month=m,
#                     depreciation_amount=monthly,
#                     coa_id=record.coa_id,
#                     account_key=record.account_key,
#                     batch_id=batch_id,
#                     file_id=record.file_id,
#                     created_at=datetime.utcnow()
#                 ))

#         if new_records:
#             db.bulk_save_objects(new_records)
#             db.commit()

#     except:
#         db.rollback()
#         raise


from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from models import (
    FactAssetYearlyDepreciation,
    FactAssetMonthlyDepreciation,
    DimAssetValue,
    DimCOA
)


# ============================================================
# 🔹 NORMALIZER
# ============================================================
def normalize(text):
    return str(text or "").strip().lower()


# ============================================================
# 🔹 BUILD P&L DEPRECIATION MAP (FULL COA HIERARCHY)
# ============================================================
def build_pnl_dep_map(db, company_id, batch_id):

    pnl_dep_accounts = []

    query = db.query(DimCOA).filter(
        DimCOA.company_id == company_id,
        DimCOA.batch_id == batch_id,
        DimCOA.is_deleted == False
    )

    for coa in query:

        report = normalize(coa.report)
        class_name = normalize(coa.class_name)
        subclass = normalize(coa.subclass)
        subclass2 = normalize(coa.subclass2)
        account = normalize(coa.account)
        subaccount = normalize(coa.subaccount)

        # ✅ STRICT FILTER (VERY IMPORTANT)
        if (
            report == "profit and loss"
            and class_name == "operating account"
            and subclass == "depreciation & amortization"
            and subclass2 == "depreciation"
        ):
            pnl_dep_accounts.append({
                "coa_id": coa.id,
                "account_key": coa.account_key,
                "account": account,
                "subaccount": subaccount
            })

    return pnl_dep_accounts


# ============================================================
# 🔹 MATCH P&L DEPRECIATION ACCOUNT
# ============================================================
def match_pnl_account(asset_name, pnl_dep_accounts):

    asset_lower = normalize(asset_name)

    # =========================
    # ✅ STEP 1: DIRECT MATCH
    # =========================
    for acc in pnl_dep_accounts:
        if acc["subaccount"] in asset_lower:
            return acc

    # =========================
    # ✅ STEP 2: LOGICAL MATCH
    # =========================
    for acc in pnl_dep_accounts:

        name = acc["subaccount"]

        if "vehicle" in asset_lower and "vehicle" in name:
            return acc

        if "machinery" in asset_lower or "equipment" in asset_lower:
            if "equipment" in name:
                return acc

        if "furniture" in asset_lower:
            if "furniture" in name:
                return acc

    # =========================
    # ❗ NO FALLBACK
    # =========================
    return {
        "coa_id": None,
        "account_key": None
    }


# ============================================================
# 🔹 MAIN FUNCTION (FINAL)
# ============================================================
def process_asset_monthly_depreciation(db, company_id, batch_id):
    try:

        # =========================
        # 🔹 LOAD ASSETS
        # =========================
        asset_map = {
            a.id: a
            for a in db.query(DimAssetValue).filter(
                DimAssetValue.company_id == company_id,
                DimAssetValue.batch_id == batch_id,
                DimAssetValue.is_deleted == False
            )
        }

        # =========================
        # 🔹 LOAD YEARLY
        # =========================
        yearly_query = db.query(FactAssetYearlyDepreciation).filter(
            FactAssetYearlyDepreciation.company_id == company_id,
            FactAssetYearlyDepreciation.batch_id == batch_id
        )

        # =========================
        # 🔹 BUILD P&L MAP
        # =========================
        pnl_dep_accounts = build_pnl_dep_map(db, company_id, batch_id)

        # =========================
        # 🔹 EXISTING CHECK
        # =========================
        existing = {
            (d.asset_id, d.year, d.month)
            for d in db.query(FactAssetMonthlyDepreciation).filter(
                FactAssetMonthlyDepreciation.company_id == company_id,
                FactAssetMonthlyDepreciation.batch_id == batch_id
            )
        }

        new_records = []

        # =========================
        # 🔹 PROCESS LOOP
        # =========================
        for record in yearly_query.yield_per(500):

            asset = asset_map.get(record.asset_id)
            if not asset:
                continue

            # ✅ ONLY FIRST YEAR
            if record.year != asset.year:
                continue

            if not record.depreciation_amount:
                continue

            # =========================
            # 🔹 MONTHLY VALUE
            # =========================
            monthly_amount = (
                Decimal(str(record.depreciation_amount)) / Decimal(12)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # =========================
            # 🔹 P&L MAPPING (NEW LOGIC)
            # =========================
            pnl_coa = match_pnl_account(
                asset.asset_name, pnl_dep_accounts
            )

            # =========================
            # 🔹 BS MAPPING (FROM DIM ✔)
            # =========================
            bs_coa_id = asset.bs_accumulated_dep_coa_id
            bs_account_key = asset.bs_accumulated_dep_account_key

            # =========================
            # 🔹 CREATE MONTHS
            # =========================
            for month in range(1, 13):

                if (record.asset_id, record.year, month) in existing:
                    continue

                new_records.append(
                    FactAssetMonthlyDepreciation(
                        company_id=company_id,
                        asset_id=record.asset_id,
                        year=record.year,
                        month=month,
                        depreciation_amount=monthly_amount,

                        # ✅ P&L (FIXED)
                        pnl_depreciation_coa_id=pnl_coa["coa_id"],
                        pnl_depreciation_account_key=pnl_coa["account_key"],

                        # ✅ BS (FROM DIM)
                        bs_accumulated_dep_coa_id=bs_coa_id,
                        bs_accumulated_dep_account_key=bs_account_key,

                        batch_id=batch_id,
                        file_id=asset.file_id,
                        created_at=datetime.utcnow()
                    )
                )

        # =========================
        # 🔹 SAVE
        # =========================
        if new_records:
            db.bulk_save_objects(new_records)
            db.commit()

    except Exception as e:
        db.rollback()
        raise e