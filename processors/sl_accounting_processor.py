# from models import FactSLAccounting, FactSubLedger


# def process_slaccounting(db, company_id, batch_id):

#     facts = db.query(FactSubLedger).filter_by(
#         company_id=company_id
#     ).all()

#     for f in facts:

#         # Revenue Entry
#         db.add(FactSLAccounting(
#             company_id=company_id,
#             subledger_id=f.id,
#             journal_group_id=f"JRN-{f.id}",
#             line_type="REVENUE",
#             movement_type="STANDARD",
#             entry_index=1,
#             side="CR",
#             account_code="REV",
#             amount=f.revenue,
#             date=f.date
#         ))

#         # COGS Entry
#         db.add(FactSLAccounting(
#             company_id=company_id,
#             subledger_id=f.id,
#             journal_group_id=f"JRN-{f.id}",
#             line_type="COGS",
#             movement_type="STANDARD",
#             entry_index=2,
#             side="DR",
#             account_code="COGS",
#             amount=f.cogs,
#             date=f.date
#         ))

#     db.commit()



# from models import (
#     FactSubLedger,
#     FactSLAccountingWide,
#     DimProduct,
#     DimBSVTaxRate,
#     DimGeography,
#     DimDate,
#     DimCustomer
# )
# from datetime import datetime


# def generate_wide_accounting(db, company_id):

#     # =========================
#     # 1. PRELOAD DIMENSIONS 🚀
#     # =========================

#     product_map = {
#         p.id: {
#             "code": p.product_code,
#             "name": p.product_name
#         }
#         for p in db.query(DimProduct).filter_by(company_id=company_id)
#     }

#     customer_map = {
#         c.id: c.customer_name
#         for c in db.query(DimCustomer).filter_by(company_id=company_id)
#     }

#     bsv_map = {
#         b.geography_id: b.bsv_code
#         for b in db.query(DimBSVTaxRate).filter_by(company_id=company_id)
#     }

#     geo_map = {
#         g.id: {
#             "region": g.region,
#             "geo": g.geo,
#             "country": g.country
#         }
#         for g in db.query(DimGeography)
#     }

#     date_map = {
#         d.date: {
#             "year": d.year,
#             "month": d.month
#         }
#         for d in db.query(DimDate)
#     }

#     # =========================
#     # 2. RULE ENGINE 🔥
#     # =========================

#     rules = {
#         "total_revenue": [("30", "210")],

#         "raw_material": [
#             ("60", "110"),
#             ("61", "60")
#         ],

#         "direct_labor": [
#             ("240", "130"),
#             ("61", "240")
#         ],

#         "overhead": [
#             ("351", "110"),
#             ("61", "351"),
#             ("62", "61")
#         ],

#         "cogs": [
#             ("230", "62")
#         ],

#         "sga": [
#             ("240", "130")
#         ]
#     }

#     # =========================
#     # 3. FETCH SUBLEDGER
#     # =========================

#     subs = db.query(FactSubLedger).filter_by(company_id=company_id).all()

#     for sub in subs:

#         # =========================
#         # DIM LOOKUPS
#         # =========================

#         product = product_map.get(sub.product_id)
#         customer_name = customer_map.get(sub.customer_id)
#         geo = geo_map.get(sub.geography_id)
#         coa_bsv = bsv_map.get(sub.geography_id)
#         date_info = date_map.get(sub.date)

#         if not product or not geo or not coa_bsv:
#             continue

#         coa_product = product["code"]

#         def acc(key):
#             return f"{coa_bsv}-{coa_product}-{key}"

#         # =========================
#         # CREATE WIDE OBJECT
#         # =========================

#         wide = FactSLAccountingWide(
#             company_id=sub.company_id,

#             # Geography
#             region=geo["region"],
#             geo=geo["geo"],
#             country=geo["country"],

#             # Product / Customer
#             item_type=product["name"],
#             customer_name=customer_name,

#             # Order Info
#             order_id=sub.order_id,
#             order_date=sub.date,
#             year=date_info["year"] if date_info else None,
#             month=date_info["month"] if date_info else None,

#             # COA
#             coa_bsv=coa_bsv,
#             coa_product=coa_product,

#             # Cost Components (pass-through)
#             freight=sub.freight,
#             storage=sub.storage,
#             packaging=sub.packaging,
#             indirect_labor=sub.indirect_labor,
#             rent_utility=sub.rent_utility,

#             created_at=datetime.utcnow(),
#             updated_at=datetime.utcnow()
#         )

#         # =========================
#         # APPLY RULES
#         # =========================

#         for field, pairs in rules.items():

#             amount = getattr(sub, field, 0)
#             if not amount:
#                 continue

#             # -------------------------
#             # REVENUE (1 PAIR)
#             # -------------------------
#             if field == "total_revenue":
#                 dr, cr = pairs[0]

#                 wide.total_revenue = amount
#                 wide.revenue_dr_account = acc(dr)
#                 wide.revenue_dr_amount = amount
#                 wide.revenue_cr_account = acc(cr)
#                 wide.revenue_cr_amount = amount

#             # -------------------------
#             # RAW MATERIAL (2 PAIRS)
#             # -------------------------
#             elif field == "raw_material":
#                 wide.raw_material = amount

#                 for i, (dr, cr) in enumerate(pairs):
#                     setattr(wide, f"rm_dr_account_{i+1}", acc(dr))
#                     setattr(wide, f"rm_dr_amount_{i+1}", amount)
#                     setattr(wide, f"rm_cr_account_{i+1}", acc(cr))
#                     setattr(wide, f"rm_cr_amount_{i+1}", amount)

#             # -------------------------
#             # DIRECT LABOR (2 PAIRS)
#             # -------------------------
#             elif field == "direct_labor":
#                 wide.direct_labor = amount

#                 for i, (dr, cr) in enumerate(pairs):
#                     setattr(wide, f"dl_dr_account_{i+1}", acc(dr))
#                     setattr(wide, f"dl_dr_amount_{i+1}", amount)
#                     setattr(wide, f"dl_cr_account_{i+1}", acc(cr))
#                     setattr(wide, f"dl_cr_amount_{i+1}", amount)

#             # -------------------------
#             # OVERHEAD (SUM + 3 PAIRS)
#             # -------------------------
#             elif field == "overhead":

#                 overhead_amount = (
#                     (sub.freight or 0) +
#                     (sub.storage or 0) +
#                     (sub.packaging or 0) +
#                     (sub.indirect_labor or 0) +
#                     (sub.rent_utility or 0)
#                 )

#                 wide.overhead = overhead_amount

#                 for i, (dr, cr) in enumerate(pairs):
#                     setattr(wide, f"overhead_dr_account_{i+1}", acc(dr))
#                     setattr(wide, f"overhead_dr_amount_{i+1}", overhead_amount)
#                     setattr(wide, f"overhead_cr_account_{i+1}", acc(cr))
#                     setattr(wide, f"overhead_cr_amount_{i+1}", overhead_amount)

#             # -------------------------
#             # COGS (1 PAIR)
#             # -------------------------
#             elif field == "cogs":
#                 dr, cr = pairs[0]

#                 wide.cogs = amount
#                 wide.cogs_dr_account = acc(dr)
#                 wide.cogs_dr_amount = amount
#                 wide.cogs_cr_account = acc(cr)
#                 wide.cogs_cr_amount = amount

#             # -------------------------
#             # SG&A (1 PAIR)
#             # -------------------------
#             elif field == "sga":
#                 dr, cr = pairs[0]

#                 wide.sga = amount
#                 wide.sga_dr_account = acc(dr)
#                 wide.sga_dr_amount = amount
#                 wide.sga_cr_account = acc(cr)
#                 wide.sga_cr_amount = amount

#         # =========================
#         # DERIVED METRIC
#         # =========================
#         wide.gross_profit = (sub.total_revenue or 0) - (sub.cogs or 0)

#         db.add(wide)

#     db.commit()


from models import (
    FactSubLedger,
    FactSLAccountingWide,
    DimProduct,
    DimBSVTaxRate,
    DimGeography,
    DimDate,
    DimCustomer
)
from datetime import datetime


def generate_wide_accounting(db, company_id, batch_id):

    # =========================
    # 1. PRELOAD DIMENSIONS 🚀
    # =========================

    product_map = {
        p.id: {
            "code": p.product_code,
            "name": p.product_name
        }
        for p in db.query(DimProduct).filter_by(
            company_id=company_id,
            batch_id=batch_id
        )
    }

    customer_map = {
        c.id: c.customer_name
        for c in db.query(DimCustomer).filter_by(
            company_id=company_id,
            batch_id=batch_id
        )
    }

    bsv_map = {
        b.geography_id: b.bsv_code
        for b in db.query(DimBSVTaxRate).filter_by(
            company_id=company_id,
            batch_id=batch_id
        )
    }

    geo_map = {
        g.id: {
            "region": g.region,
            "geo": g.geo,
            "country": g.country
        }
        for g in db.query(DimGeography)
    }

    date_map = {
        d.date: {
            "year": d.year,
            "month": d.month
        }
        for d in db.query(DimDate)
    }

    # =========================
    # 2. RULE ENGINE 🔥
    # =========================

    rules = {
        "total_revenue": [("30", "210")],

        "raw_material": [
            ("60", "110"),
            ("61", "60")
        ],

        "direct_labor": [
            ("240", "130"),
            ("61", "240")
        ],

        "overhead": [
            ("351", "110"),
            ("61", "351"),
            ("62", "61")
        ],

        "cogs": [
            ("230", "62")
        ],

        "sga": [
            ("240", "130")
        ]
    }

    # =========================
    # 3. FETCH SUBLEDGER (ONLY CURRENT BATCH)
    # =========================

    subs = db.query(FactSubLedger).filter_by(
        company_id=company_id,
        batch_id=batch_id
    ).all()

    for sub in subs:

        # =========================
        # DIM LOOKUPS
        # =========================

        product = product_map.get(sub.product_id)
        customer_name = customer_map.get(sub.customer_id)
        geo = geo_map.get(sub.geography_id)
        coa_bsv = bsv_map.get(sub.geography_id)
        date_info = date_map.get(sub.date)

        if not product or not geo or not coa_bsv:
            continue

        coa_product = product["code"]

        def acc(key):
            return f"{coa_bsv}-{coa_product}-{key}"

        # =========================
        # CREATE WIDE OBJECT
        # =========================

        wide = FactSLAccountingWide(
            company_id=sub.company_id,

            # Geography
            region=geo["region"],
            geo=geo["geo"],
            country=geo["country"],

            # Product / Customer
            item_type=product["name"],
            customer_name=customer_name,

            # Order Info
            order_id=sub.order_id,
            order_date=sub.date,
            year=date_info["year"] if date_info else None,
            month=date_info["month"] if date_info else None,

            # COA
            coa_bsv=coa_bsv,
            coa_product=coa_product,

            # Cost Components
            freight=sub.freight,
            storage=sub.storage,
            packaging=sub.packaging,
            indirect_labor=sub.indirect_labor,
            rent_utility=sub.rent_utility,
            overhead=sub.overhead,

            # META
            batch_id=sub.batch_id,
            source_file_id=sub.source_file_id,

            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # =========================
        # APPLY RULES
        # =========================

        for field, pairs in rules.items():

            amount = getattr(sub, field, 0)
            if not amount:
                continue

            # REVENUE
            if field == "total_revenue":
                dr, cr = pairs[0]

                wide.total_revenue = amount
                wide.revenue_dr_account = acc(dr)
                wide.revenue_dr_amount = amount
                wide.revenue_cr_account = acc(cr)
                wide.revenue_cr_amount = amount

            # RAW MATERIAL
            elif field == "raw_material":
                wide.raw_material = amount

                for i, (dr, cr) in enumerate(pairs):
                    setattr(wide, f"rm_dr_account_{i+1}", acc(dr))
                    setattr(wide, f"rm_dr_amount_{i+1}", amount)
                    setattr(wide, f"rm_cr_account_{i+1}", acc(cr))
                    setattr(wide, f"rm_cr_amount_{i+1}", amount)

            # DIRECT LABOR
            elif field == "direct_labor":
                wide.direct_labor = amount

                for i, (dr, cr) in enumerate(pairs):
                    setattr(wide, f"dl_dr_account_{i+1}", acc(dr))
                    setattr(wide, f"dl_dr_amount_{i+1}", amount)
                    setattr(wide, f"dl_cr_account_{i+1}", acc(cr))
                    setattr(wide, f"dl_cr_amount_{i+1}", amount)

            # OVERHEAD
            elif field == "overhead":

                overhead_amount = (
                    (sub.freight or 0) +
                    (sub.storage or 0) +
                    (sub.packaging or 0) +
                    (sub.indirect_labor or 0) +
                    (sub.rent_utility or 0) +
                    (sub.overhead or 0)
                )

                # wide.overhead = overhead_amount

                for i, (dr, cr) in enumerate(pairs):
                    setattr(wide, f"overhead_dr_account_{i+1}", acc(dr))
                    setattr(wide, f"overhead_dr_amount_{i+1}", overhead_amount)
                    setattr(wide, f"overhead_cr_account_{i+1}", acc(cr))
                    setattr(wide, f"overhead_cr_amount_{i+1}", overhead_amount)

                wide.overhead_dr_amount_3=wide.rm_dr_amount_2+wide.dl_dr_amount_2+wide.overhead_dr_amount_2
                wide.overhead_cr_amount_3=wide.overhead_dr_amount_3

            # COGS
            elif field == "cogs":
                dr, cr = pairs[0]

                wide.cogs = amount
                wide.cogs_dr_account = acc(dr)
                wide.cogs_dr_amount = amount
                wide.cogs_cr_account = acc(cr)
                wide.cogs_cr_amount = amount

            # SG&A
            elif field == "sga":
                dr, cr = pairs[0]

                wide.sga = amount
                wide.sga_dr_account = acc(dr)
                wide.sga_dr_amount = amount
                wide.sga_cr_account = acc(cr)
                wide.sga_cr_amount = amount

        # =========================
        # DERIVED METRIC
        # =========================

        wide.gross_profit = (sub.total_revenue or 0) - (sub.cogs or 0)

        db.add(wide)

    db.commit()