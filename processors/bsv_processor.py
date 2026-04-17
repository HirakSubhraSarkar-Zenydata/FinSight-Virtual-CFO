# from models import DimBSVTaxRate, DimGeography
# from processors.utils import get_df


# def process_bsv(db, company_id, file):
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

    for _, row in df.iterrows():

        geo = db.query(DimGeography).filter_by(
            country=row["Country"]
        ).first()

        if not geo:
            geo = DimGeography(
                region="Unknown",
                geo="Unknown",
                country=row["Country"]
            )
            db.add(geo)
            db.flush()

        tax = str(row["Tax rate"]).replace("%", "")

        bsv = DimBSVTaxRate(
            company_id=company_id,
            batch_id=batch_id,
            geography_id=geo.id,
            bsv_code=row["Value"],
            tax_rate=float(tax) / 100
        )
        db.add(bsv)

    db.commit()