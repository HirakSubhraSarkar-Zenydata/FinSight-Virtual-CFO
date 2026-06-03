# from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Path
# from sqlalchemy.orm import Session
# from database import SessionLocal
# from models import FileUpload, IngestionBatch, User
# from auth import get_current_user
# from supabase import create_client
# import os
# from datetime import datetime
# import uuid
# from typing import Optional

# router = APIRouter()

# # =========================
# # SUPABASE CONFIG
# # =========================
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# BUCKET_NAME = "File Storage"

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# # =========================
# # VALID FILE TYPES
# # =========================
# VALID_FILE_TYPES = {"COA", "PRODUCT", "BSV_TAX", "SUBLEDGER", "ASSET_VALUE"}

# # =========================
# # DB Dependency
# # =========================
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # =========================
# # UPLOAD API (UPDATED)
# # =========================
# @router.post("/upload")
# async def upload_file(
#     file: UploadFile = File(...),
#     file_type: str = Form(...),
#     batch_id: Optional[int] = Form(None),   # ✅ NEW
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user)
# ):
#     file_type = file_type.upper()

#     if file_type not in VALID_FILE_TYPES:
#         raise HTTPException(status_code=400, detail="Invalid file type")

#     try:
#         # =========================
#         # USE OR CREATE BATCH
#         # =========================
#         if batch_id:
#             batch = db.query(IngestionBatch).filter(
#                 IngestionBatch.id == batch_id,
#                 IngestionBatch.company_id == user.company_id
#             ).first()

#             if not batch:
#                 raise HTTPException(status_code=404, detail="Batch not found")

#         else:
#             batch = IngestionBatch(
#                 company_id=user.company_id,
#                 status="pending",
#                 created_at=datetime.utcnow()
#             )
#             db.add(batch)
#             db.commit()
#             db.refresh(batch)

#         # =========================
#         # PREVENT DUPLICATE FILE TYPE
#         # =========================
#         existing = db.query(FileUpload).filter(
#             FileUpload.batch_id == batch.id,
#             FileUpload.file_type == file_type
#         ).first()

#         if existing:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"{file_type} already uploaded in this batch"
#             )

#         # =========================
#         # FILE PATH
#         # =========================
#         file_id = str(uuid.uuid4())
#         file_path = f"{user.company_id}/{batch.id}/{file_type}/{file_id}_{file.filename}"

#         # =========================
#         # READ FILE
#         # =========================
#         file_bytes = await file.read()

#         # =========================
#         # UPLOAD TO SUPABASE
#         # =========================
#         supabase.storage.from_(BUCKET_NAME).upload(
#             file_path,
#             file_bytes,
#             {"content-type": file.content_type}
#         )

#         # =========================
#         # SAVE DB ENTRY
#         # =========================
#         upload_entry = FileUpload(
#             company_id=user.company_id,
#             batch_id=batch.id,
#             file_name=file.filename,
#             file_type=file_type,
#             file_path=file_path,
#             status="pending",
#             uploaded_at=datetime.utcnow()
#         )

#         db.add(upload_entry)
#         db.commit()

#         return {
#             "message": "File uploaded successfully",
#             "file_type": file_type,
#             "file_path": file_path,
#             "batch_id": batch.id
#         }

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))


# # =========================
# # DELETE FILE
# # =========================
# @router.delete("/files/{file_id}")
# async def delete_file(
#     file_id: int = Path(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         file_upload = db.query(FileUpload).filter(
#             FileUpload.id == file_id,
#             FileUpload.company_id == current_user.company_id
#         ).first()

#         if not file_upload:
#             raise HTTPException(status_code=404, detail="File not found")

#         batch_id = file_upload.batch_id

#         # =========================
#         # DELETE FROM STORAGE
#         # =========================
#         try:
#             supabase.storage.from_(BUCKET_NAME).remove([file_upload.file_path])
#         except Exception as storage_err:
#             print(f"Storage delete warning: {storage_err}")

#         # =========================
#         # DELETE FILE
#         # =========================
#         db.delete(file_upload)
#         db.commit()

#         # =========================
#         # DELETE BATCH IF EMPTY
#         # =========================
#         remaining_files = db.query(FileUpload).filter(
#             FileUpload.batch_id == batch_id
#         ).count()

#         if remaining_files == 0:
#             db.query(IngestionBatch).filter(
#                 IngestionBatch.id == batch_id,
#                 IngestionBatch.company_id == current_user.company_id
#             ).delete()
#             db.commit()

#         return {
#             "message": "File deleted successfully",
#             "file_id": file_id,
#             "batch_deleted": remaining_files == 0
#         }

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))


from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from database import SessionLocal
from models import FileUpload, IngestionBatch, User
from auth import get_current_user, require_admin
from supabase import create_client
import os
from datetime import datetime
import uuid
from typing import Optional

router = APIRouter()

# =========================
# SUPABASE CONFIG
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "File Storage"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# VALID FILE TYPES
# =========================
VALID_FILE_TYPES = {"COA", "PRODUCT", "BSV_TAX", "SUBLEDGER", "ASSET_VALUE"}

# =========================
# DB Dependency
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# UPLOAD API (UPDATED)
# =========================
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    batch_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    # user: User = Depends(get_current_user)
    user: User = Depends(require_admin)  # ✅ ONLY ADMINS CAN UPLOAD
):
    file_type = file_type.upper()

    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        # =========================
        # USE OR CREATE BATCH
        # =========================
        if batch_id:
            batch = db.query(IngestionBatch).filter(
                IngestionBatch.id == batch_id,
                IngestionBatch.company_id == user.company_id
            ).first()

            if not batch:
                raise HTTPException(status_code=404, detail="Batch not found")

        else:
            batch = IngestionBatch(
                company_id=user.company_id,
                status="pending",
                created_by=user.id,  # ✅ ADDED
                created_at=datetime.utcnow()
            )
            db.add(batch)
            db.commit()
            db.refresh(batch)

        # =========================
        # PREVENT DUPLICATE FILE TYPE
        # =========================
        existing = db.query(FileUpload).filter(
            FileUpload.batch_id == batch.id,
            FileUpload.file_type == file_type
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"{file_type} already uploaded in this batch"
            )

        # =========================
        # FILE PATH
        # =========================
        file_id = str(uuid.uuid4())
        file_path = f"{user.company_id}/{batch.id}/{file_type}/{file_id}_{file.filename}"

        # =========================
        # READ FILE
        # =========================
        file_bytes = await file.read()

        # =========================
        # UPLOAD TO SUPABASE
        # =========================
        supabase.storage.from_(BUCKET_NAME).upload(
            file_path,
            file_bytes,
            {"content-type": file.content_type}
        )

        # =========================
        # SAVE DB ENTRY
        # =========================
        upload_entry = FileUpload(
            company_id=user.company_id,
            batch_id=batch.id,
            uploaded_by=user.id,  # ✅ ADDED
            file_name=file.filename,
            file_type=file_type,
            file_path=file_path,
            status="pending",
            uploaded_at=datetime.utcnow()
        )

        db.add(upload_entry)
        db.commit()

        return {
            "message": "File uploaded successfully",
            "file_type": file_type,
            "file_path": file_path,
            "batch_id": batch.id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# DELETE FILE
# =========================
@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int = Path(...),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(require_admin)  # ✅ ONLY ADMINS CAN DELETE
):
    try:
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id,
            FileUpload.company_id == current_user.company_id
        ).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        batch_id = file_upload.batch_id

        # =========================
        # DELETE FROM STORAGE
        # =========================
        try:
            supabase.storage.from_(BUCKET_NAME).remove([file_upload.file_path])
        except Exception as storage_err:
            print(f"Storage delete warning: {storage_err}")

        # =========================
        # DELETE FILE
        # =========================
        db.delete(file_upload)
        db.commit()

        # =========================
        # DELETE BATCH IF EMPTY
        # =========================
        remaining_files = db.query(FileUpload).filter(
            FileUpload.batch_id == batch_id
        ).count()

        if remaining_files == 0:
            db.query(IngestionBatch).filter(
                IngestionBatch.id == batch_id,
                IngestionBatch.company_id == current_user.company_id
            ).delete()
            db.commit()

        return {
            "message": "File deleted successfully",
            "file_id": file_id,
            "batch_deleted": remaining_files == 0
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))