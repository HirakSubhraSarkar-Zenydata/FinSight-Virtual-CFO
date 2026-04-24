# import calendar
# from datetime import datetime
# from models import FactSubLedger, DimProduct, DimCustomer, DimGeography, DimDate
# from processors.utils import get_df, clean_money

# def process_subledger(db, company_id, file):
#     df = get_df(file.file_path)

#     # =========================
#     # PRELOAD (PERFORMANCE BOOST 🚀)
#     # =========================
#     product_map = {
#         (p.product_name.strip().lower(), p.company_id): p
#         for p in db.query(DimProduct).filter_by(company_id=company_id).all()
#     }

#     customer_map = {
#         (c.customer_name.strip().lower(), c.company_id): c
#         for c in db.query(DimCustomer).filter_by(company_id=company_id).all()
#     }

#     geo_map = {
#         g.country.strip().lower(): g
#         for g in db.query(DimGeography).all()
#     }

#     # Pre-fetch existing dates to avoid Duplicate Key errors
#     # We store them in a set for O(1) lookup speed
#     existing_dates = {d.date for d in db.query(DimDate.date).all()}

#     # =========================
#     # PROCESS ROWS
#     # =========================
#     for idx, row in df.iterrows():

#         # Normalize inputs
#         product_name = str(row["Item type"]).strip().lower()
#         customer_name = str(row["Customer"]).strip().lower()
#         country = str(row["Country"]).strip().lower()
#         region = str(row["Region"]).strip()
#         geo_val = str(row["Geo"]).strip()

#         # Parse Date (using %Y for 4-digit years)
#         order_date_dt = datetime.strptime(row["Order Date"], "%d-%m-%Y")
#         order_date = order_date_dt.date()

#         # =========================
#         # DIM_DATE (AUTO-CHECK / CREATE)
#         # =========================
#         if order_date not in existing_dates:
#             _, last_day = calendar.monthrange(order_date.year, order_date.month)
            
#             new_date = DimDate(
#                 date=order_date,
#                 year=order_date.year,
#                 month=order_date.month,
#                 day=order_date.day,
#                 quarter=(order_date.month - 1) // 3 + 1,
#                 is_month_end=(order_date.day == last_day),
#                 is_quarter_end=(order_date.day == last_day and order_date.month in [3, 6, 9, 12]),
#                 is_year_end=(order_date.month == 12 and order_date.day == 31),
#                 created_at=datetime.utcnow(),
#                 updated_at=datetime.utcnow()
#             )
#             db.add(new_date)
#             # Flush immediately so the Fact record can "see" this date in the DB
#             db.flush()
#             existing_dates.add(order_date)

#         # =========================
#         # PRODUCT
#         # =========================
#         product = product_map.get((product_name, company_id))
#         if not product:
#             print(f"❌ Product not found: {row['Item type']}")
#             continue 

#         # =========================
#         # CUSTOMER (AUTO CREATE)
#         # =========================
#         customer = customer_map.get((customer_name, company_id))
#         if not customer:
#             customer = DimCustomer(
#                 company_id=company_id,
#                 customer_name=row["Customer"]
#             )
#             db.add(customer)
#             db.flush()
#             customer_map[(customer_name, company_id)] = customer

#         # =========================
#         # GEOGRAPHY (ENRICH ONLY)
#         # =========================
#         geo = geo_map.get(country)
#         if not geo:
#             print(f"❌ Geography missing for country: {row['Country']}")
#             continue 

#         updated = False
#         if (not geo.region) or geo.region.lower() == "unknown":
#             geo.region = region
#             updated = True
#         if (not geo.geo) or geo.geo.lower() == "unknown":
#             geo.geo = geo_val
#             updated = True
#         if updated:
#             db.add(geo)

#         # =========================
#         # FACT INSERT
#         # =========================
#         fact = FactSubLedger(
#             company_id=company_id,
#             date=order_date, # References the DimDate we just checked/created

#             product_id=product.id,
#             customer_id=customer.id,
#             geography_id=geo.id,
            
#             # WARNING: Ensure coa_id is handled if it's NOT NULL in your DB
#             # If you have a default COA or logic to find it, add it here:
#             # coa_id = 1, 

#             order_id=row["Order Id"],

#             total_revenue=clean_money(row["Total Revenue"]),
#             raw_material=clean_money(row["Raw Material"]),
#             direct_labor=clean_money(row["Direct Labor"]),
#             freight=clean_money(row["Freight"]),
#             storage=clean_money(row["Storage"]),
#             packaging=clean_money(row["Packaging"]),
#             indirect_labor=clean_money(row["Indirect Labor"]),
#             rent_utility=clean_money(row["Rent & Utility"]),
#             overhead=clean_money(row["Overhead"]),
#             cogs=clean_money(row["COGS"]),
#             gross_profit=clean_money(row["Gross Profit"]),
#             sga=clean_money(row["SG&A"]),

#             source_file_id=file.id,
#             source_row_number=idx + 1
#         )

#         db.add(fact)

#     # Commit all changes at the end of the file
#     db.commit()


# import calendar
# from datetime import datetime
# from models import FactSubLedger, DimProduct, DimCustomer, DimGeography, DimDate
# from processors.utils import get_df, clean_money

# def process_subledger(db, company_id, file, batch_id):
#     df = get_df(file.file_path)

#     product_map = {
#         (p.product_name.strip().lower(), p.company_id): p
#         for p in db.query(DimProduct).filter_by(
#             company_id=company_id,
#             batch_id=batch_id
#         ).all()
#     }

#     customer_map = {
#         (c.customer_name.strip().lower(), c.company_id): c
#         for c in db.query(DimCustomer).filter_by(
#             company_id=company_id,
#             batch_id=batch_id
#         ).all()
#     }

#     geo_map = {
#         g.country.strip().lower(): g
#         for g in db.query(DimGeography).all()
#     }

#     existing_dates = {d.date for d in db.query(DimDate.date).all()}

#     for idx, row in df.iterrows():

#         product_name = str(row["Item type"]).strip().lower()
#         customer_name = str(row["Customer"]).strip().lower()
#         country = str(row["Country"]).strip().lower()
#         region = str(row["Region"]).strip()
#         geo_val = str(row["Geo"]).strip()

#         order_date_dt = datetime.strptime(row["Order Date"], "%d-%m-%Y")
#         order_date = order_date_dt.date()

#         if order_date not in existing_dates:
#             _, last_day = calendar.monthrange(order_date.year, order_date.month)

#             new_date = DimDate(
#                 date=order_date,
#                 year=order_date.year,
#                 month=order_date.month,
#                 day=order_date.day,
#                 quarter=(order_date.month - 1) // 3 + 1,
#                 is_month_end=(order_date.day == last_day),
#                 is_quarter_end=(order_date.day == last_day and order_date.month in [3, 6, 9, 12]),
#                 is_year_end=(order_date.month == 12 and order_date.day == 31),
#                 created_at=datetime.utcnow(),
#                 updated_at=datetime.utcnow()
#             )
#             db.add(new_date)
#             db.flush()
#             existing_dates.add(order_date)

#         product = product_map.get((product_name, company_id))
#         if not product:
#             continue

#         customer = customer_map.get((customer_name, company_id))
#         if not customer:
#             customer = DimCustomer(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 customer_name=row["Customer"]
#             )
#             db.add(customer)
#             db.flush()
#             customer_map[(customer_name, company_id)] = customer

#         geo = geo_map.get(country)
#         if not geo:
#             continue

#         if (not geo.region) or geo.region.lower() == "unknown":
#             geo.region = region
#         if (not geo.geo) or geo.geo.lower() == "unknown":
#             geo.geo = geo_val

#         fact = FactSubLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             date=order_date,
#             product_id=product.id,
#             customer_id=customer.id,
#             geography_id=geo.id,
#             order_id=row["Order Id"],

#             total_revenue=clean_money(row["Total Revenue"]),
#             raw_material=clean_money(row["Raw Material"]),
#             direct_labor=clean_money(row["Direct Labor"]),
#             freight=clean_money(row["Freight"]),
#             storage=clean_money(row["Storage"]),
#             packaging=clean_money(row["Packaging"]),
#             indirect_labor=clean_money(row["Indirect Labor"]),
#             rent_utility=clean_money(row["Rent & Utility"]),
#             overhead=clean_money(row["Overhead"]),
#             cogs=clean_money(row["COGS"]),
#             gross_profit=clean_money(row["Gross Profit"]),
#             sga=clean_money(row["SG&A"]),

#             source_file_id=file.id,
#             source_row_number=idx + 1
#         )

#         db.add(fact)

#     db.commit()



import calendar
from datetime import datetime
import pandas as pd
from models import FactSubLedger, DimProduct, DimCustomer, DimGeography, DimDate
from processors.utils import get_df, clean_money

def process_subledger(db, company_id, file, batch_id):
    df = get_df(file.file_path)

    product_map = {
        (p.product_name.strip().lower(), p.company_id): p
        for p in db.query(DimProduct).filter_by(
            company_id=company_id,
            batch_id=batch_id
        ).all()
    }

    customer_map = {
        (c.customer_name.strip().lower(), c.company_id): c
        for c in db.query(DimCustomer).filter_by(
            company_id=company_id,
            batch_id=batch_id
        ).all()
    }

    geo_map = {
        g.country.strip().lower(): g
        for g in db.query(DimGeography).all()
    }

    existing_dates = {d.date for d in db.query(DimDate.date).all()}

    for idx, row in df.iterrows():

        product_name = str(row["Item type"]).strip().lower()
        customer_name = str(row["Customer"]).strip().lower()
        country = str(row["Country"]).strip().lower()
        region = str(row["Region"]).strip()
        geo_val = str(row["Geo"]).strip()

        # ✅ HANDLE ANY DATE FORMAT + STORE STANDARD DATE
        order_date_dt = pd.to_datetime(row["Order Date"], errors="coerce", dayfirst=True)
        if pd.isna(order_date_dt):
            continue

        order_date = order_date_dt.date()  # always clean YYYY-MM-DD internally

        if order_date not in existing_dates:
            _, last_day = calendar.monthrange(order_date.year, order_date.month)

            new_date = DimDate(
                date=order_date,
                year=order_date.year,
                month=order_date.month,
                day=order_date.day,
                quarter=(order_date.month - 1) // 3 + 1,
                is_month_end=(order_date.day == last_day),
                is_quarter_end=(order_date.day == last_day and order_date.month in [3, 6, 9, 12]),
                is_year_end=(order_date.month == 12 and order_date.day == 31),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_date)
            db.flush()
            existing_dates.add(order_date)

        product = product_map.get((product_name, company_id))
        if not product:
            continue

        customer = customer_map.get((customer_name, company_id))
        if not customer:
            customer = DimCustomer(
                company_id=company_id,
                batch_id=batch_id,
                customer_name=row["Customer"]
            )
            db.add(customer)
            db.flush()
            customer_map[(customer_name, company_id)] = customer

        geo = geo_map.get(country)
        if not geo:
            continue

        if (not geo.region) or geo.region.lower() == "unknown":
            geo.region = region
        if (not geo.geo) or geo.geo.lower() == "unknown":
            geo.geo = geo_val

        fact = FactSubLedger(
            company_id=company_id,
            batch_id=batch_id,
            date=order_date,  # ✅ stored cleanly (DB DATE type)
            product_id=product.id,
            customer_id=customer.id,
            geography_id=geo.id,
            order_id=row["Order Id"],

            total_revenue=clean_money(row["Total Revenue"]),
            raw_material=clean_money(row["Raw Material"]),
            direct_labor=clean_money(row["Direct Labor"]),
            freight=clean_money(row["Freight"]),
            storage=clean_money(row["Storage"]),
            packaging=clean_money(row["Packaging"]),
            indirect_labor=clean_money(row["Indirect Labor"]),
            rent_utility=clean_money(row["Rent & Utility"]),
            overhead=clean_money(row["Overhead"]),
            cogs=clean_money(row["COGS"]),
            gross_profit=clean_money(row["Gross Profit"]),
            sga=clean_money(row["SG&A"]),

            source_file_id=file.id,
            source_row_number=idx + 1
        )

        db.add(fact)

    db.commit()