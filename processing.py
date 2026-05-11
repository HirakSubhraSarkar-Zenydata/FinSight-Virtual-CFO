# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from database import SessionLocal
# from models import FileUpload, IngestionBatch, User
# from auth import get_current_user

# from processors.coa_processor import process_coa
# from processors.product_processor import process_product
# from processors.bsv_processor import process_bsv
# from processors.subledger_processor import process_subledger
# from processors.sl_accounting_processor import generate_wide_accounting

# router = APIRouter()


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @router.post("/start-processing/{batch_id}")
# def start_processing(
#     batch_id: int,
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user)
# ):
#     batch = db.query(IngestionBatch).filter(
#         IngestionBatch.id == batch_id,
#         IngestionBatch.company_id == user.company_id
#     ).first()

#     if not batch:
#         raise HTTPException(status_code=404, detail="Batch not found")

#     files = db.query(FileUpload).filter(
#         FileUpload.batch_id == batch_id
#     ).all()

#     file_map = {f.file_type: f for f in files}

#     try:
#         batch.status = "processing"
#         db.commit()

#         # STEP 1
#         process_coa(db, user.company_id, file_map["COA"])

#         # STEP 2
#         process_product(db, user.company_id, file_map["PRODUCT"])

#         # STEP 3
#         process_bsv(db, user.company_id, file_map["BSV_TAX"])

#         # # STEP 4
#         process_subledger(db, user.company_id, file_map["SUBLEDGER"])

#         # # STEP 5
#         # process_slaccounting(db, user.company_id, batch_id)

#         generate_wide_accounting(db, user.company_id)

#         batch.status = "done"
#         db.commit()

#         return {"message": "Processing completed successfully"}

#     except Exception as e:
#         batch.status = "failed"
#         batch.error_summary = str(e)
#         db.commit()
#         raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import FileUpload, IngestionBatch, User
from auth import get_current_user

from processors.coa_processor import process_coa
from processors.product_processor import process_product
from processors.bsv_processor import process_bsv
from processors.subledger_processor import process_subledger
from processors.sl_accounting_processor import generate_wide_accounting
from processors.asset_processor import process_asset_value # for asset value processing
from processors.asset_value_yearly_depretiation_processor import process_asset_yearly_depreciation # for yearly depreciation processing 
from processors.asset_value_monthly_depretiation_processor import process_asset_monthly_depreciation # for monthly depreciation processing
from processors.asset_journal_processor import process_asset_journal # for journal entry generation based on monthly depreciation
from processors.fact_tax_processor import process_fact_tax # for tax calculation based on SL and depreciation data
from processors.fact_general_ledger_processor import process_fact_general_ledger # for generating wide general ledger entries from SL and Asset Journal data, and also calculating tax amounts for each entry based on the tax processor output
from processors.fact_gl_recon_processor import populate_fact_gl_recon # for reconciling the generated general ledger entries to ensure they tie out to the subledger and to calculate final balances for each account
from processors.fact_gl_summary_before_closing import populate_gl_summary_before_closing # for populating the fact_gl_summary_before_closing table with aggregated data from the reconciled general ledger, and comparing to SL net income for validation before we generate closing entries
from processors.fact_gl_summary_after_closing import populate_fact_gl_summary_after_closing # for populating the fact_gl_summary_after_closing table with aggregated data from the general ledger after closing entries have been generated, to validate that the books are balanced and to provide a final summary of assets, liabilities, and equity after closing
from processors.fact_monthly_pnl_processor import populate_fact_monthly_pnl # for populating the fact_monthly_pnl table with monthly aggregated data from the general ledger, to enable monthly P&L reporting and analysis
from processors.fact_monthly_bs_processor import populate_fact_monthly_bs # for populating the fact_monthly_bs table with monthly aggregated data from the fact_monthly_pnl table, to enable monthly balance sheet reporting and analysis
from processors.fact_yearly_pnl_report_processor import populate_fact_yearly_pnl_report # for populating the fact_yearly_pnl_report table with aggregated yearly P&L data by line of business, to enable yearly P&L reporting and analysis
from processors.fact_yearly_bs_report_processor import populate_fact_yearly_bs_report # for populating the fact_yearly_bs_report table with aggregated yearly balance sheet data by line of business, to enable yearly balance sheet reporting and analysis

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/start-processing/{batch_id}")
def start_processing(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    batch = db.query(IngestionBatch).filter(
        IngestionBatch.id == batch_id,
        IngestionBatch.company_id == user.company_id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    files = db.query(FileUpload).filter(
        FileUpload.batch_id == batch_id
    ).all()

    file_map = {f.file_type: f for f in files}

    try:
        batch.status = "processing"
        db.commit()

        # ALL PROCESSING STEPS (ORDER MATTERS)
        process_coa(db, user.company_id, file_map["COA"], batch_id)
        process_product(db, user.company_id, file_map["PRODUCT"], batch_id)
        process_bsv(db, user.company_id, file_map["BSV_TAX"], batch_id)
        process_subledger(db, user.company_id, file_map["SUBLEDGER"], batch_id)

        # Generate wide accounting entries before asset value processing, as asset values may be needed for correct mapping
        generate_wide_accounting(db, user.company_id, batch_id)

        # Added asset value processing step -- dim_asset_value needs to be populated before we can calculate depreciation
        process_asset_value(db, user.company_id, file_map["ASSET_VALUE"], batch_id)

        # Added asset yearly depreciation processing step
        process_asset_yearly_depreciation(db, user.company_id, batch_id)

        # Added asset monthly depreciation processing step (depends on yearly depreciation)
        process_asset_monthly_depreciation(db, user.company_id, batch_id)

        # Added asset journal entry generation step (depends on monthly depreciation)
        process_asset_journal(db, user.company_id, batch_id)

        # Added tax calculation step (depends on wide accounting and monthly depreciation)
        process_fact_tax(db, user.company_id, batch_id)

        # Added general ledger generation step (depends on wide accounting, asset journal, and tax calculation)
        process_fact_general_ledger(db, user.company_id, batch_id)  

        # Added general ledger reconciliation step (depends on general ledger generation)
        populate_fact_gl_recon(db, user.company_id, batch_id)

        # Added step to populate the GL summary before closing
        populate_gl_summary_before_closing(db, user.company_id, batch_id)

        # Added step to populate the GL summary after closing
        populate_fact_gl_summary_after_closing(db, user.company_id, batch_id)

        # Added step to populate the monthly P&L summary
        populate_fact_monthly_pnl(db, user.company_id, batch_id)

        # Added step to populate the monthly balance sheet summary
        populate_fact_monthly_bs(db, user.company_id, batch_id)

        # Added step to populate the yearly P&L report summary
        populate_fact_yearly_pnl_report(db, user.company_id, batch_id)

        # Added step to populate the yearly balance sheet report summary
        populate_fact_yearly_bs_report(db, user.company_id, batch_id)   

        batch.status = "done"
        db.commit()

        return {"message": "Processing completed successfully"}

    except Exception as e:
        batch.status = "failed"
        batch.error_summary = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))