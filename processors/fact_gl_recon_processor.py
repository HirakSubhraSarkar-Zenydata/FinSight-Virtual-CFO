from sqlalchemy import text

def populate_fact_gl_recon(db, company_id: int, batch_id: int):

    db.execute(text("""
        INSERT INTO fact_gl_recon (
            company_id,
            batch_id,
            year,
            account,
            natural_account,
            account_subclass,
            account_type,
            total_dr,
            total_cr,
            coa_id,
            balance
        )
        SELECT
            gl.company_id,
            gl.batch_id,
            EXTRACT(YEAR FROM gl.order_date)::int AS year,
            gl.account,
            split_part(gl.account, '-', 3) AS natural_account,
            coa.subclass,

            CASE
                WHEN lower(coa.subclass) = 'assets' THEN 'Assets'
                WHEN lower(coa.subclass) = 'liabilities' THEN 'Liabilities'
                WHEN lower(coa.subclass) = 'sales' THEN 'Income'
                WHEN lower(coa.subclass) = 'owners equity' THEN 'Equity'
                ELSE 'Expense'
            END AS account_type,

            SUM(gl.dr_amount) AS total_dr,
            SUM(gl.cr_amount) AS total_cr,
            coa.id AS coa_id,
            NULL AS balance

        FROM fact_general_ledger gl

        LEFT JOIN dim_coa coa
            ON coa.account_key = split_part(gl.account, '-', 3)::bigint
            AND coa.company_id = gl.company_id

        WHERE
            gl.company_id = :company_id
            AND gl.batch_id = :batch_id
            AND gl.order_date IS NOT NULL
            AND gl.is_closing_entry = false

        GROUP BY
            gl.company_id,
            gl.batch_id,
            year,
            gl.account,
            natural_account,
            coa.subclass,
            coa.id

        -- 🔥 THIS IS THE KEY PART
        ON CONFLICT (company_id, batch_id, year, account)
        DO UPDATE SET
            total_dr = EXCLUDED.total_dr,
            total_cr = EXCLUDED.total_cr,
            account_subclass = EXCLUDED.account_subclass,
            account_type = EXCLUDED.account_type,
            coa_id = EXCLUDED.coa_id,
            balance = NULL  -- will recompute
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    # ============================================
    # 🔥 BALANCE UPDATE
    # ============================================
    db.execute(text("""
        UPDATE fact_gl_recon
        SET balance = ABS(total_dr - total_cr)
        WHERE
            company_id = :company_id
            AND batch_id = :batch_id
            AND account_type IN ('Expense', 'Income')
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()