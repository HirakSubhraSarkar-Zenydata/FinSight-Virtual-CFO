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

from models import DimProduct
from processors.utils import get_df


def process_product(db, company_id, file, batch_id):
    df = get_df(file.file_path)

    for _, row in df.iterrows():
        product = DimProduct(
            id=row["Value"],
            company_id=company_id,
            batch_id=batch_id,
            product_code=row["Value"],
            product_name=row["Product name"]
        )
        db.add(product)

    db.commit()