"""
models.py — Virtual CFO Platform
SQLAlchemy ORM Models  |  Production Grade  |  Multi-Tenant  |  v3.0 Final

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE  (Medallion)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🥉 Bronze  →  RawData               (immutable, as-uploaded)
  🥈 Silver  →  FactSubLedger         (cleaned, enriched, mapped)
  🥇 Gold    →  FinancialBalance
               KPIValue               (aggregated, KPI-ready)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABLE INVENTORY  (23 tables)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE
  Company                – top-level tenant
  User                   – company employee / CFO user

INGESTION PIPELINE
  IngestionBatch         – batch-level tracking (NEW)
  FileUpload             – every file the company uploads
  RawData                – 🥉 Bronze: immutable staging rows + row_hash
  ValidationLog          – rows that failed ingestion validation

PLATFORM DIMENSIONS  (seeded once, shared across all tenants)
  StandardAccount        – universal COA taxonomy
  DimDate                – full date spine with period-end flags
  DimGeography           – deduplicated region / geo / country

COMPANY DIMENSIONS  (scoped per company_id)
  DimCOA                 – company's raw chart of accounts
  DimProduct             – product master
  DimBSVTaxRate          – BSV + tax rate master
  DimCustomer            – customer master

MAPPING & CONFIGURATION
  AccountMapping         – natural account → standard account bridge
                           (now versioned via effective_from / effective_to)
  CompanySchemaMap       – maps company upload columns → platform columns
  CompanyKPIConfig       – company-level KPI behaviour flags
  KPIFormulaOverride     – country / company KPI formula overrides

FACTS
  FactSubLedger          – 🥈 Silver: transaction-level grain
                           (now carries standard_code + currency_code)

AGGREGATES
  FinancialBalance       – 🥇 Gold: period × standard account balances

FX
  FXRate                 – daily FX rates for multi-currency conversion

KPI
  KPIDefinition          – platform KPI registry (formula as JSON AST)
  KPIValue               – 🥇 Gold: computed KPI values per company × period
                           (now has period_end)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES APPLIED  (v3.0)
  CRITICAL
  1.  Explicit company_id indexes on FactSubLedger, FinancialBalance, KPIValue
  2.  Composite FK safety comment + service-layer validation note on AccountMapping
  3.  standard_code denormalised onto FactSubLedger for 3–10× faster aggregations
  4.  AccountMapping versioned: effective_from / effective_to columns
  5.  IngestionBatch table + batch_id FK on FileUpload and FactSubLedger
  6.  KPIDefinition.formula_ast JSON column (alongside formula text for migration)
  MEDIUM
  7.  currency_code on FactSubLedger for multi-currency transactions
  8.  row_hash on RawData for dedup / replay safety
  9.  StandardAccount: surrogate int id added, code kept as unique index
  10. KPIValue.period_end added
  OTHER
  11. FactSubLedger.coa relationship added (was missing)
  12. ValidationLog back_populates wired on Company + FileUpload
  13. All nullable=False / updated_at fully consistent across all 23 tables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTITIONING  (apply at DB level — PostgreSQL)

  fact_subledger       → PARTITION BY RANGE (date)
                         one child partition per quarter
  financial_balances   → PARTITION BY RANGE (period_start)
  kpi_values           → PARTITION BY HASH  (company_id)

  Example:
    CREATE TABLE fact_subledger PARTITION BY RANGE (date);
    CREATE TABLE fact_subledger_2024_q1
      PARTITION OF fact_subledger
      FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SERVICE-LAYER VALIDATION RULES  (enforce in code, not DB)

  1. AccountMapping cross-company safety:
       ASSERT account_mappings.company_id == dim_coa.company_id
       Enforce in: ingestion service + mapping API endpoint

  2. FactSubLedger.standard_code population:
       On insert, resolve:
         standard_code = AccountMapping
                           .filter(company_id=row.company_id,
                                   natural_account_key=coa.account_key,
                                   status='mapped',
                                   effective_from <= row.date,
                                   effective_to IS NULL OR effective_to >= row.date)
                           .standard_code
       Log to ValidationLog if no active mapping found.

  3. AccountMapping versioning:
       When updating a mapping, set effective_to = today on old row,
       insert new row with effective_from = today + 1.
       Never UPDATE a mapping row — always version it.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

"""
models.py — Virtual CFO Platform
SQLAlchemy ORM Models | Production Grade | Multi-Tenant | v4.0 Final (Connected)
"""

"""
models.py — Virtual CFO Platform
SQLAlchemy ORM Models | Production Grade | Multi-Tenant | v4.1 Fixed
"""

from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, Enum,
    ForeignKey, ForeignKeyConstraint, Index, Integer,
    JSON, Numeric, String, Text, UniqueConstraint,
    and_,
)
from sqlalchemy.orm import relationship, foreign
from database import Base
from sqlalchemy import func

# ============================================================
# ENUMS
# ============================================================
UserRoleEnum = Enum("admin", "analyst", "viewer", name="user_role_enum")
FileTypeEnum = Enum("COA", "PRODUCT", "BSV_TAX", "SUBLEDGER", "SLACCOUNTING", "ASSET_VALUE", name="file_type_enum")
FileStatusEnum = Enum("pending", "processing", "done", "failed", name="file_status_enum")
BatchStatusEnum = Enum("pending", "processing", "done", "failed", "partial", name="batch_status_enum")
MappingStatusEnum = Enum("pending", "mapped", "excluded", name="mapping_status_enum")
AccountMappingStatusEnum = Enum("pending_review", "mapped", "unmapped", "excluded", name="account_mapping_status_enum")
PeriodTypeEnum = Enum("MONTH", "QUARTER", "YEAR", name="period_type_enum")
KPIScopeTypeEnum = Enum("COUNTRY", "COMPANY", name="kpi_scope_type_enum")
SchemaTransformEnum = Enum("uppercase", "lowercase", "strip",
                           "date_dmy", "date_mdy", "int", "float", name="schema_transform_enum")
JournalSideEnum = Enum("DR", "CR", name="journal_side_enum")
SourceTypeEnum = Enum("SUBLEDGER", "MANUAL", "ADJUSTMENT", "GL", name="source_type_enum")

# ============================================================
# NUMERIC CONSTANTS
# ============================================================
MONEY = Numeric(18, 4)
AGGREGATE = Numeric(20, 4)
RATIO = Numeric(18, 6)
MOVEMENT_DEFAULT = "STANDARD"

# ============================================================
# COMPANY - MUST BE FIRST
# ============================================================
class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100))
    country = Column(String(100))
    base_currency = Column(String(3), nullable=False)
    reporting_currency = Column(String(3), nullable=False, default="USD")
    slug = Column(String(100), unique=True, nullable=False)
    fiscal_year_end_month = Column(Integer, nullable=False, default=12)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete")
    batches = relationship("IngestionBatch", back_populates="company", cascade="all, delete")
    uploads = relationship("FileUpload", back_populates="company", cascade="all, delete")
    raw_data = relationship("RawData", back_populates="company", cascade="all, delete")
    validation_logs = relationship("ValidationLog", back_populates="company", cascade="all, delete")
    coas = relationship("DimCOA", back_populates="company", cascade="all, delete")
    products = relationship("DimProduct", back_populates="company", cascade="all, delete")
    bsv_tax_rates = relationship("DimBSVTaxRate", back_populates="company", cascade="all, delete")
    customers = relationship("DimCustomer", back_populates="company", cascade="all, delete")
    account_mappings = relationship("AccountMapping", back_populates="company", cascade="all, delete")
    schema_maps = relationship("CompanySchemaMap", back_populates="company", cascade="all, delete")
    kpi_configs = relationship("CompanyKPIConfig", back_populates="company", cascade="all, delete")
    subledger_facts = relationship("FactSubLedger", back_populates="company", cascade="all, delete")
    financial_balances = relationship("FinancialBalance", back_populates="company", cascade="all, delete")
    kpi_values = relationship("KPIValue", back_populates="company", cascade="all, delete")
    sl_accounting = relationship("FactSLAccounting", back_populates="company", cascade="all, delete")

    # Added
    asset_values = relationship("DimAssetValue", back_populates="company", cascade="all, delete")

    __table_args__ = (
        Index("idx_company_slug", "slug"),
        Index("idx_company_is_deleted", "is_deleted"),
    )


# ============================================================
# USER
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150))
    email = Column(String(255), nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(UserRoleEnum, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="users")
    account_mappings = relationship("AccountMapping", back_populates="mapped_user",
                                    foreign_keys="AccountMapping.mapped_by")

    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_user_company_email"),
        Index("idx_user_company", "company_id"),
        Index("idx_user_is_deleted", "company_id", "is_deleted"),
    )



class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    # ✅ WHO CREATED THIS BATCH
    created_by = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    status = Column(BatchStatusEnum, nullable=False, default="pending")

    total_rows = Column(Integer, nullable=False, default=0)
    processed_rows = Column(Integer, nullable=False, default=0)
    failed_rows = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    error_summary = Column(Text)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =========================
    # RELATIONSHIPS
    # =========================
    company = relationship("Company", back_populates="batches")

    created_user = relationship("User", foreign_keys=[created_by])

    files = relationship(
        "FileUpload",
        back_populates="batch",
        cascade="all, delete"
    )

    subledger_facts = relationship("FactSubLedger", back_populates="batch")
    sl_accounting = relationship("FactSLAccounting", back_populates="batch")

    # =========================
    # INDEXES
    # =========================
    __table_args__ = (
        Index("idx_batch_company", "company_id"),

        # 🔥 IMPORTANT for dashboard filtering
        Index("idx_batch_company_user", "company_id", "created_by"),

        Index("idx_batch_status", "company_id", "status"),
        Index("idx_batch_created_at", "company_id", "created_at"),
    )
    

class FileUpload(Base):
    __tablename__ = "file_uploads"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="SET NULL"),
        nullable=True
    )

    # ✅ WHO UPLOADED THIS FILE
    uploaded_by = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    file_name = Column(String(255))
    file_type = Column(FileTypeEnum, nullable=False)

    file_path = Column(String(500))

    status = Column(FileStatusEnum, nullable=False, default="pending")

    is_deleted = Column(Boolean, nullable=False, default=False)

    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime)

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =========================
    # RELATIONSHIPS
    # =========================
    company = relationship("Company", back_populates="uploads")

    batch = relationship("IngestionBatch", back_populates="files")

    uploaded_user = relationship("User", foreign_keys=[uploaded_by])

    raw_rows = relationship("RawData", back_populates="file", cascade="all, delete")

    validation_logs = relationship("ValidationLog", back_populates="file", cascade="all, delete")

    subledger_facts = relationship("FactSubLedger", back_populates="source_file")
    sl_accounting = relationship("FactSLAccounting", back_populates="source_file")

    asset_values = relationship("DimAssetValue", back_populates="source_file")

    # =========================
    # INDEXES
    # =========================
    __table_args__ = (
        Index("idx_file_upload_company", "company_id"),
        Index("idx_file_upload_batch", "batch_id"),

        # 🔥 IMPORTANT for user filtering
        Index("idx_file_upload_company_user", "company_id", "uploaded_by"),

        Index("idx_file_upload_status", "company_id", "status"),
        Index("idx_file_upload_is_deleted", "company_id", "is_deleted"),
    )


# ============================================================
# RAW DATA & VALIDATION
# ============================================================
class RawData(Base):
    __tablename__ = "raw_data"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(BigInteger, ForeignKey("file_uploads.id", ondelete="CASCADE"), nullable=False)
    row_data = Column(JSON, nullable=False)
    row_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    company = relationship("Company", back_populates="raw_data")
    file = relationship("FileUpload", back_populates="raw_rows")

    __table_args__ = (
        UniqueConstraint("company_id", "file_id", "row_hash", name="uq_raw_data_row_hash"),
        Index("idx_raw_data_company", "company_id"),
        Index("idx_raw_data_file", "file_id"),
        Index("idx_raw_data_row_hash", "row_hash"),
    )


class ValidationLog(Base):
    __tablename__ = "validation_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(BigInteger, ForeignKey("file_uploads.id", ondelete="CASCADE"), nullable=False)
    error_message = Column(Text)
    row_data = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    company = relationship("Company", back_populates="validation_logs")
    file = relationship("FileUpload", back_populates="validation_logs")

    __table_args__ = (
        Index("idx_validation_company", "company_id"),
        Index("idx_validation_file", "file_id"),
    )


# ============================================================
# PLATFORM DIMENSIONS
# ============================================================
class StandardAccount(Base):
    __tablename__ = "standard_accounts"

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    category = Column(String(50))
    is_balance_sheet = Column(Boolean, nullable=False)
    is_flow = Column(Boolean, nullable=False)
    parent_code = Column(String(50), ForeignKey("standard_accounts.code"))
    description = Column(Text)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("StandardAccount", remote_side="StandardAccount.code",
                          foreign_keys=[parent_code], back_populates="children")
    children = relationship("StandardAccount", back_populates="parent",
                            foreign_keys=[parent_code])
    account_mappings = relationship("AccountMapping", back_populates="standard_account")
    subledger_facts = relationship("FactSubLedger", back_populates="standard_acc",
                                   foreign_keys="FactSubLedger.standard_code")
    financial_balances = relationship("FinancialBalance", back_populates="standard_account")

    __table_args__ = (
        Index("idx_standard_account_code", "code"),
        Index("idx_standard_account_parent", "parent_code"),
        Index("idx_standard_account_category", "category"),
    )


class DimDate(Base):
    __tablename__ = "dim_date"

    date = Column(Date, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    is_month_end = Column(Boolean, nullable=False, default=False)
    is_quarter_end = Column(Boolean, nullable=False, default=False)
    is_year_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_dim_date_year_month", "year", "month"),
        Index("idx_dim_date_month_end", "is_month_end"),
        Index("idx_dim_date_quarter_end", "is_quarter_end"),
        Index("idx_dim_date_year_end", "is_year_end"),
    )


class DimGeography(Base):
    __tablename__ = "dim_geography"

    id = Column(BigInteger, primary_key=True, index=True)
    region = Column(String(100), nullable=False)
    geo = Column(String(50), nullable=False)
    country = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    bsv_tax_rates = relationship("DimBSVTaxRate", back_populates="geography")
    subledger_facts = relationship("FactSubLedger", back_populates="geography")
    sl_accounting = relationship("FactSLAccounting", back_populates="geography")

    __table_args__ = (
        UniqueConstraint("region", "geo", "country", name="uq_geography"),
        Index("idx_geography_country", "country"),
        Index("idx_geography_geo", "geo"),
    )



class DimCOA(Base):
    __tablename__ = "dim_coa"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=False)

    account_key = Column(BigInteger, nullable=False)
    report = Column(String(50))
    class_name = Column(String(50))
    subclass = Column(String(100))
    subclass2 = Column(String(100))
    account = Column(String(150))
    subaccount = Column(String(150))

    mapping_status = Column(MappingStatusEnum, nullable=False, default="pending")

    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="coas")
    batch = relationship("IngestionBatch")

    account_mapping = relationship("AccountMapping", back_populates="coa")
    account_rule_mappings = relationship("AccountRuleMapping", back_populates="coa")

    subledger_facts = relationship("FactSubLedger", back_populates="coa", overlaps="company", viewonly=True)

    __table_args__ = (
        UniqueConstraint("company_id", "account_key", "batch_id", name="uq_coa_company_account_batch"),
        UniqueConstraint("id", "company_id", name="uq_coa_id_company"),

        Index("idx_coa_company", "company_id"),
        Index("idx_coa_batch", "company_id", "batch_id"),
        Index("idx_coa_account_key", "account_key"),
        Index("idx_coa_mapping_status", "company_id", "mapping_status"),
        Index("idx_coa_is_deleted", "company_id", "is_deleted"),
    )




class DimProduct(Base):
    __tablename__ = "dim_product"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=False)

    product_code = Column(String(50), nullable=False)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100))
    subcategory = Column(String(100))

    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="products")
    batch = relationship("IngestionBatch")

    subledger_facts = relationship("FactSubLedger", back_populates="product", overlaps="company")

    __table_args__ = (
        UniqueConstraint("company_id", "product_code", "batch_id", name="uq_product_code_batch"),
        UniqueConstraint("id", "company_id", name="uq_product_id_company"),

        Index("idx_product_company", "company_id"),
        Index("idx_product_batch", "company_id", "batch_id"),
        Index("idx_product_is_deleted", "company_id", "is_deleted"),
    )




class DimBSVTaxRate(Base):
    __tablename__ = "dim_bsv_tax_rate"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=False)

    geography_id = Column(BigInteger, ForeignKey("dim_geography.id"), nullable=False)
    bsv_code = Column(String(50))
    tax_rate = Column(RATIO)
    currency = Column(String(3))

    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="bsv_tax_rates")
    geography = relationship("DimGeography", back_populates="bsv_tax_rates")
    batch = relationship("IngestionBatch")

    subledger_facts = relationship("FactSubLedger", back_populates="bsv_tax", overlaps="company")

    __table_args__ = (
        UniqueConstraint("company_id", "geography_id", "bsv_code", "batch_id", name="uq_bsv_batch"),
        UniqueConstraint("id", "company_id", name="uq_bsv_id_company"),

        Index("idx_bsv_company", "company_id"),
        Index("idx_bsv_batch", "company_id", "batch_id"),
        Index("idx_bsv_geography", "geography_id"),
        Index("idx_bsv_is_deleted", "company_id", "is_deleted"),
    )





class DimCustomer(Base):
    __tablename__ = "dim_customer"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=False)

    customer_name = Column(String(255), nullable=False)
    segment = Column(String(100))

    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="customers")
    batch = relationship("IngestionBatch")

    subledger_facts = relationship("FactSubLedger", back_populates="customer", overlaps="company")

    __table_args__ = (
        UniqueConstraint("company_id", "customer_name", "batch_id", name="uq_customer_name_batch"),
        UniqueConstraint("id", "company_id", name="uq_customer_id_company"),

        Index("idx_customer_company", "company_id"),
        Index("idx_customer_batch", "company_id", "batch_id"),
        Index("idx_customer_is_deleted", "company_id", "is_deleted"),
    )

# ============================================================
# CONFIG TABLES (After Company)
# ============================================================
class CompanySchemaMap(Base):
    __tablename__ = "company_schema_maps"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    file_type = Column(FileTypeEnum, nullable=False)
    source_column = Column(String(150), nullable=False)
    target_column = Column(String(150), nullable=False)
    transform = Column(SchemaTransformEnum)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="schema_maps")

    __table_args__ = (
        UniqueConstraint("company_id", "file_type", "source_column", name="uq_schema_map"),
        Index("idx_schema_map_company_file", "company_id", "file_type"),
    )


class CompanyKPIConfig(Base):
    __tablename__ = "company_kpi_configs"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    config_key = Column(String(100), nullable=False)
    config_value = Column(String(255), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="kpi_configs")

    __table_args__ = (
        UniqueConstraint("company_id", "config_key", name="uq_company_kpi_config"),
        Index("idx_kpi_config_company", "company_id"),
    )


# ============================================================
# ACCOUNT MAPPINGS & RULES
# ============================================================
class AccountMapping(Base):
    __tablename__ = "account_mappings"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    coa_id = Column(BigInteger, ForeignKey("dim_coa.id"), nullable=False)
    natural_account_key = Column(BigInteger, nullable=False)
    standard_code = Column(String(50), ForeignKey("standard_accounts.code"), nullable=True)
    confidence = Column(RATIO, nullable=False, default=1.0)
    mapped_by = Column(BigInteger, ForeignKey("users.id"))
    mapped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(AccountMappingStatusEnum, nullable=False, default="pending_review")
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="account_mappings")
    coa = relationship("DimCOA", back_populates="account_mapping")
    standard_account = relationship("StandardAccount", back_populates="account_mappings")
    mapped_user = relationship("User", back_populates="account_mappings", foreign_keys=[mapped_by])

    __table_args__ = (
        UniqueConstraint("company_id", "natural_account_key", "effective_from", name="uq_account_mapping_versioned"),
        Index("idx_account_mapping_company", "company_id"),
        Index("idx_account_mapping_coa", "coa_id"),
        Index("idx_account_mapping_natural", "natural_account_key"),
        Index("idx_account_mapping_standard", "standard_code"),
        Index("idx_account_mapping_status", "company_id", "status"),
        Index("idx_account_mapping_active", "company_id", "natural_account_key", "effective_to"),
        Index("idx_account_mapping_is_deleted", "company_id", "is_deleted"),
    )


class AccountRuleMapping(Base):
    __tablename__ = "account_rule_mappings"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    rule_key = Column(String(100), nullable=False)
    coa_id = Column(BigInteger, ForeignKey("dim_coa.id"), nullable=False)

    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")
    coa = relationship("DimCOA", back_populates="account_rule_mappings")

    __table_args__ = (
        UniqueConstraint("company_id", "rule_key", "coa_id", name="uq_rulemapping_key_coa"),
        Index("idx_rulemap_company", "company_id"),
        Index("idx_rulemap_key", "rule_key"),
        Index("idx_rulemap_is_deleted", "company_id", "is_deleted"),
    )


class AccountingRule(Base):
    __tablename__ = "accounting_rules"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    is_platform_default = Column(Boolean, nullable=False, default=False)
    metric_name = Column(String(50), nullable=False)
    entry_index = Column(Integer, nullable=False, default=1)
    side = Column(JournalSideEnum, nullable=False)
    account_rule_key = Column(String(100), nullable=False)
    movement_type = Column(String(50), nullable=False, default=MOVEMENT_DEFAULT)
    priority = Column(Integer, default=100)
    condition = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("company_id", "metric_name", "movement_type", "side", "entry_index",
                         name="uq_rule_metric_movement_side_entry"),
        Index("idx_rule_company_metric", "company_id", "metric_name"),
        Index("idx_rule_platform_default", "is_platform_default"),
        Index("idx_rule_active", "company_id", "is_active"),
        Index("idx_rule_is_deleted", "company_id", "is_deleted"),
    )


# ============================================================
# FACT TABLES
# ============================================================
class FactSubLedger(Base):
    __tablename__ = "fact_subledger"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    product_id = Column(BigInteger)
    customer_id = Column(BigInteger)
    geography_id = Column(BigInteger, ForeignKey("dim_geography.id"))
    bsv_tax_id = Column(BigInteger)
    coa_id = Column(BigInteger, nullable=True)
    standard_code = Column(String(50), ForeignKey("standard_accounts.code"), nullable=True)
    order_id = Column(String(100))
    currency_code = Column(String(3))
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=True)
    source_file_id = Column(BigInteger, ForeignKey("file_uploads.id"), nullable=False)
    source_row_number = Column(Integer, nullable=False)

    total_revenue = Column(MONEY, nullable=False, default=0)
    raw_material = Column(MONEY, nullable=False, default=0)
    direct_labor = Column(MONEY, nullable=False, default=0)
    freight = Column(MONEY, nullable=False, default=0)
    storage = Column(MONEY, nullable=False, default=0)
    packaging = Column(MONEY, nullable=False, default=0)
    indirect_labor = Column(MONEY, nullable=False, default=0)
    rent_utility = Column(MONEY, nullable=False, default=0)
    overhead = Column(MONEY, nullable=False, default=0)
    cogs = Column(MONEY, nullable=False, default=0)
    gross_profit = Column(MONEY, nullable=False, default=0)
    sga = Column(MONEY, nullable=False, default=0)

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="subledger_facts")
    geography = relationship("DimGeography", back_populates="subledger_facts")
    standard_acc = relationship("StandardAccount", back_populates="subledger_facts", foreign_keys=[standard_code])
    batch = relationship("IngestionBatch", back_populates="subledger_facts")
    source_file = relationship("FileUpload", back_populates="subledger_facts")
    sl_accounting_lines = relationship("FactSLAccounting", back_populates="subledger")

    coa = relationship("DimCOA", primaryjoin=and_(foreign(coa_id) == DimCOA.id, foreign(company_id) == DimCOA.company_id),
                       back_populates="subledger_facts", overlaps="company", viewonly=True)
    product = relationship("DimProduct", primaryjoin=and_(foreign(product_id) == DimProduct.id, foreign(company_id) == DimProduct.company_id),
                           back_populates="subledger_facts", overlaps="company,coa", viewonly=True)
    customer = relationship("DimCustomer", primaryjoin=and_(foreign(customer_id) == DimCustomer.id, foreign(company_id) == DimCustomer.company_id),
                            back_populates="subledger_facts", overlaps="company,coa,product", viewonly=True)
    bsv_tax = relationship("DimBSVTaxRate", primaryjoin=and_(foreign(bsv_tax_id) == DimBSVTaxRate.id, foreign(company_id) == DimBSVTaxRate.company_id),
                           back_populates="subledger_facts", overlaps="company,coa,product,customer", viewonly=True)

    __table_args__ = (
        UniqueConstraint("company_id", "order_id", "date", "coa_id", name="uq_fact_unique"),
        ForeignKeyConstraint(["coa_id", "company_id"], ["dim_coa.id", "dim_coa.company_id"], name="fk_fact_coa_tenant"),
        ForeignKeyConstraint(["product_id", "company_id"], ["dim_product.id", "dim_product.company_id"], name="fk_fact_product_tenant"),
        ForeignKeyConstraint(["customer_id", "company_id"], ["dim_customer.id", "dim_customer.company_id"], name="fk_fact_customer_tenant"),
        ForeignKeyConstraint(["bsv_tax_id", "company_id"], ["dim_bsv_tax_rate.id", "dim_bsv_tax_rate.company_id"], name="fk_fact_bsv_tenant"),
        Index("idx_fact_company", "company_id"),
        Index("idx_fact_company_date", "company_id", "date"),

        # New / Improved:
        Index("idx_fact_company_date_coa", "company_id", "date", "coa_id"),      # Very common filter
        Index("idx_fact_company_order", "company_id", "order_id"),               # For order-level lookups
        Index("idx_fact_company_batch", "company_id", "batch_id"),               # For batch operations
        Index("idx_fact_company_product", "company_id", "product_id", "date"),   # Product analysis
        Index("idx_fact_company_customer", "company_id", "customer_id", "date"),
    
        # Covering index for common reporting queries
        Index("idx_fact_covering_main", "company_id", "date", "standard_code", "coa_id",
                postgresql_include=['total_revenue', 'cogs', 'gross_profit', 'sga']),
        Index("idx_fact_is_deleted", "company_id", "is_deleted"),
    )


class FactSLAccounting(Base):
    __tablename__ = "fact_slaccounting"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    subledger_id = Column(BigInteger, ForeignKey("fact_subledger.id", ondelete="CASCADE"), nullable=True)
    source_type = Column(SourceTypeEnum, nullable=False, default="SUBLEDGER")

    journal_group_id = Column(String(200), nullable=False)
    coa_bsv = Column(String(50), nullable=True)
    coa_product = Column(String(50), nullable=True)

    line_type = Column(String(50), nullable=False)
    movement_type = Column(String(50), nullable=False, default=MOVEMENT_DEFAULT)
    entry_index = Column(Integer, nullable=False)
    side = Column(JournalSideEnum, nullable=False)

    account_code = Column(String(100), nullable=False)
    coa_id = Column(BigInteger, ForeignKey("dim_coa.id"), nullable=True)
    standard_code = Column(String(50), ForeignKey("standard_accounts.code"), nullable=True)

    amount = Column(MONEY, nullable=False, default=0)

    order_id = Column(String(100), nullable=True)
    date = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    product_id = Column(BigInteger, nullable=True)
    customer_id = Column(BigInteger, nullable=True)
    geography_id = Column(BigInteger, ForeignKey("dim_geography.id"), nullable=True)

    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"), nullable=True)
    source_file_id = Column(BigInteger, ForeignKey("file_uploads.id"), nullable=True)
    source_row_number = Column(Integer, nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="sl_accounting")
    subledger = relationship("FactSubLedger", back_populates="sl_accounting_lines")
    geography = relationship("DimGeography", back_populates="sl_accounting")
    batch = relationship("IngestionBatch", back_populates="sl_accounting")
    source_file = relationship("FileUpload", back_populates="sl_accounting")
    coa = relationship("DimCOA", foreign_keys=[coa_id])

    __table_args__ = (
        UniqueConstraint("company_id", "journal_group_id", "line_type", "movement_type", "side", "entry_index",
                         name="uq_fact_slaccounting_line"),
        ForeignKeyConstraint(["product_id", "company_id"], ["dim_product.id", "dim_product.company_id"], name="fk_slacc_product_tenant"),
        ForeignKeyConstraint(["customer_id", "company_id"], ["dim_customer.id", "dim_customer.company_id"], name="fk_slacc_customer_tenant"),
        Index("idx_slacc_company_journal", "company_id", "journal_group_id"),
        Index("idx_slacc_line_type", "company_id", "line_type"),
        Index("idx_slacc_account", "company_id", "account_code"),
        Index("idx_slacc_coa", "coa_id"),
        Index("idx_slacc_date", "company_id", "date"),

        Index("idx_slacc_company_date_side", "company_id", "date", "side"),
        Index("idx_slacc_company_account_date", "company_id", "account_code", "date"),
        Index("idx_slacc_company_coa_date", "company_id", "coa_id", "date"),
        Index("idx_slacc_company_batch_date", "company_id", "batch_id", "date"),
    
        # Covering index for P&L / Journal reporting
        Index("idx_slacc_covering_reporting", "company_id", "date", "line_type", "side",
            postgresql_include=['amount', 'account_code', 'movement_type']),
        Index("idx_slacc_is_deleted", "company_id", "is_deleted"),
    )


# Reuse your MONEY type
MONEY = Numeric(18, 4)


class FactSLAccountingWide(Base):
    __tablename__ = "fact_slaccounting_wide"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # =========================
    # BASIC INFO
    # =========================
    region = Column(String(100))
    geo = Column(String(50))
    country = Column(String(100))

    item_type = Column(String(100))
    customer_name = Column(String(255))

    order_id = Column(String(100))
    order_date = Column(Date)
    year = Column(Integer)
    month = Column(Integer)

    coa_bsv = Column(String(50))
    coa_product = Column(String(50))

    # =========================
    # REVENUE
    # =========================
    total_revenue = Column(MONEY)

    revenue_dr_account = Column(String(100))
    revenue_dr_amount = Column(MONEY)

    revenue_cr_account = Column(String(100))
    revenue_cr_amount = Column(MONEY)

    # =========================
    # RAW MATERIAL
    # =========================
    raw_material = Column(MONEY)

    rm_dr_account_1 = Column(String(100))
    rm_dr_amount_1 = Column(MONEY)
    rm_cr_account_1 = Column(String(100))
    rm_cr_amount_1 = Column(MONEY)

    rm_dr_account_2 = Column(String(100))
    rm_dr_amount_2 = Column(MONEY)
    rm_cr_account_2 = Column(String(100))
    rm_cr_amount_2 = Column(MONEY)

    # =========================
    # DIRECT LABOR
    # =========================
    direct_labor = Column(MONEY)

    dl_dr_account_1 = Column(String(100))
    dl_dr_amount_1 = Column(MONEY)
    dl_cr_account_1 = Column(String(100))
    dl_cr_amount_1 = Column(MONEY)

    dl_dr_account_2 = Column(String(100))
    dl_dr_amount_2 = Column(MONEY)
    dl_cr_account_2 = Column(String(100))
    dl_cr_amount_2 = Column(MONEY)

    # =========================
    # OTHER COSTS
    # =========================
    freight = Column(MONEY)
    storage = Column(MONEY)
    packaging = Column(MONEY)
    indirect_labor = Column(MONEY)
    rent_utility = Column(MONEY)
    overhead = Column(MONEY)

    # =========================
    # OVERHEAD JOURNALS
    # =========================
    overhead_dr_account_1 = Column(String(100))
    overhead_dr_amount_1 = Column(MONEY)
    overhead_cr_account_1 = Column(String(100))
    overhead_cr_amount_1 = Column(MONEY)

    overhead_dr_account_2 = Column(String(100))
    overhead_dr_amount_2 = Column(MONEY)
    overhead_cr_account_2 = Column(String(100))
    overhead_cr_amount_2 = Column(MONEY)

    overhead_dr_account_3 = Column(String(100))
    overhead_dr_amount_3 = Column(MONEY)
    overhead_cr_account_3 = Column(String(100))
    overhead_cr_amount_3 = Column(MONEY)

    # =========================
    # COGS
    # =========================
    cogs = Column(MONEY)

    cogs_dr_account = Column(String(100))
    cogs_dr_amount = Column(MONEY)
    cogs_cr_account = Column(String(100))
    cogs_cr_amount = Column(MONEY)

    # =========================
    # PROFIT
    # =========================
    gross_profit = Column(MONEY)

    # =========================
    # SG&A
    # =========================
    sga = Column(MONEY)

    sga_dr_account = Column(String(100))
    sga_dr_amount = Column(MONEY)
    sga_cr_account = Column(String(100))
    sga_cr_amount = Column(MONEY)

    # =========================
    # META
    # =========================
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))
    source_file_id = Column(BigInteger, ForeignKey("file_uploads.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =========================
    # RELATIONSHIPS (MINIMAL)
    # =========================
    company = relationship("Company")
    batch = relationship("IngestionBatch")
    source_file = relationship("FileUpload")

    # =========================
    # INDEXES (MVP OPTIMIZED)
    # =========================
    __table_args__ = (
        Index("idx_sl_wide_company", "company_id"),
        Index("idx_sl_wide_order", "company_id", "order_id"),
        Index("idx_sl_wide_date", "company_id", "order_date"),

        # Add these:
        Index("idx_sl_wide_company_date_coa", "company_id", "order_date", "coa_bsv"),
        Index("idx_sl_wide_company_customer", "company_id", "customer_name", "order_date"),
        Index("idx_sl_wide_company_revenue", "company_id", "order_date", 
            postgresql_include=['total_revenue', 'gross_profit', 'sga']),
    )

# ============================================================
# AGGREGATES
# ============================================================
class FinancialBalance(Base):
    __tablename__ = "financial_balances"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    period_end = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    period_type = Column(PeriodTypeEnum, nullable=False)
    standard_code = Column(String(50), ForeignKey("standard_accounts.code"), nullable=False)
    amount = Column(AGGREGATE, nullable=False)
    amount_reporting = Column(AGGREGATE)
    is_average = Column(Boolean, nullable=False, default=False)
    currency_code = Column(String(3))
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="financial_balances")
    standard_account = relationship("StandardAccount", back_populates="financial_balances")

    __table_args__ = (
        UniqueConstraint("company_id", "period_start", "period_type", "standard_code", "is_average", name="uq_financial_balance"),
        Index("idx_fb_company", "company_id"),
        Index("idx_fb_company_period", "company_id", "period_start"),
        Index("idx_fb_standard_code", "standard_code"),
        Index("idx_fb_is_deleted", "company_id", "is_deleted"),
    )


class FXRate(Base):
    __tablename__ = "fx_rates"

    id = Column(BigInteger, primary_key=True, index=True)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    rate = Column(RATIO, nullable=False)
    date = Column(Date, nullable=False)
    source = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "date", name="uq_fx_rate"),
        Index("idx_fx_date", "date"),
        Index("idx_fx_currency_pair", "from_currency", "to_currency"),
        Index("idx_fx_lookup", "from_currency", "to_currency", "date"),
    )


class KPIDefinition(Base):
    __tablename__ = "kpi_definitions"

    code = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    formula = Column(Text)
    formula_ast = Column(JSON)
    category = Column(String(50))
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    formula_overrides = relationship("KPIFormulaOverride", back_populates="kpi_definition")
    kpi_values = relationship("KPIValue", back_populates="kpi_definition")

    __table_args__ = (
        Index("idx_kpi_def_category", "category"),
        Index("idx_kpi_def_is_active", "is_active"),
    )


class KPIFormulaOverride(Base):
    __tablename__ = "kpi_formula_overrides"

    id = Column(BigInteger, primary_key=True, index=True)
    kpi_code = Column(String(50), ForeignKey("kpi_definitions.code"), nullable=False)
    scope_type = Column(KPIScopeTypeEnum, nullable=False)
    scope_id = Column(String(100), nullable=False)
    formula = Column(Text)
    formula_ast = Column(JSON)
    notes = Column(Text)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    kpi_definition = relationship("KPIDefinition", back_populates="formula_overrides")

    __table_args__ = (
        UniqueConstraint("kpi_code", "scope_type", "scope_id", name="uq_kpi_formula_override"),
        Index("idx_kpi_override_code", "kpi_code"),
        Index("idx_kpi_override_scope", "scope_type", "scope_id"),
    )


class KPIValue(Base):
    __tablename__ = "kpi_values"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    period_end = Column(Date, ForeignKey("dim_date.date"), nullable=False)
    period_type = Column(PeriodTypeEnum, nullable=False)
    kpi_code = Column(String(50), ForeignKey("kpi_definitions.code"), nullable=False)
    value = Column(RATIO)
    calculation_metadata = Column(JSON)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="kpi_values")
    kpi_definition = relationship("KPIDefinition", back_populates="kpi_values")

    __table_args__ = (
        UniqueConstraint("company_id", "period_start", "period_type", "kpi_code", name="uq_kpi_value"),
        Index("idx_kpi_company", "company_id"),
        Index("idx_kpi_company_period", "company_id", "period_start"),
        Index("idx_kpi_code", "kpi_code"),
        Index("idx_kpi_is_deleted", "company_id", "is_deleted"),
    )



# ----------------------------------------------------------#

# ============================================================
# DIM: ASSET VALUE (BALANCE SHEET ONLY)
# ============================================================
class DimAssetValue(Base):
    __tablename__ = "dim_asset_value"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(BigInteger, ForeignKey("file_uploads.id", ondelete="SET NULL"))
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))

    asset_name = Column(String(255), nullable=False)
    purchase_date = Column(Date, nullable=True)
    year = Column(Integer, nullable=False)

    asset_value = Column(MONEY, nullable=False)  # ✅ FIXED

    useful_life_years = Column(Integer)
    depreciation_method = Column(String(50))

    # =========================
    # ✅ BALANCE SHEET (ASSET)
    # =========================
    bs_asset_coa_id = Column(BigInteger, nullable=True)
    bs_asset_account_key = Column(BigInteger, nullable=True)

    # =========================
    # ✅ BALANCE SHEET (ACC DEP)
    # =========================
    bs_accumulated_dep_coa_id = Column(BigInteger, nullable=True)
    bs_accumulated_dep_account_key = Column(BigInteger, nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="asset_values")
    batch = relationship("IngestionBatch")
    source_file = relationship("FileUpload", back_populates="asset_values")

    __table_args__ = (
        ForeignKeyConstraint(
            ["bs_asset_coa_id", "company_id"],
            ["dim_coa.id", "dim_coa.company_id"],
            name="fk_asset_bs_asset_coa"
        ),
        ForeignKeyConstraint(
            ["bs_accumulated_dep_coa_id", "company_id"],
            ["dim_coa.id", "dim_coa.company_id"],
            name="fk_asset_bs_acc_dep_coa"
        ),
        Index("idx_asset_company", "company_id"),
        Index("idx_asset_year", "year"),
        Index("idx_asset_batch", "batch_id"),
        Index("idx_asset_file", "file_id"),
    )


# ============================================================
# FACT: YEARLY DEPRECIATION
# ============================================================
class FactAssetYearlyDepreciation(Base):
    __tablename__ = "fact_asset_yearly_depreciation"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    asset_id = Column(BigInteger, ForeignKey("dim_asset_value.id", ondelete="CASCADE"), nullable=False)

    year = Column(Integer, nullable=False)
    depreciation_amount = Column(MONEY, nullable=False)  # ✅ FIXED

    bs_asset_account_key = Column(BigInteger, nullable=True)

    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))
    file_id = Column(BigInteger, ForeignKey("file_uploads.id"))

    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")
    batch = relationship("IngestionBatch")
    source_file = relationship("FileUpload")

    __table_args__ = (
        UniqueConstraint("company_id", "asset_id", "year", name="uq_asset_yearly_dep"),
        Index("idx_asset_dep_company", "company_id"),
        Index("idx_asset_dep_year", "year"),
    )


# ============================================================
# FACT: MONTHLY DEPRECIATION
# ============================================================
class FactAssetMonthlyDepreciation(Base):
    __tablename__ = "fact_asset_monthly_depreciation"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    asset_id = Column(BigInteger, ForeignKey("dim_asset_value.id", ondelete="CASCADE"), nullable=False)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    depreciation_amount = Column(MONEY, nullable=False)  # ✅ FIXED

    pnl_depreciation_coa_id = Column(BigInteger, nullable=True)
    pnl_depreciation_account_key = Column(BigInteger, nullable=True)

    bs_accumulated_dep_coa_id = Column(BigInteger, nullable=True)
    bs_accumulated_dep_account_key = Column(BigInteger, nullable=True)

    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))
    file_id = Column(BigInteger, ForeignKey("file_uploads.id"))

    is_deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")
    batch = relationship("IngestionBatch")
    source_file = relationship("FileUpload")

    __table_args__ = (
        UniqueConstraint("company_id", "asset_id", "year", "month", name="uq_asset_monthly_dep"),
        ForeignKeyConstraint(
            ["pnl_depreciation_coa_id", "company_id"],
            ["dim_coa.id", "dim_coa.company_id"],
            name="fk_monthly_pnl_coa"
        ),
        ForeignKeyConstraint(
            ["bs_accumulated_dep_coa_id", "company_id"],
            ["dim_coa.id", "dim_coa.company_id"],
            name="fk_monthly_bs_coa"
        ),
        Index("idx_asset_month_company", "company_id"),
        Index("idx_asset_month_year", "year"),
        Index("idx_asset_month_month", "month"),
    )


# ============================================================
# FACT: JOURNAL
# ============================================================
class FactAssetJournal(Base):
    __tablename__ = "fact_asset_journal"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    asset_id = Column(BigInteger, ForeignKey("dim_asset_value.id", ondelete="CASCADE"), nullable=False)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    natural_account = Column(BigInteger, nullable=False)
    account_code = Column(String(50), nullable=False)

    dr_amount = Column(MONEY, nullable=True)  # ✅ FIXED
    cr_amount = Column(MONEY, nullable=True)  # ✅ FIXED

    bsv_code = Column(String(50), nullable=True)
    product_code = Column(String(50), default="0000")

    remarks = Column(String(255))

    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))
    file_id = Column(BigInteger, ForeignKey("file_uploads.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(dr_amount IS NOT NULL AND cr_amount IS NULL) OR (dr_amount IS NULL AND cr_amount IS NOT NULL)",
            name="check_dr_cr_only_one"
        ),
        Index("idx_journal_company", "company_id"),
        Index("idx_journal_asset", "asset_id"),
        Index("idx_journal_year_month", "year", "month"),
        Index("idx_journal_account", "natural_account"),
    )



from sqlalchemy import (
    Column, BigInteger, Integer, String, DateTime,
    UniqueConstraint, Index
)
from datetime import datetime

class FactTax(Base):
    __tablename__ = "fact_tax"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(BigInteger, ForeignKey("ingestion_batches.id"))


    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    # =========================
    # 🔹 FINANCIALS
    # =========================
    gross_profit = Column(MONEY, nullable=True)
    sga = Column(MONEY, nullable=True)
    depreciation = Column(MONEY, nullable=True)

    ebit = Column(AGGREGATE, nullable=True)
    tax = Column(MONEY, nullable=True)
    net_profit = Column(AGGREGATE, nullable=True)

    # =========================
    # 🔹 JOURNAL ENTRY
    # =========================
    dr_account = Column(String, nullable=True)
    dr_amount = Column(MONEY, nullable=True)

    cr_account = Column(String, nullable=True)
    cr_amount = Column(MONEY, nullable=True)

    bsv_code = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # =========================
    # 🔹 CONSTRAINTS + INDEXES
    # =========================
    __table_args__ = (
        # Prevent duplicate month entries
        UniqueConstraint(
            "company_id", "batch_id", "year", "month",
            name="uq_fact_tax_month"
        ),

        # Main query index (MOST IMPORTANT)
        Index(
            "idx_fact_tax_company_batch_year_month",
            "company_id", "batch_id", "year", "month"
        ),

        # Year-level reporting
        Index(
            "idx_fact_tax_company_batch_year",
            "company_id", "batch_id", "year"
        ),

        # Journal lookups (optional but useful)
        Index("idx_fact_tax_dr_account", "dr_account"),
        Index("idx_fact_tax_cr_account", "cr_account"),
    )


from sqlalchemy import (
    Column, BigInteger, String, Date, Integer,
    Boolean, ForeignKey, Index
)
# from sqlalchemy.dialects.postgresql import MONEY
from sqlalchemy.orm import relationship
from database import Base


class FactGeneralLedger(Base):
    __tablename__ = "fact_general_ledger"

    # ============================================
    # 🔥 PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # 🔥 TENANT / BATCH (UPDATED ✅ FK ADDED)
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),  # ✅ ADDED FK
        nullable=False,
        index=True
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),  # ✅ ADDED FK
        nullable=False,
        index=True
    )

    # ============================================
    # 🔥 SOURCE LINEAGE
    # ============================================
    sl_accounting_id = Column(
        BigInteger,
        ForeignKey("fact_slaccounting_wide.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    asset_journal_id = Column(
        BigInteger,
        ForeignKey("fact_asset_journal.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    fact_tax_id = Column(
        BigInteger,
        ForeignKey("fact_tax.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # ============================================
    # 🔥 BUSINESS CONTEXT
    # ============================================
    order_id = Column(String, nullable=True, index=True)
    order_date = Column(Date, nullable=True, index=True)
    month = Column(Integer, nullable=False, index=True)

    # ============================================
    # 🔥 ACCOUNT DETAILS
    # ============================================
    account = Column(String, nullable=False, index=True)
    natural_account = Column(String, nullable=True, index=True)
    account_subclass = Column(String, nullable=True, index=True)
    account_type = Column(String, nullable=True, index=True)
    sub_account = Column(String, nullable=True, index=True)

    # ============================================
    # 🔥 AMOUNTS
    # ============================================
    dr_amount = Column(MONEY, nullable=False, default=0)
    cr_amount = Column(MONEY, nullable=False, default=0)

    # ============================================
    # 🔥 FLAGS
    # ============================================
    is_closing_entry = Column(Boolean, default=False, index=True)

    # ============================================
    # 🔥 DIMENSIONS
    # ============================================
    coa_id = Column(
        BigInteger,
        ForeignKey("dim_coa.id"),
        nullable=True,
        index=True
    )

    asset_id = Column(
        BigInteger,
        ForeignKey("dim_asset_value.id"),
        nullable=True,
        index=True
    )

    # ============================================
    # 🔥 RELATIONSHIPS
    # ============================================
    # ============================================
    # 🔥 RELATIONSHIPS (OPTIONAL BUT GOOD)
    # ============================================
    company = relationship("Company")        # ✅ ADDED
    batch = relationship("IngestionBatch")   # ✅ ADDED

    sl_accounting = relationship("FactSLAccountingWide")
    asset_journal = relationship("FactAssetJournal")
    fact_tax = relationship("FactTax")
    coa = relationship("DimCOA")
    asset = relationship("DimAssetValue")

    # ============================================
    # 🔥 INDEXES (PERFORMANCE OPTIMIZED 🚀)
    # ============================================
    __table_args__ = (

        # 🔑 Core filtering (MOST IMPORTANT)
        Index("idx_gl_company_batch", "company_id", "batch_id"),

        # 📊 Reporting
        Index("idx_gl_date_account", "order_date", "account"),
        Index("idx_gl_month_account", "month", "account"),

        # 📈 P&L / BS queries
        Index("idx_gl_type_date", "account_type", "order_date"),
        Index("idx_gl_month_type", "month", "account_type"),

        # 🔁 Closing entries filtering
        Index("idx_gl_closing", "company_id", "batch_id", "is_closing_entry"),

        # 🔗 Source lineage tracking
        Index(
            "idx_gl_lineage_all",
            "sl_accounting_id",
            "asset_journal_id",
            "fact_tax_id"
        ),

        # 🔍 COA lookup
        Index("idx_gl_coa_lookup", "natural_account", "coa_id"),

        # 📦 Asset reporting
        Index("idx_gl_asset_date", "asset_id", "order_date"),
    )


# class FactGeneralLedger(Base):
#     __tablename__ = "fact_general_ledger"

#     # ============================================
#     # 🔥 PRIMARY KEY
#     # ============================================
#     id = Column(BigInteger, primary_key=True)

#     # ============================================
#     # 🔥 TENANT / BATCH
#     # ============================================
#     company_id = Column(
#         BigInteger,
#         ForeignKey("companies.id", ondelete="CASCADE"),
#         nullable=False
#     )

#     batch_id = Column(
#         BigInteger,
#         ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
#         nullable=False
#     )

#     # ============================================
#     # 🔥 SOURCE LINEAGE
#     # ============================================
#     sl_accounting_id = Column(
#         BigInteger,
#         ForeignKey("fact_slaccounting_wide.id", ondelete="CASCADE"),
#         nullable=True
#     )

#     asset_journal_id = Column(
#         BigInteger,
#         ForeignKey("fact_asset_journal.id", ondelete="CASCADE"),
#         nullable=True
#     )

#     fact_tax_id = Column(
#         BigInteger,
#         ForeignKey("fact_tax.id", ondelete="CASCADE"),
#         nullable=True
#     )

#     # ============================================
#     # 🔥 BUSINESS CONTEXT
#     # ============================================
#     order_id = Column(String, nullable=True)
#     order_date = Column(Date, nullable=True)

#     # 🔥 PERFORMANCE COLUMNS (IMPORTANT)
#     year = Column(Integer, nullable=False, index=True)
#     month = Column(Integer, nullable=False, index=True)

#     # ============================================
#     # 🔥 ACCOUNT DETAILS
#     # ============================================
#     account = Column(String, nullable=False)
#     natural_account = Column(String, nullable=True)
#     account_subclass = Column(String, nullable=True)
#     account_type = Column(String, nullable=True)
#     sub_account = Column(String, nullable=True)

#     # ============================================
#     # 🔥 AMOUNTS
#     # ============================================
#     dr_amount = Column(MONEY, nullable=False, default=0)
#     cr_amount = Column(MONEY, nullable=False, default=0)

#     # ============================================
#     # 🔥 FLAGS
#     # ============================================
#     is_closing_entry = Column(Boolean, default=False)

#     # ============================================
#     # 🔥 DIMENSIONS
#     # ============================================
#     coa_id = Column(
#         BigInteger,
#         ForeignKey("dim_coa.id"),
#         nullable=True
#     )

#     asset_id = Column(
#         BigInteger,
#         ForeignKey("dim_asset_value.id"),
#         nullable=True
#     )

#     # ============================================
#     # 🔥 RELATIONSHIPS
#     # ============================================
#     company = relationship("Company")
#     batch = relationship("IngestionBatch")

#     sl_accounting = relationship("FactSLAccountingWide")
#     asset_journal = relationship("FactAssetJournal")
#     fact_tax = relationship("FactTax")
#     coa = relationship("DimCOA")
#     asset = relationship("DimAssetValue")

#     # ============================================
#     # 🔥 INDEXES (LEAN + HIGH IMPACT)
#     # ============================================
#     __table_args__ = (

#         # 🔑 Core filter
#         Index("idx_gl_company_batch", "company_id", "batch_id"),

#         # 🔥 MAIN AGGREGATION INDEX (CRITICAL)
#         Index(
#             "idx_gl_year_agg",
#             "company_id",
#             "batch_id",
#             "is_closing_entry",
#             "account_type",
#             "year"
#         ),

#         # 🔥 COVERING INDEX (SUPER FAST SUM)
#         Index(
#             "idx_gl_covering",
#             "company_id",
#             "batch_id",
#             "is_closing_entry",
#             "account_type",
#             "year",
#             postgresql_include=["dr_amount", "cr_amount"]
#         ),

#         # 🔁 Closing filter
#         Index("idx_gl_closing", "company_id", "batch_id", "is_closing_entry"),

#         # 📊 Optional reporting
#         Index("idx_gl_month_type", "month", "account_type"),
#     )

# ----------------------------------------------------------
# class FactGLRecon(Base):
#     __tablename__ = "fact_gl_recon"

#     # ============================================
#     # 🔥 PRIMARY KEY
#     # ============================================
#     id = Column(BigInteger, primary_key=True, index=True)

#     # ============================================
#     # 🔥 TENANT / BATCH (FK ✅)
#     # ============================================
#     company_id = Column(
#         BigInteger,
#         ForeignKey("companies.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     batch_id = Column(
#         BigInteger,
#         ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     # ============================================
#     # 🔥 GROUPING KEYS
#     # ============================================
#     year = Column(Integer, nullable=False, index=True)
#     account = Column(String, nullable=False, index=True)

#     # ============================================
#     # 🔥 DERIVED ACCOUNT INFO
#     # ============================================
#     natural_account = Column(String, nullable=True, index=True)
#     account_subclass = Column(String, nullable=True)
#     account_type = Column(String, nullable=True, index=True)

#     # ============================================
#     # 🔥 AGGREGATED AMOUNTS
#     # ============================================
#     total_dr = Column(MONEY, nullable=False, default=0)
#     total_cr = Column(MONEY, nullable=False, default=0)

#     # ============================================
#     # 🔥 FINAL METRIC
#     # ============================================
#     balance = Column(MONEY, nullable=True)

#     # ============================================
#     # 🔥 DIMENSION FK
#     # ============================================
#     coa_id = Column(
#         BigInteger,
#         ForeignKey("dim_coa.id"),
#         nullable=True,
#         index=True
#     )

#     # ============================================
#     # 🔥 RELATIONSHIPS
#     # ============================================
#     company = relationship("Company")
#     batch = relationship("IngestionBatch")
#     coa = relationship("DimCOA")

#     # ============================================
#     # 🔥 INDEXES + CONSTRAINTS (UPDATED 🚀)
#     # ============================================
#     __table_args__ = (

#         # 🔒 Prevent duplicate aggregation
#         UniqueConstraint(
#             "company_id", "batch_id", "year", "account",
#             name="uq_glrecon_unique"
#         ),

#         # 🚀 Core reporting index
#         Index("idx_glrecon_main", "company_id", "batch_id", "year", "account"),

#         # 📊 Account type filtering
#         Index("idx_glrecon_type", "company_id", "batch_id", "account_type", "year"),

#         # 🔍 Natural account lookup
#         Index("idx_glrecon_natural", "company_id", "natural_account"),

#         # ⚡ Covering index (Postgres only)
#         Index(
#             "idx_glrecon_covering",
#             "company_id", "batch_id", "year",
#             postgresql_include=["total_dr", "total_cr", "balance"]
#         ),
#     )

# -----------------------------------------------------------------
# FACT GL RECON
# -------------------------------------------------------------------
# class FactGLRecon(Base):
#     __tablename__ = "fact_gl_recon"

#     # ============================================
#     # 🔥 PRIMARY KEY
#     # ============================================
#     id = Column(BigInteger, primary_key=True, index=True)

#     # ============================================
#     # 🔥 TENANT / BATCH (FK ✅)
#     # ============================================
#     company_id = Column(
#         BigInteger,
#         ForeignKey("companies.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     batch_id = Column(
#         BigInteger,
#         ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     # ============================================
#     # 🔥 GROUPING KEYS
#     # ============================================
#     year = Column(Integer, nullable=False, index=True)
#     account = Column(String, nullable=False, index=True)

#     # ============================================
#     # 🔥 DERIVED ACCOUNT INFO
#     # ============================================
#     natural_account = Column(String, nullable=True, index=True)
#     account_subclass = Column(String, nullable=True)
#     account_type = Column(String, nullable=True, index=True)

#     # ✅ MOVED HERE (as requested)
#     account_name = Column(String, nullable=True)

#     # ============================================
#     # 🔥 AGGREGATED AMOUNTS
#     # ============================================
#     total_dr = Column(MONEY, nullable=False, default=0)
#     total_cr = Column(MONEY, nullable=False, default=0)

#     # ============================================
#     # 🔥 FINAL METRIC
#     # ============================================
#     balance = Column(MONEY, nullable=True)

#     # ============================================
#     # 🔥 DIMENSION FK
#     # ============================================
#     coa_id = Column(
#         BigInteger,
#         ForeignKey("dim_coa.id"),
#         nullable=True,
#         index=True
#     )

#     # ============================================
#     # 🔥 RELATIONSHIPS
#     # ============================================
#     company = relationship("Company")
#     batch = relationship("IngestionBatch")
#     coa = relationship("DimCOA")

#     # ============================================
#     # 🔥 INDEXES + CONSTRAINTS
#     # ============================================
#     __table_args__ = (

#         UniqueConstraint(
#             "company_id", "batch_id", "year", "account",
#             name="uq_glrecon_unique"
#         ),

#         Index("idx_glrecon_main", "company_id", "batch_id", "year", "account"),

#         Index("idx_glrecon_type", "company_id", "batch_id", "account_type", "year"),

#         Index("idx_glrecon_natural", "company_id", "natural_account"),

#         Index(
#             "idx_glrecon_covering",
#             "company_id", "batch_id", "year",
#             postgresql_include=["total_dr", "total_cr", "balance"]
#         ),
#     )



# class FactGLRecon(Base):
#     __tablename__ = "fact_gl_recon"

#     # ============================================
#     # 🔥 PRIMARY KEY
#     # ============================================
#     id = Column(BigInteger, primary_key=True, index=True)

#     # ============================================
#     # 🔥 TENANT / BATCH
#     # ============================================
#     company_id = Column(
#         BigInteger,
#         ForeignKey("companies.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     batch_id = Column(
#         BigInteger,
#         ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )

#     # ============================================
#     # 🔥 GRAIN (MONTHLY)  ✅ added month
#     # ============================================
#     year = Column(Integer, nullable=False, index=True)
#     month = Column(Integer, nullable=False, index=True)  # ✅ added
#     account = Column(String, nullable=False, index=True)

#     # ============================================
#     # 🔥 DERIVED ACCOUNT INFO
#     # ============================================
#     natural_account = Column(String, nullable=True, index=True)
#     account_subclass = Column(String, nullable=True)
#     account_type = Column(String, nullable=True, index=True)
#     account_name = Column(String, nullable=True)

#     # ============================================
#     # 🔥 AGGREGATED MONTHLY VALUES
#     # ============================================
#     total_dr = Column(MONEY, nullable=False, default=0)
#     total_cr = Column(MONEY, nullable=False, default=0)

#     # ============================================
#     # 🔥 MONTH-END BALANCE
#     # ============================================
#     balance = Column(MONEY, nullable=True)

#     # ============================================
#     # 🔥 DIMENSION FK
#     # ============================================
#     coa_id = Column(
#         BigInteger,
#         ForeignKey("dim_coa.id"),
#         nullable=True,
#         index=True
#     )

#     # ============================================
#     # 🔥 RELATIONSHIPS
#     # ============================================
#     company = relationship("Company")
#     batch = relationship("IngestionBatch")
#     coa = relationship("DimCOA")

#     # ============================================
#     # 🔥 CONSTRAINTS + INDEXES
#     # ============================================
#     __table_args__ = (

#         # ✅ UPDATED UNIQUE (added month)
#         UniqueConstraint(
#             "company_id", "batch_id", "year", "month", "account",
#             name="uq_glrecon_monthly"
#         ),

#         # ✅ UPDATED INDEX (added month)
#         Index(
#             "idx_glrecon_monthly_main",
#             "company_id", "batch_id", "year", "month", "account"
#         ),

#         Index(
#             "idx_glrecon_monthly_type",
#             "company_id", "batch_id", "account_type", "year", "month"
#         ),

#         Index(
#             "idx_glrecon_monthly_natural",
#             "company_id", "natural_account"
#         ),

#         Index(
#             "idx_glrecon_monthly_covering",
#             "company_id", "batch_id", "year", "month",
#             postgresql_include=["total_dr", "total_cr", "balance"]
#         ),
#     )



class FactGLRecon(Base):
    __tablename__ = "fact_gl_recon"

    # ============================================
    # 🔥 PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # 🔥 TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ============================================
    # 🔥 GRAIN (MONTHLY)
    # ============================================
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    account = Column(String, nullable=False, index=True)

    # ============================================
    # 🔥 DERIVED ACCOUNT INFO
    # ============================================
    natural_account = Column(String, nullable=True, index=True)
    account_subclass = Column(String, nullable=True)
    account_type = Column(String, nullable=True, index=True)
    account_name = Column(String, nullable=True)

    # ============================================
    # 🔥 NEW: BSV / GEOGRAPHY / LOB
    # ============================================
    bsv_code = Column(String, nullable=True, index=True)

    geography_id = Column(
        BigInteger,
        ForeignKey("dim_geography.id"),
        nullable=True,
        index=True
    )

    country = Column(String, nullable=True, index=True)

    lob = Column(String, nullable=True, index=True)  # lob = country

    # ============================================
    # 🔥 AGGREGATED MONTHLY VALUES
    # ============================================
    total_dr = Column(MONEY, nullable=False, default=0)
    total_cr = Column(MONEY, nullable=False, default=0)

    # ============================================
    # 🔥 MONTH-END BALANCE
    # ============================================
    balance = Column(MONEY, nullable=True)

    # ============================================
    # 🔥 DIMENSION FK
    # ============================================
    coa_id = Column(
        BigInteger,
        ForeignKey("dim_coa.id"),
        nullable=True,
        index=True
    )

    # ============================================
    # 🔥 RELATIONSHIPS
    # ============================================
    company = relationship("Company")
    batch = relationship("IngestionBatch")
    coa = relationship("DimCOA")
    geography = relationship("DimGeography")

    # ============================================
    # 🔥 CONSTRAINTS + INDEXES
    # ============================================
    __table_args__ = (

        UniqueConstraint(
            "company_id", "batch_id", "year", "month", "account",
            name="uq_glrecon_monthly"
        ),

        Index(
            "idx_glrecon_monthly_main",
            "company_id", "batch_id", "year", "month", "account"
        ),

        Index(
            "idx_glrecon_monthly_type",
            "company_id", "batch_id", "account_type", "year", "month"
        ),

        Index(
            "idx_glrecon_monthly_natural",
            "company_id", "natural_account"
        ),

        # 🔥 NEW: optimized for BSV + geography lookup queries
        Index(
            "idx_glrecon_bsv_geo",
            "company_id", "batch_id", "bsv_code", "geography_id"
        ),

        # 🔥 NEW: for country / lob filtering (reporting)
        Index(
            "idx_glrecon_country_lob",
            "company_id", "batch_id", "country", "lob"
        ),

        Index(
            "idx_glrecon_monthly_covering",
            "company_id", "batch_id", "year", "month",
            postgresql_include=["total_dr", "total_cr", "balance"]
        ),
    )


# -----------------
# Before closing
# -----------------
class FactGLSummaryBeforeClosing(Base):
    __tablename__ = "fact_gl_summary_before_closing"

    id = Column(BigInteger, primary_key=True, index=True)

    # =========================
    # TENANT CONTROL
    # =========================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id"),
        nullable=False
    )

    year = Column(Integer, nullable=False)

    # =========================
    # FINANCIAL VALUES
    # =========================
    assets = Column(MONEY)
    liabilities = Column(MONEY)
    income = Column(MONEY)
    expense = Column(MONEY)
    equity = Column(MONEY)

    # =========================
    # DERIVED
    # =========================
    recon_balance = Column(MONEY)   # A - (L + I - E + SE)
    net_income = Column(MONEY)      # I - E
    sl_net_income = Column(MONEY)   # From subledger
    sl_comparison = Column(MONEY)   # diff

    created_at = Column(DateTime, default=datetime.utcnow)

    # =========================
    # CONSTRAINTS
    # =========================
    __table_args__ = (
        UniqueConstraint(
            "company_id", "batch_id", "year",
            name="uq_gl_summary_before_closing"
        ),

        Index("idx_gl_summary_company_batch", "company_id", "batch_id"),
        Index("idx_gl_summary_year", "year"),
    )


# ------------------------------------------------------------
# After closing
# ------------------------------------------------------------
class FactGLSummaryAfterClosing(Base):
    __tablename__ = "fact_gl_summary_after_closing"

    # ============================================
    # 🔥 PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # 🔥 TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ============================================
    # 🔥 GRAIN
    # ============================================
    year = Column(Integer, nullable=False, index=True)

    # ============================================
    # 🔥 METRICS
    # ============================================
    total_assets = Column(MONEY, nullable=False, default=0)
    total_liabilities = Column(MONEY, nullable=False, default=0)
    total_equity = Column(MONEY, nullable=False, default=0)

    # ============================================
    # 🔥 FINAL CHECK
    # ============================================
    difference = Column(MONEY, nullable=True)  # A - (L + SE)

    # ============================================
    # 🔥 RELATIONSHIPS
    # ============================================
    company = relationship("Company")
    batch = relationship("IngestionBatch")

    # ============================================
    # 🔥 CONSTRAINTS + INDEXES
    # ============================================
    __table_args__ = (

        UniqueConstraint(
            "company_id", "batch_id", "year",
            name="uq_gl_summary_after_closing"
        ),

        Index("idx_gl_summary_main", "company_id", "batch_id", "year"),
    )



# -----------------------------------------------------------------
# Monthly P&L Summary 
# -----------------------------------------------------------------
# class FactMonthlyPnL(Base):
#     __tablename__ = "fact_monthly_pnl"

#     # ============================================
#     # 🔥 PRIMARY KEY
#     # ============================================
#     id = Column(BigInteger, primary_key=True, index=True)

#     # ============================================
#     # 🔥 TENANT / BATCH
#     # ============================================
#     company_id = Column(
#         BigInteger,
#         ForeignKey("companies.id", ondelete="CASCADE"),
#         nullable=False
#     )

#     batch_id = Column(
#         BigInteger,
#         ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
#         nullable=False
#     )

#     # ============================================
#     # 🔥 GRAIN
#     # ============================================
#     year = Column(Integer, nullable=False)
#     month = Column(Integer, nullable=False)

#     # ============================================
#     # 🔥 METRICS (DR / CR split)
#     # ============================================
#     assets_dr = Column(MONEY, default=0)
#     assets_cr = Column(MONEY, default=0)

#     liabilities_dr = Column(MONEY, default=0)
#     liabilities_cr = Column(MONEY, default=0)

#     equity_dr = Column(MONEY, default=0)
#     equity_cr = Column(MONEY, default=0)

#     expense_dr = Column(MONEY, default=0)
#     expense_cr = Column(MONEY, default=0)

#     income_dr = Column(MONEY, default=0)
#     income_cr = Column(MONEY, default=0)

#     # ============================================
#     # 🔥 RELATIONSHIPS
#     # ============================================
#     company = relationship("Company")
#     batch = relationship("IngestionBatch")

#     # ============================================
#     # 🔥 CONSTRAINTS (Minimal & Effective)
#     # ============================================
#     __table_args__ = (

#         # Prevent duplicates (core requirement)
#         UniqueConstraint(
#             "company_id", "batch_id", "year", "month",
#             name="uq_fact_monthly_pnl"
#         ),

#         # Single reporting index (enough)
#         Index(
#             "idx_monthly_pnl_main",
#             "company_id", "batch_id", "year", "month"
#         ),
#     )

class FactMonthlyPnL(Base):
    __tablename__ = "fact_monthly_pnl"

    # ============================================
    # 🔥 PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # 🔥 TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False
    )

    # ============================================
    # 🔥 GRAIN
    # ============================================
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    # ✅ NEW COLUMN (LOB)
    lob = Column(String(50), nullable=False)

    # ============================================
    # 🔥 METRICS (DR / CR split)
    # ============================================
    assets_dr = Column(MONEY, default=0)
    assets_cr = Column(MONEY, default=0)

    liabilities_dr = Column(MONEY, default=0)
    liabilities_cr = Column(MONEY, default=0)

    equity_dr = Column(MONEY, default=0)
    equity_cr = Column(MONEY, default=0)

    expense_dr = Column(MONEY, default=0)
    expense_cr = Column(MONEY, default=0)

    income_dr = Column(MONEY, default=0)
    income_cr = Column(MONEY, default=0)

    # ============================================
    # 🔥 RELATIONSHIPS
    # ============================================
    company = relationship("Company")
    batch = relationship("IngestionBatch")

    # ============================================
    # 🔥 CONSTRAINTS
    # ============================================
    __table_args__ = (

        # ✅ UPDATED UNIQUE (includes LOB)
        UniqueConstraint(
            "company_id", "batch_id", "year", "month", "lob",
            name="uq_fact_monthly_pnl"
        ),

        # ✅ UPDATED INDEX
        Index(
            "idx_monthly_pnl_main",
            "company_id", "batch_id", "year", "month", "lob"
        ),
    )



# -------------------------------------------------------------
# Monthly Balance Sheet Summary (NEW)
# -------------------------------------------------------------
class FactMonthlyBS(Base):
    __tablename__ = "fact_monthly_bs"

    # ============================================
    # PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False
    )

    # ============================================
    # GRAIN
    # ============================================
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    lob = Column(String(50), nullable=False)

    # ============================================
    # CUMULATIVE VALUES (BALANCE SHEET)
    # ============================================
    assets_dr = Column(MONEY, default=0)
    assets_cr = Column(MONEY, default=0)

    liabilities_dr = Column(MONEY, default=0)
    liabilities_cr = Column(MONEY, default=0)

    equity_dr = Column(MONEY, default=0)
    equity_cr = Column(MONEY, default=0)

    expense_dr = Column(MONEY, default=0)
    expense_cr = Column(MONEY, default=0)

    income_dr = Column(MONEY, default=0)
    income_cr = Column(MONEY, default=0)

    # ============================================
    # RELATIONSHIPS
    # ============================================
    company = relationship("Company")
    batch = relationship("IngestionBatch")

    # ============================================
    # CONSTRAINTS
    # ============================================
    __table_args__ = (
        UniqueConstraint(
            "company_id", "batch_id", "year", "month", "lob",
            name="uq_fact_monthly_bs"
        ),
        Index(
            "idx_monthly_bs_main",
            "company_id", "batch_id", "year", "month", "lob"
        ),
    )


# --------------------------------------------------------------------------
# Yearly P&L Summary (NEW)
# --------------------------------------------------------------------------
class FactYearlyPnLReport(Base):
    __tablename__ = "fact_yearly_pnl_report"

    # ============================================
    # PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False
    )

    # ============================================
    # GRAIN
    # ============================================
    year = Column(Integer, nullable=False)
    lob = Column(String(50), nullable=False)

    # ============================================
    # 🔥 METRIC LAYER
    # ============================================
    metric_name = Column(String(100), nullable=False)
    metric_order = Column(Integer, nullable=False)  # 🔥 for UI ordering

    amount = Column(MONEY, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ============================================
    # CONSTRAINTS
    # ============================================
    __table_args__ = (
        UniqueConstraint(
            "company_id", "batch_id", "year", "lob", "metric_name",
            name="uq_yearly_pnl_metric"
        ),
        Index(
            "idx_yearly_pnl_report",
            "company_id", "batch_id", "year", "lob"
        ),
    )



class FactYearlyBSReport(Base):
    __tablename__ = "fact_yearly_bs_report"

    # ============================================
    # PRIMARY KEY
    # ============================================
    id = Column(BigInteger, primary_key=True, index=True)

    # ============================================
    # TENANT / BATCH
    # ============================================
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    batch_id = Column(
        BigInteger,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False
    )

    # ============================================
    # GRAIN
    # ============================================
    year = Column(Integer, nullable=False)
    lob = Column(String(50), nullable=False)

    # ============================================
    # DIMENSION (FOR GROUPING)
    # ============================================
    section = Column(String(50), nullable=False)
    # asset / liabilities / equity / total

    account_subclass = Column(String(100), nullable=True)

    # ============================================
    # METRIC
    # ============================================
    metric_name = Column(String(100), nullable=False)
    amount = Column(MONEY, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ============================================
    # CONSTRAINTS + INDEXES
    # ============================================
    __table_args__ = (

        # prevent duplicates
        UniqueConstraint(
            "company_id", "batch_id", "year", "lob", "metric_name",
            name="uq_yearly_bs_metric"
        ),

        # 🔥 ONLY INDEX YOU REALLY NEED (covers your API filter)
        Index(
            "idx_bs_main",
            "company_id", "batch_id", "year", "lob"
        ),
    )