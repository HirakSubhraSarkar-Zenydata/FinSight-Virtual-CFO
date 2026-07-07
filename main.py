from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router     # Make sure this imports correctly
from ingestion import router as ingestion_router  # ← Add this when ready
from processing import router as processing_router  # ← Add this when ready
from reporting.yearly_pnl import router as pnl_router
from reporting.kpi_reporting import router as kpi_router  # ← Add this when ready
from reporting.expense_breakdown import router as expense_breakdown_router  # ← Add this when ready
from reporting.GetReportHistory.batch_history import router as batch_history_router  # ← Add this when ready
from reporting.customer_segmentation import router as customer_segmentation_router  # ← Add this when ready

from admin.invite_user import router as invite_user_router

from database import engine
from models import Base

app = FastAPI(
    title="Virtual CFO Platform",
    description="Multi-tenant Virtual CFO API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])  # Uncomment when ingestion is ready
app.include_router(processing_router, prefix="/processing", tags=["Processing"])  # Uncomment when processing is ready
app.include_router(pnl_router, prefix="/reporting/pnl", tags=["PnL Reporting"])  # Uncomment when PnL reporting is ready
app.include_router(kpi_router, prefix="/reporting/kpi", tags=["KPI Reporting"])  # Uncomment when KPI reporting is ready
app.include_router(expense_breakdown_router, prefix="/reporting/expense-breakdown", tags=["Expense Breakdown"])  # Uncomment when expense breakdown is ready
app.include_router(batch_history_router, prefix="/get-reporting-history", tags=["Report History"])  # Uncomment when report history is ready
app.include_router(customer_segmentation_router, prefix="/reporting", tags=["Customer Segmentation"])  # Uncomment when customer segmentation is ready
app.include_router(invite_user_router, prefix="/admin", tags=["User Management"])

@app.get("/")
def root():
    return {
        "message": "Virtual CFO API is running 🚀",
        "docs": "/docs",
        "create_tables": "/create_tables"
    }


# =========================
# CREATE TABLES (Development Only)
# =========================
@app.get("/create_tables")
def create_tables():
    try:
        # Test connection
        conn = engine.connect()
        conn.close()

        # Create all tables from models
        Base.metadata.create_all(bind=engine)

        return {
            "status": "success",
            "message": "All tables created successfully (if not existed)",
            "note": "This endpoint is for development only. Remove in production."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to create tables",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)