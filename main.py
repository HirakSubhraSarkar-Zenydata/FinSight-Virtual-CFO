from fastapi import FastAPI
from auth import router as auth_router     # Make sure this imports correctly
from ingestion import router as ingestion_router  # ← Add this when ready
from processing import router as processing_router  # ← Add this when ready
from reporting.yearly_pnl import router as pnl_router
from database import engine
from models import Base

app = FastAPI(
    title="Virtual CFO Platform",
    description="Multi-tenant Virtual CFO API",
    version="1.0.0"
)

# Include Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])  # Uncomment when ingestion is ready
app.include_router(processing_router, prefix="/processing", tags=["Processing"])  # Uncomment when processing is ready
app.include_router(pnl_router, prefix="/reporting/pnl", tags=["PnL Reporting"])  # Uncomment when PnL reporting is ready

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