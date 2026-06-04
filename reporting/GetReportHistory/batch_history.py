from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from auth import get_current_user
from models import IngestionBatch, User

router = APIRouter(
    tags=["Report History"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/has-history")
def has_report_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    batch = (
        db.query(IngestionBatch)
        .filter(
            IngestionBatch.company_id == user.company_id,
            # We want to check if the user has any completed batches, so we not filter by created_by and status
            # IngestionBatch.created_by == user.id, 
            IngestionBatch.status == "done"
        )
        .first()
    )

    return {
        "has_reports": batch is not None
    }


@router.get("/history")
def get_report_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    batches = (
        db.query(IngestionBatch)
        .filter(
            IngestionBatch.company_id == user.company_id,
            # IngestionBatch.created_by == user.id,
            IngestionBatch.status == "done"
        )
        .order_by(IngestionBatch.created_at.desc())
        .all()
    )

    return {
        "count": len(batches),
        "data": [
            {
                "batch_id": batch.id,
                "status": batch.status,
                # "total_rows": batch.total_rows,
                # "processed_rows": batch.processed_rows,
                # "failed_rows": batch.failed_rows,
                "created_at": batch.created_at,
                "started_at": batch.started_at,
                "completed_at": batch.completed_at,
            }
            for batch in batches
        ]
    }


@router.get("/history/{batch_id}")
def get_report_by_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    batch = (
        db.query(IngestionBatch)
        .filter(
            IngestionBatch.id == batch_id,
            IngestionBatch.company_id == user.company_id,
            # IngestionBatch.created_by == user.id,
            IngestionBatch.status == "done"
        )
        .first()
    )

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    return {
        "batch_id": batch.id,
        "company_id": batch.company_id,
        "created_by": batch.created_by,
        "status": batch.status,
        # "total_rows": batch.total_rows,
        # "processed_rows": batch.processed_rows,
        # "failed_rows": batch.failed_rows,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at,
        "error_summary": batch.error_summary
    }