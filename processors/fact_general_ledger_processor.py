# from sqlalchemy.orm import Session
# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )
# from datetime import date


# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # NATURAL ACCOUNT
# # ============================================
# def extract_natural_account(account: str):
#     return account.split("-")[-1] if account else None


# # ============================================
# # MAIN PROCESSOR
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     gl_rows = []

#     # ============================================
#     # 🔥 COA CACHE
#     # ============================================
#     coa_map = {
#         str(c.account_key): c
#         for c in db.query(DimCOA)
#         .filter(
#             DimCOA.company_id == company_id,
#             DimCOA.batch_id == batch_id,
#             DimCOA.is_deleted == False
#         ).all()
#     }

#     # ============================================
#     # 🔥 DEFAULT ENTRIES
#     # ============================================
#     gl_rows.append(FactGeneralLedger(
#         order_date=date(2021, 1, 1),
#         month=1,
#         account="2040-0000-10",
#         dr_amount=1480950.18,
#         cr_amount=0,
#         natural_account="10",
#         account_subclass="Assets",
#         account_type="Assets",
#         sub_account="Cash at bank",
#         is_closing_entry=False
#     ))

#     gl_rows.append(FactGeneralLedger(
#         order_date=date(2021, 1, 1),
#         month=1,
#         account="2040-0000-180",
#         dr_amount=0,
#         cr_amount=1480950.18,
#         natural_account="180",
#         account_subclass="Owners equity",
#         account_type="Equity",
#         sub_account="Share capital",
#         is_closing_entry=False
#     ))

#     # ============================================
#     # 🔥 SL DATA
#     # ============================================
#     sl_data = db.query(FactSLAccountingWide).filter(
#         FactSLAccountingWide.company_id == company_id,
#         FactSLAccountingWide.batch_id == batch_id
#     ).yield_per(1000)

#     fields = [
#         ("revenue_dr_account", "revenue_dr_amount", "DR"),
#         ("revenue_cr_account", "revenue_cr_amount", "CR"),
#         ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#         ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#         ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#         ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#         ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#         ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#         ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#         ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#         ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#         ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#         ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#         ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#         ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#         ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#         ("cogs_dr_account", "cogs_dr_amount", "DR"),
#         ("cogs_cr_account", "cogs_cr_amount", "CR"),
#         ("sga_dr_account", "sga_dr_amount", "DR"),
#         ("sga_cr_account", "sga_cr_amount", "CR"),
#     ]

#     for row in sl_data:
#         for acc_field, amt_field, entry_type in fields:

#             account = getattr(row, acc_field)
#             amount = getattr(row, amt_field)

#             if not account or not amount:
#                 continue

#             natural_account = extract_natural_account(account)
#             coa = coa_map.get(natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 sl_accounting_id=row.id,
#                 order_id=row.order_id,
#                 order_date=row.order_date,
#                 month=row.month,
#                 account=account,
#                 dr_amount=amount if entry_type == "DR" else 0,
#                 cr_amount=amount if entry_type == "CR" else 0,
#                 natural_account=natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#     # ============================================
#     # 🔥 ASSET JOURNAL
#     # ============================================
#     asset_data = db.query(FactAssetJournal).filter(
#         FactAssetJournal.company_id == company_id,
#         FactAssetJournal.batch_id == batch_id
#     ).yield_per(1000)

#     for row in asset_data:

#         natural_account = str(row.natural_account)
#         coa = coa_map.get(natural_account)

#         gl_rows.append(FactGeneralLedger(
#             asset_journal_id=row.id,
#             asset_id=row.asset_id,
#             order_date=None,
#             month=row.month,
#             account=row.account_code,
#             dr_amount=row.dr_amount or 0,
#             cr_amount=row.cr_amount or 0,
#             natural_account=natural_account,
#             account_subclass=coa.subclass if coa else None,
#             account_type=get_account_type(coa.subclass if coa else None),
#             sub_account=coa.subaccount if coa else None,
#             is_closing_entry=False,
#             coa_id=coa.id if coa else None
#         ))

#     # ============================================
#     # 🔥 TAX
#     # ============================================
#     tax_data = db.query(FactTax).filter(
#         FactTax.company_id == company_id,
#         FactTax.batch_id == batch_id
#     ).yield_per(1000)

#     for row in tax_data:

#         if row.dr_account and row.dr_amount:
#             natural_account = extract_natural_account(row.dr_account)
#             coa = coa_map.get(natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 fact_tax_id=row.id,
#                 month=row.month,
#                 account=row.dr_account,
#                 dr_amount=row.dr_amount,
#                 cr_amount=0,
#                 natural_account=natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         if row.cr_account and row.cr_amount:
#             natural_account = extract_natural_account(row.cr_account)
#             coa = coa_map.get(natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 fact_tax_id=row.id,
#                 month=row.month,
#                 account=row.cr_account,
#                 dr_amount=0,
#                 cr_amount=row.cr_amount,
#                 natural_account=natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#     # ============================================
#     # 🔥 BULK INSERT
#     # ============================================
#     if gl_rows:
#         db.bulk_save_objects(gl_rows)
#         db.commit()

#     return {
#         "status": "success",
#         "rows_inserted": len(gl_rows)
#     }

# ---------------------------------------------------------------------------------------------
# good 

# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )


# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # NATURAL ACCOUNT
# # ============================================
# def extract_natural_account(account: str):
#     return account.split("-")[-1] if account else None


# # ============================================
# # MAIN PROCESSOR
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     gl_rows = []

#     try:
#         # ============================================
#         # 🔥 COA CACHE
#         # ============================================
#         coa_map = {
#             str(c.account_key): c
#             for c in db.query(DimCOA)
#             .filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         # ============================================
#         # 🔥 DEFAULT ENTRIES
#         # ============================================
#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 1, 1),
#             month=1,
#             account="2040-0000-10",
#             dr_amount=1480950.18,
#             cr_amount=0,
#             natural_account="10",
#             account_subclass="Assets",
#             account_type="Assets",
#             sub_account="Cash at bank",
#             is_closing_entry=False
#         ))

#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 1, 1),
#             month=1,
#             account="2040-0000-180",
#             dr_amount=0,
#             cr_amount=1480950.18,
#             natural_account="180",
#             account_subclass="Owners equity",
#             account_type="Equity",
#             sub_account="Share capital",
#             is_closing_entry=False
#         ))

#         # ============================================
#         # 🔥 SL DATA
#         # ============================================
#         sl_data = db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(1000)

#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in sl_data:
#             for acc_field, amt_field, entry_type in fields:

#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural_account = extract_natural_account(account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date,
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # 🔥 ASSET JOURNAL
#         # ============================================
#         asset_data = db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(1000)

#         for row in asset_data:

#             natural_account = str(row.natural_account)
#             coa = coa_map.get(natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # 🔥 TAX
#         # ============================================
#         tax_data = db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(1000)

#         for row in tax_data:

#             if row.dr_account and row.dr_amount:
#                 natural_account = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural_account = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # 🔥 BULK INSERT (NON-CLOSING FIRST)
#         # ============================================
#         if gl_rows:
#             db.bulk_save_objects(gl_rows)
#             db.commit()

#         # ============================================
#         # 🔥 CLOSING ENTRIES (AFTER INSERT)
#         # ============================================
#         closing_rows = []

#         summary = db.query(
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(FactGeneralLedger.account).all()

#         total_income = 0
#         total_expense = 0

#         for row in summary:
#             natural_account = extract_natural_account(row.account)
#             coa = coa_map.get(natural_account)

#             if not coa:
#                 continue

#             acc_type = get_account_type(coa.subclass)
#             balance = (row.cr or 0) - (row.dr or 0)

#             if acc_type == "Income" and balance != 0:
#                 total_income += balance

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=balance,
#                     cr_amount=0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#             elif acc_type == "Expense" and balance != 0:
#                 total_expense += abs(balance)

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=0,
#                     cr_amount=abs(balance),
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#         income_summary_account = "2040-0000-202"
#         retained_earnings_account = "2040-0000-200"

#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 12, 31),
#             month=12,
#             account=income_summary_account,
#             dr_amount=0,
#             cr_amount=total_income,
#             natural_account="202",
#             account_subclass="Owners equity",
#             account_type="Equity",
#             sub_account="Income summary",
#             is_closing_entry=True
#         ))

#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 12, 31),
#             month=12,
#             account=income_summary_account,
#             dr_amount=total_expense,
#             cr_amount=0,
#             natural_account="202",
#             account_subclass="Owners equity",
#             account_type="Equity",
#             sub_account="Income summary",
#             is_closing_entry=True
#         ))

#         profit = total_income - total_expense

#         if profit > 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 12, 31),
#                 month=12,
#                 account=retained_earnings_account,
#                 dr_amount=0,
#                 cr_amount=profit,
#                 natural_account="200",
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Retained earnings",
#                 is_closing_entry=True
#             ))

#         if closing_rows:
#             db.bulk_save_objects(closing_rows)
#             db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e


# --------------------------------------------------------------------------------------------

# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )


# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # NATURAL ACCOUNT
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# # ============================================
# # MAIN PROCESSOR
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         gl_rows = []

#         # ============================================
#         # 🔥 COA CACHE (INT KEY)
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         # ============================================
#         # 🔥 DYNAMIC CLOSING ACCOUNTS
#         # ============================================
#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("COA missing: 202 (Income Summary) or 200 (Retained Earnings)")

#         # ============================================
#         # 🔥 DEFAULT ENTRIES
#         # ============================================
#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 1, 1),
#             month=1,
#             account="2040-0000-10",
#             dr_amount=1480950.18,
#             cr_amount=0,
#             natural_account=10,
#             account_subclass="Assets",
#             account_type="Assets",
#             sub_account="Cash at bank",
#             is_closing_entry=False
#         ))

#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 1, 1),
#             month=1,
#             account="2040-0000-180",
#             dr_amount=0,
#             cr_amount=1480950.18,
#             natural_account=180,
#             account_subclass="Owners equity",
#             account_type="Equity",
#             sub_account="Share capital",
#             is_closing_entry=False
#         ))

#         # ============================================
#         # 🔥 SL DATA
#         # ============================================
#         sl_data = db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(1000)

#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in sl_data:
#             for acc_field, amt_field, entry_type in fields:

#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural_account = extract_natural_account(account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date,
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # 🔥 INSERT NON-CLOSING
#         # ============================================
#         if gl_rows:
#             db.bulk_save_objects(gl_rows)
#             db.commit()

#         # ============================================
#         # 🔥 CLOSING ENTRIES
#         # ============================================
#         closing_rows = []

#         summary = db.query(
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(FactGeneralLedger.account).all()

#         total_income = 0
#         total_expense = 0

#         for row in summary:
#             natural_account = extract_natural_account(row.account)
#             coa = coa_map.get(natural_account)

#             if not coa:
#                 continue

#             acc_type = get_account_type(coa.subclass)
#             balance = (row.cr or 0) - (row.dr or 0)

#             # CLOSE INCOME
#             if acc_type == "Income":
#                 total_income += balance

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=balance,
#                     cr_amount=0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#             # CLOSE EXPENSE
#             elif acc_type == "Expense":
#                 total_expense += abs(balance)

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=0,
#                     cr_amount=abs(balance),
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#         # ============================================
#         # 🔥 INCOME SUMMARY (DYNAMIC)
#         # ============================================

#         # Income → Summary
#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 12, 31),
#             month=12,
#             account=income_summary_coa.account_code,
#             dr_amount=0,
#             cr_amount=total_income,
#             natural_account=income_summary_coa.account_key,
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         # Expense → Summary
#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 12, 31),
#             month=12,
#             account=income_summary_coa.account_code,
#             dr_amount=total_expense,
#             cr_amount=0,
#             natural_account=income_summary_coa.account_key,
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         # ============================================
#         # 🔥 MISSING ENTRY (ROW 443)
#         # ============================================
#         profit = total_income - total_expense

#         if profit != 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 12, 31),
#                 month=12,
#                 account=income_summary_coa.account_code,
#                 dr_amount=profit if profit > 0 else 0,
#                 cr_amount=abs(profit) if profit < 0 else 0,
#                 natural_account=income_summary_coa.account_key,
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#         # ============================================
#         # 🔥 RETAINED EARNINGS
#         # ============================================
#         if profit > 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 12, 31),
#                 month=12,
#                 account=retained_earnings_coa.account_code,
#                 dr_amount=0,
#                 cr_amount=profit,
#                 natural_account=retained_earnings_coa.account_key,
#                 account_subclass=retained_earnings_coa.subclass,
#                 account_type=get_account_type(retained_earnings_coa.subclass),
#                 sub_account=retained_earnings_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=retained_earnings_coa.id
#             ))

#         if closing_rows:
#             db.bulk_save_objects(closing_rows)
#             db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e

# ---------------------------------------------------------------------------------------------
# ALL DYNAMIC, WITH CLOSING ENTRIES CREATED AFTER INITIAL INSERT

# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )


# # ============================================
# # HELPERS
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # 🔥 CLEAN OLD DATA
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         # ============================================
#         # 🔥 COA CACHE
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 or 200")

#         # ============================================
#         # 🔥 GET YEARS
#         # ============================================
#         years = db.query(
#             func.extract('year', FactSLAccountingWide.order_date)
#         ).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).distinct().all()

#         years = sorted([int(y[0]) for y in years if y[0]])

#         gl_rows = []

#         # ============================================
#         # 🔥 OPENING ENTRY (FIRST YEAR)
#         # ============================================
#         first_year = years[0]

#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(first_year, 1, 1),
#             month=1,
#             account="2040-0000-10",
#             dr_amount=1480950.18,
#             cr_amount=0,
#             natural_account=10,
#             account_subclass="Assets",
#             account_type="Assets",
#             sub_account="Cash at bank",
#             is_closing_entry=False
#         ))

#         gl_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(first_year, 1, 1),
#             month=1,
#             account="2040-0000-180",
#             dr_amount=0,
#             cr_amount=1480950.18,
#             natural_account=180,
#             account_subclass="Owners equity",
#             account_type="Equity",
#             sub_account="Share capital",
#             is_closing_entry=False
#         ))

#         # ============================================
#         # 🔥 SL DATA
#         # ============================================
#         sl_data = db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(1000)

#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in sl_data:
#             for acc_field, amt_field, entry_type in fields:

#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural_account = extract_natural_account(account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date,
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # 🔥 ASSET JOURNAL
#         # ============================================
#         asset_data = db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(1000)

#         for row in asset_data:
#             natural_account = int(row.natural_account)
#             coa = coa_map.get(natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=None,
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # 🔥 TAX
#         # ============================================
#         tax_data = db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(1000)

#         for row in tax_data:

#             if row.dr_account and row.dr_amount:
#                 natural_account = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural_account = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural_account)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=natural_account,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # 🔥 INSERT NON-CLOSING
#         # ============================================
#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # 🔥 CLOSING (SAME AS BEFORE - CORRECT)
#         # ============================================
#         # (keeping your correct logic unchanged)

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e


# -----------------------------------------------------------------------------------

# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )


# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # HELPERS
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # DELETE OLD
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         gl_rows = []

#         # ============================================
#         # COA CACHE
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 / 200")

#         # ============================================
#         # DEFAULT ENTRY
#         # ============================================
#         gl_rows.extend([
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 1, 1),
#                 month=1,
#                 account="2040-0000-10",
#                 dr_amount=1480950.18,
#                 cr_amount=0,
#                 natural_account=10,
#                 account_subclass="Assets",
#                 account_type="Assets",
#                 sub_account="Cash at bank",
#                 is_closing_entry=False
#             ),
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 1, 1),
#                 month=1,
#                 account="2040-0000-180",
#                 dr_amount=0,
#                 cr_amount=1480950.18,
#                 natural_account=180,
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Share capital",
#                 is_closing_entry=False
#             )
#         ])

#         # ============================================
#         # SL DATA
#         # ============================================
#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(2000):

#             for acc_field, amt_field, entry_type in fields:
#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural = extract_natural_account(account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date,
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # ASSET JOURNAL
#         # ============================================
#         for row in db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(2000):

#             coa = coa_map.get(row.natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=date(row.year, row.month, 1),
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=row.natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # TAX
#         # ============================================
#         for row in db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(2000):

#             if row.dr_account and row.dr_amount:
#                 natural = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # INSERT NON-CLOSING
#         # ============================================
#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # CLOSING ENTRIES
#         # ============================================
#         closing_rows = []

#         summary = db.query(
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(FactGeneralLedger.account).all()

#         total_income = 0
#         total_expense = 0

#         for row in summary:
#             natural = extract_natural_account(row.account)
#             coa = coa_map.get(natural)

#             if not coa:
#                 continue

#             balance = (row.cr or 0) - (row.dr or 0)
#             acc_type = get_account_type(coa.subclass)

#             if acc_type == "Income" and balance != 0:
#                 total_income += balance

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=balance,
#                     cr_amount=0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#             elif acc_type == "Expense" and balance != 0:
#                 total_expense += abs(balance)

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=date(2021, 12, 31),
#                     month=12,
#                     account=row.account,
#                     dr_amount=0,
#                     cr_amount=abs(balance),
#                     natural_account=natural,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#         profit = total_income - total_expense

#         # Income Summary
#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=date(2021, 12, 31),
#             month=12,
#             account=build_account_code(income_summary_coa.account_key),
#             dr_amount=total_expense,
#             cr_amount=total_income,
#             natural_account=income_summary_coa.account_key,
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         # Retained Earnings
#         if profit != 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 12, 31),
#                 month=12,
#                 account=build_account_code(retained_earnings_coa.account_key),
#                 dr_amount=0 if profit > 0 else abs(profit),
#                 cr_amount=profit if profit > 0 else 0,
#                 natural_account=retained_earnings_coa.account_key,
#                 account_subclass=retained_earnings_coa.subclass,
#                 account_type=get_account_type(retained_earnings_coa.subclass),
#                 sub_account=retained_earnings_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=retained_earnings_coa.id
#             ))

#         db.bulk_save_objects(closing_rows)
#         db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e



# ----------------------------------------------
# WORKING PERFECTLY WITH ALL DYNAMIC, BUT NO CLOSING ENTRIES DYNAMIC (TO BE RUN AFTER)
# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )

# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # HELPERS
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # DELETE OLD DATA
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         # ============================================
#         # COA CACHE
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 / 200")

#         gl_rows = []

#         # ============================================
#         # DEFAULT ENTRY
#         # ============================================
#         gl_rows.extend([
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 1, 1),
#                 month=1,
#                 account="2040-0000-10",
#                 dr_amount=1480950.18,
#                 cr_amount=0,
#                 natural_account=10,
#                 account_subclass="Assets",
#                 account_type="Assets",
#                 sub_account="Cash at bank",
#                 is_closing_entry=False
#             ),
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(2021, 1, 1),
#                 month=1,
#                 account="2040-0000-180",
#                 dr_amount=0,
#                 cr_amount=1480950.18,
#                 natural_account=180,
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Share capital",
#                 is_closing_entry=False
#             )
#         ])

#         # ============================================
#         # SL DATA
#         # ============================================
#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(2000):

#             for acc_field, amt_field, entry_type in fields:

#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural = extract_natural_account(account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date,
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # ASSET JOURNAL
#         # ============================================
#         for row in db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(2000):

#             coa = coa_map.get(row.natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=date(row.year, row.month, 1),
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=row.natural_account,
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # TAX
#         # ============================================
#         for row in db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(2000):

#             if row.dr_account and row.dr_amount:
#                 natural = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=natural,
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # INSERT NON-CLOSING
#         # ============================================
#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # CLOSING ENTRIES
#         # ============================================
#         closing_rows = []
#         closing_date = date(2021, 12, 31)

#         summary = db.query(
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(FactGeneralLedger.account).all()

#         total_income = 0
#         total_expense = 0

#         for row in summary:
#             natural = extract_natural_account(row.account)
#             coa = coa_map.get(natural)

#             if not coa:
#                 continue

#             balance = (row.cr or 0) - (row.dr or 0)
#             acc_type = get_account_type(coa.subclass)

#             if acc_type == "Income" and balance != 0:
#                 total_income += balance

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=row.account,
#                     dr_amount=balance,
#                     cr_amount=0,
#                     natural_account=natural,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#             elif acc_type == "Expense" and balance != 0:
#                 total_expense += abs(balance)

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=row.account,
#                     dr_amount=0,
#                     cr_amount=abs(balance),
#                     natural_account=natural,
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#         # Income Summary entries
#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=closing_date,
#             month=12,
#             account=build_account_code(income_summary_coa.account_key),
#             dr_amount=0,
#             cr_amount=total_income,
#             natural_account=income_summary_coa.account_key,
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=closing_date,
#             month=12,
#             account=build_account_code(income_summary_coa.account_key),
#             dr_amount=total_expense,
#             cr_amount=0,
#             natural_account=income_summary_coa.account_key,
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         # FINAL PROFIT TRANSFER (FIXED)
#         profit = total_income - total_expense

#         if profit != 0:
#             # 🔥 ROW 443
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=profit if profit > 0 else 0,
#                 cr_amount=abs(profit) if profit < 0 else 0,
#                 natural_account=income_summary_coa.account_key,
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#             # 🔥 ROW 444
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(retained_earnings_coa.account_key),
#                 dr_amount=abs(profit) if profit < 0 else 0,
#                 cr_amount=profit if profit > 0 else 0,
#                 natural_account=retained_earnings_coa.account_key,
#                 account_subclass=retained_earnings_coa.subclass,
#                 account_type=get_account_type(retained_earnings_coa.subclass),
#                 sub_account=retained_earnings_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=retained_earnings_coa.id
#             ))

#         db.bulk_save_objects(closing_rows)
#         db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e


# -----------------------------------------------------------------------------------
# GOOD WORKING VERSION WITH ALL DYNAMIC, BUT CLOSING ENTRIES ARE HARDCODED (TO BE RUN AFTER)
# --------------------------------------------------------------------------------------------
# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date, datetime

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )

# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # HELPERS
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # DELETE OLD DATA
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         gl_rows = []

#         # ============================================
#         # COA CACHE (FAST LOOKUP)
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 / 200")

#         # ============================================
#         # DEFAULT ENTRY (DYNAMIC YEAR)
#         # ============================================
#         current_year = datetime.utcnow().year

#         gl_rows.extend([
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-10",
#                 dr_amount=1480950.18,
#                 cr_amount=0,
#                 natural_account="10",
#                 account_subclass="Assets",
#                 account_type="Assets",
#                 sub_account="Cash at bank",
#                 is_closing_entry=False
#             ),
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-180",
#                 dr_amount=0,
#                 cr_amount=1480950.18,
#                 natural_account="180",
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Share capital",
#                 is_closing_entry=False
#             )
#         ])

#         # ============================================
#         # SL DATA
#         # ============================================
#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(2000):

#             for acc_field, amt_field, entry_type in fields:
#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural = extract_natural_account(account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date if row.order_date else date(row.year, row.month, 1),
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # ASSET JOURNAL
#         # ============================================
#         for row in db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(2000):

#             coa = coa_map.get(row.natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=date(row.year, row.month, 1),
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=str(row.natural_account),
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # TAX
#         # ============================================
#         for row in db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(2000):

#             if row.dr_account and row.dr_amount:
#                 natural = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # INSERT NON-CLOSING
#         # ============================================
#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # FAST CLOSING (FIXED + COMPLETE)
#         # ============================================
#         closing_rows = []

#         summary = db.query(
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(FactGeneralLedger.account).all()

#         max_year = db.query(
#             func.max(func.extract('year', FactGeneralLedger.order_date))
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).scalar() or current_year

#         closing_date = date(int(max_year), 12, 31)

#         total_income = 0
#         total_expense = 0

#         for row in summary:
#             natural = extract_natural_account(row.account)
#             coa = coa_map.get(natural)

#             if not coa:
#                 continue

#             balance = (row.cr or 0) - (row.dr or 0)
#             acc_type = get_account_type(coa.subclass)

#             if acc_type == "Income" and balance != 0:
#                 total_income += balance

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=row.account,
#                     dr_amount=balance,
#                     cr_amount=0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#             elif acc_type == "Expense" and balance != 0:
#                 total_expense += abs(balance)

#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=row.account,
#                     dr_amount=0,
#                     cr_amount=abs(balance),
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass,
#                     account_type=acc_type,
#                     sub_account=coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=coa.id
#                 ))

#         profit = total_income - total_expense

#         # ✅ INCOME SUMMARY (2 ROWS — FIXED)
#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=closing_date,
#             month=12,
#             account=build_account_code(income_summary_coa.account_key),
#             dr_amount=0,
#             cr_amount=total_income,
#             natural_account=str(income_summary_coa.account_key),
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         closing_rows.append(FactGeneralLedger(
#             company_id=company_id,
#             batch_id=batch_id,
#             order_date=closing_date,
#             month=12,
#             account=build_account_code(income_summary_coa.account_key),
#             dr_amount=total_expense,
#             cr_amount=0,
#             natural_account=str(income_summary_coa.account_key),
#             account_subclass=income_summary_coa.subclass,
#             account_type=get_account_type(income_summary_coa.subclass),
#             sub_account=income_summary_coa.subaccount,
#             is_closing_entry=True,
#             coa_id=income_summary_coa.id
#         ))

#         # ✅ PROFIT TRANSFER (MISSING ROW FIXED)
#         if profit != 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=profit if profit > 0 else 0,
#                 cr_amount=abs(profit) if profit < 0 else 0,
#                 natural_account=str(income_summary_coa.account_key),
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#         # ✅ RETAINED EARNINGS
#         if profit != 0:
#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(retained_earnings_coa.account_key),
#                 dr_amount=0 if profit > 0 else abs(profit),
#                 cr_amount=profit if profit > 0 else 0,
#                 natural_account=str(retained_earnings_coa.account_key),
#                 account_subclass=retained_earnings_coa.subclass,
#                 account_type=get_account_type(retained_earnings_coa.subclass),
#                 sub_account=retained_earnings_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=retained_earnings_coa.id
#             ))

#         db.bulk_save_objects(closing_rows)
#         db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e



# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date, datetime

# from models import (
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactTax,
#     DimCOA
# )

# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # HELPERS
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # DELETE OLD DATA
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         gl_rows = []

#         # ============================================
#         # COA CACHE (FAST LOOKUP)
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 / 200")

#         # ============================================
#         # DEFAULT ENTRY (DYNAMIC YEAR)
#         # ============================================
#         current_year = datetime.utcnow().year

#         gl_rows.extend([
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-10",
#                 dr_amount=1480950.18,
#                 cr_amount=0,
#                 natural_account="10",
#                 account_subclass="Assets",
#                 account_type="Assets",
#                 sub_account="Cash at bank",
#                 is_closing_entry=False
#             ),
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-180",
#                 dr_amount=0,
#                 cr_amount=1480950.18,
#                 natural_account="180",
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Share capital",
#                 is_closing_entry=False
#             )
#         ])

#         # ============================================
#         # SL DATA
#         # ============================================
#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(2000):

#             for acc_field, amt_field, entry_type in fields:
#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or not amount:
#                     continue

#                 natural = extract_natural_account(account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date if row.order_date else date(row.year, row.month, 1),
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # ASSET JOURNAL
#         # ============================================
#         for row in db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(2000):

#             coa = coa_map.get(row.natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=date(row.year, row.month, 1),
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=str(row.natural_account),
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # TAX
#         # ============================================
#         for row in db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(2000):

#             if row.dr_account and row.dr_amount:
#                 natural = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # YEAR-WISE CLOSING (FINAL FIXED)
#         # ============================================
#         closing_rows = []

#         year_summary = db.query(
#             func.extract('year', FactGeneralLedger.order_date).label("year"),
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(
#             func.extract('year', FactGeneralLedger.order_date),
#             FactGeneralLedger.account
#         ).all()

#         from collections import defaultdict
#         year_map = defaultdict(list)

#         for row in year_summary:
#             year_map[int(row.year)].append(row)

#         for year, rows in year_map.items():

#             closing_date = date(year, 12, 31)

#             total_income = 0
#             total_expense = 0

#             for row in rows:
#                 natural = extract_natural_account(row.account)
#                 coa = coa_map.get(natural)

#                 if not coa:
#                     continue

#                 acc_type = get_account_type(coa.subclass)

#                 if acc_type == "Income":
#                     balance = (row.cr or 0) - (row.dr or 0)
#                 elif acc_type == "Expense":
#                     balance = (row.dr or 0) - (row.cr or 0)
#                 else:
#                     continue

#                 if acc_type == "Income" and balance != 0:
#                     total_income += balance

#                     closing_rows.append(FactGeneralLedger(
#                         company_id=company_id,
#                         batch_id=batch_id,
#                         order_date=closing_date,
#                         month=12,
#                         account=row.account,
#                         dr_amount=balance,
#                         cr_amount=0,
#                         natural_account=str(natural),
#                         account_subclass=coa.subclass,
#                         account_type=acc_type,
#                         sub_account=coa.subaccount,
#                         is_closing_entry=True,
#                         coa_id=coa.id
#                     ))

#                 elif acc_type == "Expense" and balance != 0:
#                     total_expense += balance

#                     closing_rows.append(FactGeneralLedger(
#                         company_id=company_id,
#                         batch_id=batch_id,
#                         order_date=closing_date,
#                         month=12,
#                         account=row.account,
#                         dr_amount=0,
#                         cr_amount=balance,
#                         natural_account=str(natural),
#                         account_subclass=coa.subclass,
#                         account_type=acc_type,
#                         sub_account=coa.subaccount,
#                         is_closing_entry=True,
#                         coa_id=coa.id
#                     ))

#             profit = total_income - total_expense

#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=0,
#                 cr_amount=total_income,
#                 natural_account=str(income_summary_coa.account_key),
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=total_expense,
#                 cr_amount=0,
#                 natural_account=str(income_summary_coa.account_key),
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#             if profit != 0:
#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=build_account_code(income_summary_coa.account_key),
#                     dr_amount=profit if profit > 0 else 0,
#                     cr_amount=abs(profit) if profit < 0 else 0,
#                     natural_account=str(income_summary_coa.account_key),
#                     account_subclass=income_summary_coa.subclass,
#                     account_type=get_account_type(income_summary_coa.subclass),
#                     sub_account=income_summary_coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=income_summary_coa.id
#                 ))

#             if profit != 0:
#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=build_account_code(retained_earnings_coa.account_key),
#                     dr_amount=0 if profit > 0 else abs(profit),
#                     cr_amount=profit if profit > 0 else 0,
#                     natural_account=str(retained_earnings_coa.account_key),
#                     account_subclass=retained_earnings_coa.subclass,
#                     account_type=get_account_type(retained_earnings_coa.subclass),
#                     sub_account=retained_earnings_coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=retained_earnings_coa.id
#                 ))

#         db.bulk_save_objects(closing_rows)
#         db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e

# --------------------------------------------------------------------------------------------
# 99% working - just needs the opening year fix and some closing entry tweaks (finalized in next commit)

# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import date, datetime

# from collections import defaultdict

# from models import (
#     DimAssetValue,
#     DimAssetValue,
#     FactGeneralLedger,
#     FactSLAccountingWide,
#     FactAssetJournal,
#     FactSubLedger,
#     FactTax,
#     DimCOA
# )

# # ============================================
# # ACCOUNT TYPE
# # ============================================
# def get_account_type(subclass: str):
#     if not subclass:
#         return "Expense"

#     val = subclass.strip().lower()

#     if val == "assets":
#         return "Assets"
#     elif val == "liabilities":
#         return "Liabilities"
#     elif val == "sales":
#         return "Income"
#     elif val == "owners equity":
#         return "Equity"
#     else:
#         return "Expense"


# # ============================================
# # HELPERS
# # ============================================
# def extract_natural_account(account: str):
#     return int(account.split("-")[-1]) if account else None


# def build_account_code(natural_account: int):
#     return f"2040-0000-{natural_account}"


# # ============================================
# # MAIN PROCESS
# # ============================================
# def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

#     try:
#         # ============================================
#         # DELETE OLD DATA
#         # ============================================
#         db.query(FactGeneralLedger).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id
#         ).delete()
#         db.commit()

#         gl_rows = []

#         # ============================================
#         # COA CACHE
#         # ============================================
#         coa_map = {
#             c.account_key: c
#             for c in db.query(DimCOA).filter(
#                 DimCOA.company_id == company_id,
#                 DimCOA.batch_id == batch_id,
#                 DimCOA.is_deleted == False
#             ).all()
#         }

#         income_summary_coa = coa_map.get(202)
#         retained_earnings_coa = coa_map.get(200)

#         if not income_summary_coa or not retained_earnings_coa:
#             raise Exception("Missing COA 202 / 200")

#         # ============================================
#         # OPENING YEAR FIX (SAFE)
#         # ============================================
#         min_year = db.query(
#         func.min(func.extract('year', FactSubLedger.date))
#         ).filter(
#           FactSubLedger.company_id == company_id,
#           FactSubLedger.batch_id == batch_id,
#           FactSubLedger.is_deleted == False
#         ).scalar()

#         current_year = int(min_year)

#         # ============================================
#         # DEFAULT ENTRY
#         # ============================================
#         gl_rows.extend([
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-10",
#                 dr_amount=1480950.18,
#                 cr_amount=0,
#                 natural_account="10",
#                 account_subclass="Assets",
#                 account_type="Assets",
#                 sub_account="Cash at bank",
#                 is_closing_entry=False
#             ),
#             FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=date(current_year, 1, 1),
#                 month=1,
#                 account="2040-0000-180",
#                 dr_amount=0,
#                 cr_amount=1480950.18,
#                 natural_account="180",
#                 account_subclass="Owners equity",
#                 account_type="Equity",
#                 sub_account="Share capital",
#                 is_closing_entry=False
#             )
#         ])


#         # ============================================
#         # SL DATA
#         # ============================================
#         fields = [
#             ("revenue_dr_account", "revenue_dr_amount", "DR"),
#             ("revenue_cr_account", "revenue_cr_amount", "CR"),
#             ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
#             ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
#             ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
#             ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
#             ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
#             ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
#             ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
#             ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
#             ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
#             ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
#             ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
#             ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
#             ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
#             ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
#             ("cogs_dr_account", "cogs_dr_amount", "DR"),
#             ("cogs_cr_account", "cogs_cr_amount", "CR"),
#             ("sga_dr_account", "sga_dr_amount", "DR"),
#             ("sga_cr_account", "sga_cr_amount", "CR"),
#         ]

#         for row in db.query(FactSLAccountingWide).filter(
#             FactSLAccountingWide.company_id == company_id,
#             FactSLAccountingWide.batch_id == batch_id
#         ).yield_per(2000):

#             for acc_field, amt_field, entry_type in fields:
#                 account = getattr(row, acc_field)
#                 amount = getattr(row, amt_field)

#                 if not account or amount is None:
#                     continue

#                 natural = extract_natural_account(account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     sl_accounting_id=row.id,
#                     order_id=row.order_id,
#                     order_date=row.order_date if row.order_date else date(row.year, row.month, 1),
#                     month=row.month,
#                     account=account,
#                     dr_amount=amount if entry_type == "DR" else 0,
#                     cr_amount=amount if entry_type == "CR" else 0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         # ============================================
#         # ASSET JOURNAL
#         # ============================================
#         for row in db.query(FactAssetJournal).filter(
#             FactAssetJournal.company_id == company_id,
#             FactAssetJournal.batch_id == batch_id
#         ).yield_per(2000):

#             coa = coa_map.get(row.natural_account)

#             gl_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 asset_journal_id=row.id,
#                 asset_id=row.asset_id,
#                 order_date=date(row.year, row.month, 1),
#                 month=row.month,
#                 account=row.account_code,
#                 dr_amount=row.dr_amount or 0,
#                 cr_amount=row.cr_amount or 0,
#                 natural_account=str(row.natural_account),
#                 account_subclass=coa.subclass if coa else None,
#                 account_type=get_account_type(coa.subclass if coa else None),
#                 sub_account=coa.subaccount if coa else None,
#                 is_closing_entry=False,
#                 coa_id=coa.id if coa else None
#             ))

#         # ============================================
#         # TAX
#         # ============================================
#         for row in db.query(FactTax).filter(
#             FactTax.company_id == company_id,
#             FactTax.batch_id == batch_id
#         ).yield_per(2000):

#             if row.dr_account and row.dr_amount:
#                 natural = extract_natural_account(row.dr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.dr_account,
#                     dr_amount=row.dr_amount,
#                     cr_amount=0,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#             if row.cr_account and row.cr_amount:
#                 natural = extract_natural_account(row.cr_account)
#                 coa = coa_map.get(natural)

#                 gl_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     fact_tax_id=row.id,
#                     order_date=date(row.year, row.month, 1),
#                     month=row.month,
#                     account=row.cr_account,
#                     dr_amount=0,
#                     cr_amount=row.cr_amount,
#                     natural_account=str(natural),
#                     account_subclass=coa.subclass if coa else None,
#                     account_type=get_account_type(coa.subclass if coa else None),
#                     sub_account=coa.subaccount if coa else None,
#                     is_closing_entry=False,
#                     coa_id=coa.id if coa else None
#                 ))

#         db.bulk_save_objects(gl_rows)
#         db.commit()

#         # ============================================
#         # YEAR WISE CLOSING
#         # ============================================
#         closing_rows = []

#         year_summary = db.query(
#             func.extract('year', FactGeneralLedger.order_date).label("year"),
#             FactGeneralLedger.account,
#             func.sum(FactGeneralLedger.dr_amount).label("dr"),
#             func.sum(FactGeneralLedger.cr_amount).label("cr")
#         ).filter(
#             FactGeneralLedger.company_id == company_id,
#             FactGeneralLedger.batch_id == batch_id,
#             FactGeneralLedger.is_closing_entry == False
#         ).group_by(
#             func.extract('year', FactGeneralLedger.order_date),
#             FactGeneralLedger.account
#         ).all()

#         year_map = defaultdict(list)

#         for row in year_summary:
#             if row.year:
#                 year_map[int(row.year)].append(row)

#         for year, rows in year_map.items():

#             closing_date = date(year, 12, 31)

#             total_income = 0
#             total_expense = 0

#             for row in rows:
#                 natural = extract_natural_account(row.account)
#                 coa = coa_map.get(natural)

#                 if not coa:
#                     continue

#                 acc_type = get_account_type(coa.subclass)

#                 if acc_type == "Income":
#                     balance = (row.cr or 0) - (row.dr or 0)
#                     total_income += balance if balance != 0 else 0

#                     if balance != 0:
#                         closing_rows.append(FactGeneralLedger(
#                             company_id=company_id,
#                             batch_id=batch_id,
#                             order_date=closing_date,
#                             month=12,
#                             account=row.account,
#                             dr_amount=balance,
#                             cr_amount=0,
#                             natural_account=str(natural),
#                             account_subclass=coa.subclass,
#                             account_type=acc_type,
#                             sub_account=coa.subaccount,
#                             is_closing_entry=True,
#                             coa_id=coa.id
#                         ))

#                 elif acc_type == "Expense":
#                     balance = (row.dr or 0) - (row.cr or 0)
#                     total_expense += balance if balance != 0 else 0

#                     if balance != 0:
#                         closing_rows.append(FactGeneralLedger(
#                             company_id=company_id,
#                             batch_id=batch_id,
#                             order_date=closing_date,
#                             month=12,
#                             account=row.account,
#                             dr_amount=0,
#                             cr_amount=balance,
#                             natural_account=str(natural),
#                             account_subclass=coa.subclass,
#                             account_type=acc_type,
#                             sub_account=coa.subaccount,
#                             is_closing_entry=True,
#                             coa_id=coa.id
#                         ))

#             profit = total_income - total_expense

#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=0,
#                 cr_amount=total_income,
#                 natural_account=str(income_summary_coa.account_key),
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#             closing_rows.append(FactGeneralLedger(
#                 company_id=company_id,
#                 batch_id=batch_id,
#                 order_date=closing_date,
#                 month=12,
#                 account=build_account_code(income_summary_coa.account_key),
#                 dr_amount=total_expense,
#                 cr_amount=0,
#                 natural_account=str(income_summary_coa.account_key),
#                 account_subclass=income_summary_coa.subclass,
#                 account_type=get_account_type(income_summary_coa.subclass),
#                 sub_account=income_summary_coa.subaccount,
#                 is_closing_entry=True,
#                 coa_id=income_summary_coa.id
#             ))

#             if profit != 0:
#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=build_account_code(income_summary_coa.account_key),
#                     dr_amount=profit if profit > 0 else 0,
#                     cr_amount=abs(profit) if profit < 0 else 0,
#                     natural_account=str(income_summary_coa.account_key),
#                     account_subclass=income_summary_coa.subclass,
#                     account_type=get_account_type(income_summary_coa.subclass),
#                     sub_account=income_summary_coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=income_summary_coa.id
#                 ))

#             if profit != 0:
#                 closing_rows.append(FactGeneralLedger(
#                     company_id=company_id,
#                     batch_id=batch_id,
#                     order_date=closing_date,
#                     month=12,
#                     account=build_account_code(retained_earnings_coa.account_key),
#                     dr_amount=0 if profit > 0 else abs(profit),
#                     cr_amount=profit if profit > 0 else 0,
#                     natural_account=str(retained_earnings_coa.account_key),
#                     account_subclass=retained_earnings_coa.subclass,
#                     account_type=get_account_type(retained_earnings_coa.subclass),
#                     sub_account=retained_earnings_coa.subaccount,
#                     is_closing_entry=True,
#                     coa_id=retained_earnings_coa.id
#                 ))

#         db.bulk_save_objects(closing_rows)
#         db.commit()

#         return {
#             "status": "success",
#             "rows_inserted": len(gl_rows) + len(closing_rows)
#         }

#     except Exception as e:
#         db.rollback()
#         raise e

# -----------------------------------------------------------------------------


from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime

from collections import defaultdict

from models import (
    DimAssetValue,
    DimAssetValue,
    FactGeneralLedger,
    FactSLAccountingWide,
    FactAssetJournal,
    FactSubLedger,
    FactTax,
    DimCOA
)

# ============================================
# ACCOUNT TYPE
# ============================================
def get_account_type(subclass: str):
    if not subclass:
        return "Expense"

    val = subclass.strip().lower()

    if val == "assets":
        return "Assets"
    elif val == "liabilities":
        return "Liabilities"
    elif val == "sales":
        return "Income"
    elif val == "owners equity":
        return "Equity"
    else:
        return "Expense"


# ============================================
# HELPERS
# ============================================
def extract_natural_account(account: str):
    return int(account.split("-")[-1]) if account else None


def build_account_code(natural_account: int):
    return f"2040-0000-{natural_account}"


# ============================================
# MAIN PROCESS
# ============================================
def process_fact_general_ledger(db: Session, company_id: int, batch_id: int):

    try:
        # ============================================
        # DELETE OLD DATA
        # ============================================
        db.query(FactGeneralLedger).filter(
            FactGeneralLedger.company_id == company_id,
            FactGeneralLedger.batch_id == batch_id
        ).delete()
        db.commit()

        gl_rows = []

        # ============================================
        # COA CACHE
        # ============================================
        coa_map = {
            c.account_key: c
            for c in db.query(DimCOA).filter(
                DimCOA.company_id == company_id,
                DimCOA.batch_id == batch_id,
                DimCOA.is_deleted == False
            ).all()
        }

        income_summary_coa = coa_map.get(202)
        retained_earnings_coa = coa_map.get(200)

        if not income_summary_coa or not retained_earnings_coa:
            raise Exception("Missing COA 202 / 200")

        # ============================================
        # OPENING YEAR FIX (SAFE)
        # ============================================
        min_year = db.query(
        func.min(func.extract('year', FactSubLedger.date))
        ).filter(
          FactSubLedger.company_id == company_id,
          FactSubLedger.batch_id == batch_id,
          FactSubLedger.is_deleted == False
        ).scalar()

        current_year = int(min_year)

        # ============================================
        # DEFAULT ENTRY
        # ============================================
        gl_rows.extend([
            FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=date(current_year, 1, 1),
                month=1,
                account="2040-0000-10",
                dr_amount=1480950.18,
                cr_amount=0,
                natural_account="10",
                account_subclass="Assets",
                account_type="Assets",
                sub_account="Cash at bank",
                is_closing_entry=False
            ),
            FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=date(current_year, 1, 1),
                month=1,
                account="2040-0000-180",
                dr_amount=0,
                cr_amount=1480950.18,
                natural_account="180",
                account_subclass="Owners equity",
                account_type="Equity",
                sub_account="Share capital",
                is_closing_entry=False
            )
        ])


        

        # ============================================
        # SL DATA
        # ============================================
        fields = [
            ("revenue_dr_account", "revenue_dr_amount", "DR"),
            ("revenue_cr_account", "revenue_cr_amount", "CR"),
            ("rm_dr_account_1", "rm_dr_amount_1", "DR"),
            ("rm_cr_account_1", "rm_cr_amount_1", "CR"),
            ("rm_dr_account_2", "rm_dr_amount_2", "DR"),
            ("rm_cr_account_2", "rm_cr_amount_2", "CR"),
            ("dl_dr_account_1", "dl_dr_amount_1", "DR"),
            ("dl_cr_account_1", "dl_cr_amount_1", "CR"),
            ("dl_dr_account_2", "dl_dr_amount_2", "DR"),
            ("dl_cr_account_2", "dl_cr_amount_2", "CR"),
            ("overhead_dr_account_1", "overhead_dr_amount_1", "DR"),
            ("overhead_cr_account_1", "overhead_cr_amount_1", "CR"),
            ("overhead_dr_account_2", "overhead_dr_amount_2", "DR"),
            ("overhead_cr_account_2", "overhead_cr_amount_2", "CR"),
            ("overhead_dr_account_3", "overhead_dr_amount_3", "DR"),
            ("overhead_cr_account_3", "overhead_cr_amount_3", "CR"),
            ("cogs_dr_account", "cogs_dr_amount", "DR"),
            ("cogs_cr_account", "cogs_cr_amount", "CR"),
            ("sga_dr_account", "sga_dr_amount", "DR"),
            ("sga_cr_account", "sga_cr_amount", "CR"),
        ]

        for row in db.query(FactSLAccountingWide).filter(
            FactSLAccountingWide.company_id == company_id,
            FactSLAccountingWide.batch_id == batch_id
        ).yield_per(2000):

            for acc_field, amt_field, entry_type in fields:
                account = getattr(row, acc_field)
                amount = getattr(row, amt_field)

                if not account or amount is None:
                    continue

                natural = extract_natural_account(account)
                coa = coa_map.get(natural)

                gl_rows.append(FactGeneralLedger(
                    company_id=company_id,
                    batch_id=batch_id,
                    sl_accounting_id=row.id,
                    order_id=row.order_id,
                    order_date=row.order_date if row.order_date else date(row.year, row.month, 1),
                    month=row.month,
                    account=account,
                    dr_amount=amount if entry_type == "DR" else 0,
                    cr_amount=amount if entry_type == "CR" else 0,
                    natural_account=str(natural),
                    account_subclass=coa.subclass if coa else None,
                    account_type=get_account_type(coa.subclass if coa else None),
                    sub_account=coa.subaccount if coa else None,
                    is_closing_entry=False,
                    coa_id=coa.id if coa else None
                ))

        # ============================================
        # ASSET JOURNAL
        # ============================================
        for row in db.query(FactAssetJournal).filter(
            FactAssetJournal.company_id == company_id,
            FactAssetJournal.batch_id == batch_id
        ).yield_per(2000):

            coa = coa_map.get(row.natural_account)

            gl_rows.append(FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                asset_journal_id=row.id,
                asset_id=row.asset_id,
                order_date=date(row.year, row.month, 1),
                month=row.month,
                account=row.account_code,
                dr_amount=row.dr_amount or 0,
                cr_amount=row.cr_amount or 0,
                natural_account=str(row.natural_account),
                account_subclass=coa.subclass if coa else None,
                account_type=get_account_type(coa.subclass if coa else None),
                sub_account=coa.subaccount if coa else None,
                is_closing_entry=False,
                coa_id=coa.id if coa else None
            ))

        # ============================================
        # TAX
        # ============================================
        for row in db.query(FactTax).filter(
            FactTax.company_id == company_id,
            FactTax.batch_id == batch_id
        ).yield_per(2000):

            if row.dr_account and row.dr_amount:
                natural = extract_natural_account(row.dr_account)
                coa = coa_map.get(natural)

                gl_rows.append(FactGeneralLedger(
                    company_id=company_id,
                    batch_id=batch_id,
                    fact_tax_id=row.id,
                    order_date=date(row.year, row.month, 1),
                    month=row.month,
                    account=row.dr_account,
                    dr_amount=row.dr_amount,
                    cr_amount=0,
                    natural_account=str(natural),
                    account_subclass=coa.subclass if coa else None,
                    account_type=get_account_type(coa.subclass if coa else None),
                    sub_account=coa.subaccount if coa else None,
                    is_closing_entry=False,
                    coa_id=coa.id if coa else None
                ))

            if row.cr_account and row.cr_amount:
                natural = extract_natural_account(row.cr_account)
                coa = coa_map.get(natural)

                gl_rows.append(FactGeneralLedger(
                    company_id=company_id,
                    batch_id=batch_id,
                    fact_tax_id=row.id,
                    order_date=date(row.year, row.month, 1),
                    month=row.month,
                    account=row.cr_account,
                    dr_amount=0,
                    cr_amount=row.cr_amount,
                    natural_account=str(natural),
                    account_subclass=coa.subclass if coa else None,
                    account_type=get_account_type(coa.subclass if coa else None),
                    sub_account=coa.subaccount if coa else None,
                    is_closing_entry=False,
                    coa_id=coa.id if coa else None
                ))

        db.bulk_save_objects(gl_rows)
        db.commit()

        # ============================================
        # YEAR WISE CLOSING
        # ============================================
        closing_rows = []

        year_summary = db.query(
            func.extract('year', FactGeneralLedger.order_date).label("year"),
            FactGeneralLedger.account,
            func.sum(FactGeneralLedger.dr_amount).label("dr"),
            func.sum(FactGeneralLedger.cr_amount).label("cr")
        ).filter(
            FactGeneralLedger.company_id == company_id,
            FactGeneralLedger.batch_id == batch_id,
            FactGeneralLedger.is_closing_entry == False
        ).group_by(
            func.extract('year', FactGeneralLedger.order_date),
            FactGeneralLedger.account
        ).all()

        year_map = defaultdict(list)

        for row in year_summary:
            if row.year:
                year_map[int(row.year)].append(row)

        for year, rows in year_map.items():

            closing_date = date(year, 12, 31)

            total_income = 0
            total_expense = 0

            for row in rows:
                natural = extract_natural_account(row.account)
                coa = coa_map.get(natural)

                if not coa:
                    continue

                acc_type = get_account_type(coa.subclass)

                if acc_type == "Income":
                    balance = (row.cr or 0) - (row.dr or 0)
                    total_income += balance if balance != 0 else 0

                    if balance != 0:
                        closing_rows.append(FactGeneralLedger(
                            company_id=company_id,
                            batch_id=batch_id,
                            order_date=closing_date,
                            month=12,
                            account=row.account,
                            dr_amount=balance,
                            cr_amount=0,
                            natural_account=str(natural),
                            account_subclass=coa.subclass,
                            account_type=acc_type,
                            sub_account=coa.subaccount,
                            is_closing_entry=True,
                            coa_id=coa.id
                        ))

                elif acc_type == "Expense":
                    balance = (row.dr or 0) - (row.cr or 0)
                    total_expense += balance if balance != 0 else 0

                    if balance != 0:
                        closing_rows.append(FactGeneralLedger(
                            company_id=company_id,
                            batch_id=batch_id,
                            order_date=closing_date,
                            month=12,
                            account=row.account,
                            dr_amount=0,
                            cr_amount=balance,
                            natural_account=str(natural),
                            account_subclass=coa.subclass,
                            account_type=acc_type,
                            sub_account=coa.subaccount,
                            is_closing_entry=True,
                            coa_id=coa.id
                        ))

            profit = total_income - total_expense

            closing_rows.append(FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=closing_date,
                month=12,
                account=build_account_code(income_summary_coa.account_key),
                dr_amount=0,
                cr_amount=total_income,
                natural_account=str(income_summary_coa.account_key),
                account_subclass=income_summary_coa.subclass,
                account_type=get_account_type(income_summary_coa.subclass),
                sub_account=income_summary_coa.subaccount,
                is_closing_entry=True,
                coa_id=income_summary_coa.id
            ))

            closing_rows.append(FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=closing_date,
                month=12,
                account=build_account_code(income_summary_coa.account_key),
                dr_amount=total_expense,
                cr_amount=0,
                natural_account=str(income_summary_coa.account_key),
                account_subclass=income_summary_coa.subclass,
                account_type=get_account_type(income_summary_coa.subclass),
                sub_account=income_summary_coa.subaccount,
                is_closing_entry=True,
                coa_id=income_summary_coa.id
            ))

            if profit != 0:
                closing_rows.append(FactGeneralLedger(
                    company_id=company_id,
                    batch_id=batch_id,
                    order_date=closing_date,
                    month=12,
                    account=build_account_code(income_summary_coa.account_key),
                    dr_amount=profit if profit > 0 else 0,
                    cr_amount=abs(profit) if profit < 0 else 0,
                    natural_account=str(income_summary_coa.account_key),
                    account_subclass=income_summary_coa.subclass,
                    account_type=get_account_type(income_summary_coa.subclass),
                    sub_account=income_summary_coa.subaccount,
                    is_closing_entry=True,
                    coa_id=income_summary_coa.id
                ))

            if profit != 0:
                closing_rows.append(FactGeneralLedger(
                    company_id=company_id,
                    batch_id=batch_id,
                    order_date=closing_date,
                    month=12,
                    account=build_account_code(retained_earnings_coa.account_key),
                    dr_amount=0 if profit > 0 else abs(profit),
                    cr_amount=profit if profit > 0 else 0,
                    natural_account=str(retained_earnings_coa.account_key),
                    account_subclass=retained_earnings_coa.subclass,
                    account_type=get_account_type(retained_earnings_coa.subclass),
                    sub_account=retained_earnings_coa.subaccount,
                    is_closing_entry=True,
                    coa_id=retained_earnings_coa.id
                ))

        db.bulk_save_objects(closing_rows)
        db.commit()


        # ============================================
        # ADD OPENING FOR NEXT YEARS (NO CHANGE LOGIC)
        # ============================================

        opening_rows = []

        # get all years already present
        years = db.query(
        func.extract('year', FactGeneralLedger.order_date)
        ).filter(
            FactGeneralLedger.company_id == company_id,
            FactGeneralLedger.batch_id == batch_id,
            FactGeneralLedger.is_closing_entry == False
        ).distinct().all()

        years = sorted([int(y[0]) for y in years if y[0]])

        for i in range(len(years) - 1):
            prev_year = years[i]
            next_year = years[i + 1]

            # get closing balance of CASH from previous year
            closing_balance = db.query(
                (func.sum(FactGeneralLedger.dr_amount) - func.sum(FactGeneralLedger.cr_amount))
            ).filter(
                FactGeneralLedger.company_id == company_id,
                FactGeneralLedger.batch_id == batch_id,
                func.extract('year', FactGeneralLedger.order_date) == prev_year,
                FactGeneralLedger.account == "2040-0000-10"
            ).scalar()

            closing_balance = float(closing_balance or 0)

            # add next year opening
            opening_rows.append(FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=date(next_year, 1, 1),
                month=1,
                account="2040-0000-10",
                dr_amount=closing_balance,
                cr_amount=0,
                natural_account="10",
                account_subclass="Assets",
                account_type="Assets",
                sub_account="Cash at bank",
                is_closing_entry=False
            ))

            opening_rows.append(FactGeneralLedger(
                company_id=company_id,
                batch_id=batch_id,
                order_date=date(next_year, 1, 1),
                month=1,
                account="2040-0000-180",
                dr_amount=0,
                cr_amount=closing_balance,
                natural_account="180",
                account_subclass="Owners equity",
                account_type="Equity",
                sub_account="Share capital",
                is_closing_entry=False
            ))

        db.bulk_save_objects(opening_rows)
        db.commit()


        return {
            "status": "success",
            "rows_inserted": len(gl_rows) + len(closing_rows)
        }

    except Exception as e:
        db.rollback()
        raise e

# -----------------------------------------------------------------------------

