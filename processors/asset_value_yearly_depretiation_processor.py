# from decimal import Decimal
# from datetime import datetime
# from models import DimAssetValue, FactAssetYearlyDepreciation


# def process_asset_yearly_depreciation(db, company_id, batch_id):
#     try:
#         query = db.query(DimAssetValue).filter(
#             DimAssetValue.company_id == company_id,
#             DimAssetValue.batch_id == batch_id,
#             # DimAssetValue.is_deleted == False
#         )

#         existing = {
#             (d.asset_id, d.year): True
#             for d in db.query(FactAssetYearlyDepreciation).filter(
#                 FactAssetYearlyDepreciation.company_id == company_id,
#                 FactAssetYearlyDepreciation.batch_id == batch_id
#             )
#         }

#         new_records = []

#         for asset in query.yield_per(500):

#             if not asset.useful_life_years or not asset.asset_value or not asset.year:
#                 continue

#             yearly_dep = Decimal(str(asset.asset_value)) / Decimal(asset.useful_life_years)

#             for i in range(asset.useful_life_years):
#                 year = asset.year + i

#                 if (asset.id, year) in existing:
#                     continue

#                 new_records.append(FactAssetYearlyDepreciation(
#                     company_id=company_id,
#                     asset_id=asset.id,
#                     asset_name=asset.asset_name,
#                     year=year,
#                     depreciation_amount=yearly_dep,
#                     coa_id=asset.coa_id,
#                     account_key=asset.account_key,
#                     batch_id=batch_id,
#                     file_id=asset.file_id,
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
from models import DimAssetValue, FactAssetYearlyDepreciation


def process_asset_yearly_depreciation(db, company_id, batch_id):
    try:
        # =========================
        # 🔹 FETCH ASSETS
        # =========================
        assets = db.query(DimAssetValue).filter(
            DimAssetValue.company_id == company_id,
            DimAssetValue.batch_id == batch_id,
            DimAssetValue.is_deleted == False
        )

        # =========================
        # 🔹 EXISTING RECORDS (DEDUP)
        # =========================
        existing = {
            (d.asset_id, d.year)
            for d in db.query(FactAssetYearlyDepreciation).filter(
                FactAssetYearlyDepreciation.company_id == company_id,
                FactAssetYearlyDepreciation.batch_id == batch_id
            )
        }

        new_records = []

        # =========================
        # 🔹 PROCESS LOOP
        # =========================
        for asset in assets.yield_per(500):

            if not asset.useful_life_years or not asset.asset_value or not asset.year:
                continue

            # =========================
            # 🔹 YEARLY DEPRECIATION
            # =========================
            yearly_dep = (
                Decimal(str(asset.asset_value)) /
                Decimal(asset.useful_life_years)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # =========================
            # 🔹 LOOP THROUGH LIFE
            # =========================
            for i in range(asset.useful_life_years):
                year = asset.year + i

                if (asset.id, year) in existing:
                    continue

                new_records.append(
                    FactAssetYearlyDepreciation(
                        company_id=company_id,
                        asset_id=asset.id,

                        # ❌ removed asset_name (not needed, derive via join)

                        year=year,
                        depreciation_amount=yearly_dep,

                        # ✅ BALANCE SHEET ACCOUNT
                        bs_asset_account_key=asset.bs_asset_account_key,

                        batch_id=batch_id,
                        file_id=asset.file_id,
                        created_at=datetime.utcnow()
                    )
                )

        # =========================
        # 🔹 BULK INSERT
        # =========================
        if new_records:
            db.bulk_save_objects(new_records)
            db.commit()

    except Exception as e:
        db.rollback()
        raise e