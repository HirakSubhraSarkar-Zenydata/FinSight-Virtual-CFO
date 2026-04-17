# from datetime import datetime
# from decimal import Decimal
# from models import FactAssetMonthlyDepreciation, FactAssetJournal, DimCOA


# def process_asset_journal(db, company_id, batch_id):
#     try:
#         # ✅ get BSV code (assume one per batch)
#         bsv = "2040"  # replace with lookup if needed

#         monthly_query = db.query(FactAssetMonthlyDepreciation).filter(
#             FactAssetMonthlyDepreciation.company_id == company_id,
#             FactAssetMonthlyDepreciation.batch_id == batch_id
#         )

#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id
#             )
#         }

#         new_records = []

#         for rec in monthly_query.yield_per(500):

#             if not rec.account_key:
#                 continue

#             amount = Decimal(str(rec.depreciation_amount))

#             # =========================
#             # DR (Expense)
#             # =========================
#             dr_account = rec.account_key
#             dr_code = f"{bsv}-0000-{dr_account}"

#             new_records.append(FactAssetJournal(
#                 company_id=company_id,
#                 asset_id=rec.asset_id,
#                 asset_name=rec.asset_name,
#                 year=rec.year,
#                 month=rec.month,
#                 natural_account=dr_account,
#                 account_code=dr_code,
#                 dr_amount=amount,
#                 cr_amount=None,
#                 coa_id=rec.coa_id,
#                 account_key=rec.account_key,
#                 bsv_code=bsv,
#                 remarks=f"Depreciation {rec.month}/{rec.year}",
#                 batch_id=batch_id,
#                 file_id=rec.file_id,
#                 created_at=datetime.utcnow()
#             ))

#             # =========================
#             # CR (Accumulated Dep)
#             # rule: +1 (380→381, 390→391)
#             # =========================
#             cr_account = rec.account_key + 1
#             cr_code = f"{bsv}-0000-{cr_account}"

#             new_records.append(FactAssetJournal(
#                 company_id=company_id,
#                 asset_id=rec.asset_id,
#                 asset_name=rec.asset_name,
#                 year=rec.year,
#                 month=rec.month,
#                 natural_account=cr_account,
#                 account_code=cr_code,
#                 dr_amount=None,
#                 cr_amount=amount,
#                 coa_id=None,
#                 account_key=cr_account,
#                 bsv_code=bsv,
#                 remarks=f"Accumulated Dep {rec.month}/{rec.year}",
#                 batch_id=batch_id,
#                 file_id=rec.file_id,
#                 created_at=datetime.utcnow()
#             ))

#         if new_records:
#             db.bulk_save_objects(new_records)
#             db.commit()

#     except:
#         db.rollback()
#         raise


from datetime import datetime
from decimal import Decimal
from models import (
    DimAssetValue,
    FactAssetMonthlyDepreciation,
    FactAssetJournal,
    DimBSVTaxRate
)


def process_asset_journal(db, company_id, batch_id):
    try:
        # =========================
        # 🔹 GET BSV CODE
        # =========================
        bsv_row = db.query(DimBSVTaxRate).filter(
            DimBSVTaxRate.company_id == company_id,
            DimBSVTaxRate.batch_id == batch_id,
            DimBSVTaxRate.is_deleted == False
        ).first()

        if not bsv_row or not bsv_row.bsv_code:
            raise Exception("BSV code not found")

        bsv = bsv_row.bsv_code

        # =========================
        # 🔹 EXISTING (DEDUP)
        # =========================
        existing = {
            (j.asset_id, j.year, j.month, j.natural_account)
            for j in db.query(FactAssetJournal).filter(
                FactAssetJournal.company_id == company_id,
                FactAssetJournal.batch_id == batch_id
            )
        }

        new_records = []

        # ============================================================
        # 🔥 1. ONE-TIME ENTRIES (ASSET PURCHASE)
        # ============================================================
        asset_query = db.query(DimAssetValue).filter(
            DimAssetValue.company_id == company_id,
            DimAssetValue.batch_id == batch_id,
            DimAssetValue.is_deleted == False
        )

        CASH_ACCOUNT = 10  # ⚠️ Ideally fetch from COA (Cash account)

        for asset in asset_query.yield_per(500):

            if not asset.asset_value or not asset.bs_asset_account_key:
                continue

            year = asset.year
            month = 1  # Jan

            amount = Decimal(str(asset.asset_value))

            # 🔹 DR → ASSET
            if (asset.id, year, month, asset.bs_asset_account_key) not in existing:
                new_records.append(
                    FactAssetJournal(
                        company_id=company_id,
                        asset_id=asset.id,
                        year=year,
                        month=month,

                        natural_account=asset.bs_asset_account_key,
                        account_code=f"{bsv}-0000-{asset.bs_asset_account_key}",

                        dr_amount=amount,
                        cr_amount=None,

                        bsv_code=bsv,
                        remarks=f"Asset Purchase {month}/{year}",

                        batch_id=batch_id,
                        file_id=asset.file_id,
                        created_at=datetime.utcnow()
                    )
                )

            # 🔹 CR → CASH
            if (asset.id, year, month, CASH_ACCOUNT) not in existing:
                new_records.append(
                    FactAssetJournal(
                        company_id=company_id,
                        asset_id=asset.id,
                        year=year,
                        month=month,

                        natural_account=CASH_ACCOUNT,
                        account_code=f"{bsv}-0000-{CASH_ACCOUNT}",

                        dr_amount=None,
                        cr_amount=amount,

                        bsv_code=bsv,
                        remarks=f"Cash Payment {month}/{year}",

                        batch_id=batch_id,
                        file_id=asset.file_id,
                        created_at=datetime.utcnow()
                    )
                )

        # ============================================================
        # 🔥 2. MONTHLY DEPRECIATION ENTRIES
        # ============================================================
        monthly_query = db.query(FactAssetMonthlyDepreciation).filter(
            FactAssetMonthlyDepreciation.company_id == company_id,
            FactAssetMonthlyDepreciation.batch_id == batch_id
        )

        for rec in monthly_query.yield_per(500):

            if not rec.depreciation_amount:
                continue

            pnl_account = rec.pnl_depreciation_account_key
            bs_account = rec.bs_accumulated_dep_account_key

            if not pnl_account or not bs_account:
                continue

            amount = Decimal(str(rec.depreciation_amount))

            # 🔹 DR → P&L Depreciation
            if (rec.asset_id, rec.year, rec.month, pnl_account) not in existing:
                new_records.append(
                    FactAssetJournal(
                        company_id=company_id,
                        asset_id=rec.asset_id,
                        year=rec.year,
                        month=rec.month,

                        natural_account=pnl_account,
                        account_code=f"{bsv}-0000-{pnl_account}",

                        dr_amount=amount,
                        cr_amount=None,

                        bsv_code=bsv,
                        remarks=f"Depreciation {rec.month}/{rec.year}",

                        batch_id=batch_id,
                        file_id=rec.file_id,
                        created_at=datetime.utcnow()
                    )
                )

            # 🔹 CR → ACCUMULATED DEP
            if (rec.asset_id, rec.year, rec.month, bs_account) not in existing:
                new_records.append(
                    FactAssetJournal(
                        company_id=company_id,
                        asset_id=rec.asset_id,
                        year=rec.year,
                        month=rec.month,

                        natural_account=bs_account,
                        account_code=f"{bsv}-0000-{bs_account}",

                        dr_amount=None,
                        cr_amount=amount,

                        bsv_code=bsv,
                        remarks=f"Accumulated Dep {rec.month}/{rec.year}",

                        batch_id=batch_id,
                        file_id=rec.file_id,
                        created_at=datetime.utcnow()
                    )
                )

        # ============================================================
        # 🔹 SAVE
        # ============================================================
        if new_records:
            db.bulk_save_objects(new_records)
            db.commit()

    except Exception as e:
        db.rollback()
        raise e