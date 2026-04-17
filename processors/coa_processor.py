# from models import DimCOA
# from processors.utils import get_df


# def process_coa(db, company_id, file):
#     df = get_df(file.file_path)

#     for _, row in df.iterrows():
#         coa = DimCOA(
#             company_id=company_id,
#             account_key=row["Account_key"],
#             report=row.get("Report"),
#             class_name=row.get("Class"),
#             subclass=row.get("Subclass"),
#             subclass2=row.get("Subclass2"),
#             account=row.get("Account"),
#             subaccount=row.get("Subaccount"),
#         )
#         db.add(coa)

#     db.commit()


from models import DimCOA
from processors.utils import get_df


def process_coa(db, company_id, file, batch_id):
    df = get_df(file.file_path)

    for _, row in df.iterrows():
        coa = DimCOA(
            company_id=company_id,
            batch_id=batch_id,
            account_key=row["Account_key"],
            report=row.get("Report"),
            class_name=row.get("Class"),
            subclass=row.get("Subclass"),
            subclass2=row.get("Subclass2"),
            account=row.get("Account"),
            subaccount=row.get("Subaccount"),
        )
        db.add(coa)

    db.commit()