# from models import DimProduct
# from processors.utils import get_df


# def process_product(db, company_id, file):
#     df = get_df(file.file_path)

#     for _, row in df.iterrows():
#         product = DimProduct(
#             id=row["Value"],
#             company_id=company_id,
#             product_code=row["Value"],
#             product_name=row["Product name"]
#         )
#         db.add(product)

#     db.commit()

# from models import DimProduct
# from processors.utils import get_df


# def process_product(db, company_id, file, batch_id):
#     df = get_df(file.file_path)

#     for _, row in df.iterrows():
#         product = DimProduct(
#             id=row["Value"],
#             company_id=company_id,
#             batch_id=batch_id,
#             product_code=row["Value"],
#             product_name=row["Product name"]
#         )
#         db.add(product)

#     db.commit()



from models import DimProduct
from processors.utils import get_df


def process_product(db, company_id, file, batch_id):
    df = get_df(file.file_path)

    # Get existing product ids for this company and batch
    existing_ids = {
        row[0]
        for row in db.query(DimProduct.id)
        .filter(
            DimProduct.company_id == company_id,
            DimProduct.batch_id == batch_id
        )
        .all()
    }

    for _, row in df.iterrows():
        product_id = row["Value"]

        # Skip if already exists
        if product_id in existing_ids:
            continue

        product = DimProduct(
            id=product_id,
            company_id=company_id,
            batch_id=batch_id,
            product_code=product_id,
            product_name=row["Product name"]
        )

        db.add(product)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise