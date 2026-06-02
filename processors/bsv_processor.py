# from models import DimBSVTaxRate, DimGeography
# from processors.utils import get_df


# def process_bsv(db, company_id, file, batch_id):
#     df = get_df(file.file_path)

#     for _, row in df.iterrows():

#         geo = db.query(DimGeography).filter_by(
#             country=row["Country"]
#         ).first()

#         if not geo:
#             geo = DimGeography(
#                 region="Unknown",
#                 geo="Unknown",
#                 country=row["Country"]
#             )
#             db.add(geo)
#             db.flush()

#         tax = str(row["Tax rate"]).replace("%", "")

#         bsv = DimBSVTaxRate(
#             company_id=company_id,
#             batch_id=batch_id,
#             geography_id=geo.id,
#             bsv_code=row["Value"],
#             tax_rate=float(tax) / 100
#         )
#         db.add(bsv)

#     db.commit()



from models import DimBSVTaxRate, DimGeography
from processors.utils import get_df


def process_bsv(db, company_id, file, batch_id):
    df = get_df(file.file_path)

    # Track duplicates within the same file
    seen = set()

    for _, row in df.iterrows():

        country = str(row["Country"]).strip()

        geo = (
            db.query(DimGeography)
            .filter_by(country=country)
            .first()
        )

        if not geo:
            geo = DimGeography(
                region="Unknown",
                geo="Unknown",
                country=country
            )
            db.add(geo)
            db.flush()  # get geo.id

        bsv_code = str(row["Value"]).strip()

        tax = str(row["Tax rate"]).replace("%", "").strip()

        unique_key = (
            company_id,
            geo.id,
            bsv_code,
            batch_id
        )

        # Skip duplicates within the uploaded file
        if unique_key in seen:
            continue

        seen.add(unique_key)

        # Skip duplicates already in DB
        existing = (
            db.query(DimBSVTaxRate)
            .filter_by(
                company_id=company_id,
                geography_id=geo.id,
                bsv_code=bsv_code,
                batch_id=batch_id
            )
            .first()
        )

        if existing:
            continue

        bsv = DimBSVTaxRate(
            company_id=company_id,
            batch_id=batch_id,
            geography_id=geo.id,
            bsv_code=bsv_code,
            tax_rate=float(tax) / 100
        )

        db.add(bsv)

    db.commit()