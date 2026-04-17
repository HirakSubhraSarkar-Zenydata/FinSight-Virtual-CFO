from sqlalchemy import func
from decimal import Decimal
from datetime import datetime

from models import (
    FactTax,
    DimBSVTaxRate,
    FactSLAccountingWide,
    FactAssetMonthlyDepreciation
)


def process_fact_tax(db, company_id, batch_id):

    try:
        # =========================
        # 🔹 CLEAN OLD DATA (RERUN SAFE)
        # =========================
        db.query(FactTax).filter(
            FactTax.company_id == company_id,
            FactTax.batch_id == batch_id
        ).delete()

        # =========================
        # 🔹 GET BSV + TAX RATE
        # =========================
        bsv_row = db.query(DimBSVTaxRate).filter(
            DimBSVTaxRate.company_id == company_id,
            DimBSVTaxRate.batch_id == batch_id,
            DimBSVTaxRate.is_deleted == False
        ).first()

        if not bsv_row:
            raise Exception("BSV not found")

        bsv = bsv_row.bsv_code

        # ✅ FIXED: use tax_rate (already stored as decimal like 0.25)
        tax_rate = (
            Decimal(str(bsv_row.tax_rate))
            if bsv_row.tax_rate is not None
            else Decimal(0)
        )

        # =========================
        # 🔹 SUBLEDGER (GP, SGA)
        # =========================
        sl_data = db.query(
            FactSLAccountingWide.year,
            FactSLAccountingWide.month,
            func.sum(FactSLAccountingWide.gross_profit).label("gp"),
            func.sum(FactSLAccountingWide.sga).label("sga")
        ).filter(
            FactSLAccountingWide.company_id == company_id,
            FactSLAccountingWide.batch_id == batch_id
        ).group_by(
            FactSLAccountingWide.year,
            FactSLAccountingWide.month
        ).all()

        # (2021,1) → gp=100000, sga=40000
        # (2021,3) → gp=50000, sga=20000

        sl_map = {(r.year, r.month): r for r in sl_data}

        # =========================
        # 🔹 DEPRECIATION
        # =========================
        dep_data = db.query(
            FactAssetMonthlyDepreciation.year,
            FactAssetMonthlyDepreciation.month,
            func.sum(FactAssetMonthlyDepreciation.depreciation_amount).label("dep")
        ).filter(
            FactAssetMonthlyDepreciation.company_id == company_id,
            FactAssetMonthlyDepreciation.batch_id == batch_id
        ).group_by(
            FactAssetMonthlyDepreciation.year,
            FactAssetMonthlyDepreciation.month
        ).all()

        # (2021,1) →dep= 10000
        # (2021,2) →dep= 10000
        # (2021,3) →dep= 10000

        dep_map = {(r.year, r.month): r.dep for r in dep_data}

        # =========================
        # 🔹 YEARS
        # =========================
        years = list(set([r.year for r in sl_data] + [r.year for r in dep_data]))

        new_records = []

        for year in years:

            monthly_rows = []

            # =========================
            # 🔁 GENERATE 1–12 MONTHS
            # =========================
            for month in range(1, 13):

                sl = sl_map.get((year, month))

                gp = Decimal(str(sl.gp)) if sl and sl.gp is not None else None
                sga = Decimal(str(sl.sga)) if sl and sl.sga is not None else None
                dep = (
                    Decimal(str(dep_map.get((year, month))))
                    if dep_map.get((year, month))
                    else Decimal(0)
                )

                # =========================
                # 🔹 EBIT
                # =========================
                if gp is None and sga is None and dep == 0:
                    ebit = None
                else:
                    ebit = (gp or Decimal(0)) - (sga or Decimal(0)) - dep

                monthly_rows.append({
                    "year": year,
                    "month": month,
                    "gp": gp,
                    "sga": sga,
                    "dep": dep,
                    "ebit": ebit
                })

            # =========================
            # 🔹 TAX (YEARLY SPREAD)
            # =========================
            total_ebit = sum([r["ebit"] or Decimal(0) for r in monthly_rows])

            # 🔥 Optional (recommended): no tax if loss
            if total_ebit <= 0:
                monthly_tax = Decimal(0)
            else:
                monthly_tax = (total_ebit * tax_rate) / 12

            # =========================
            # 🔹 INSERT FINAL ROWS
            # =========================
            for r in monthly_rows:

                ebit = r["ebit"]

                if ebit is None:
                    tax = None
                    net_profit = None
                else:
                    tax = monthly_tax
                    net_profit = ebit - tax

                new_records.append(
                    FactTax(
                        company_id=company_id,
                        batch_id=batch_id,
                        year=r["year"],
                        month=r["month"],

                        gross_profit=r["gp"],
                        sga=r["sga"],
                        depreciation=r["dep"],

                        ebit=ebit,
                        tax=tax,
                        net_profit=net_profit,

                        # 🔹 Journal Entries
                        dr_account=f"{bsv}-0000-450",
                        dr_amount=tax,

                        cr_account=f"{bsv}-0000-122",
                        cr_amount=tax,

                        bsv_code=bsv,
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