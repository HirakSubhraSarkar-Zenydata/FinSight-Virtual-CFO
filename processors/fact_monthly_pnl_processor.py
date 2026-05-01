from sqlalchemy import text


def populate_fact_monthly_pnl(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH base AS (
            SELECT
                company_id,
                batch_id,
                EXTRACT(YEAR FROM order_date)::int AS year,
                month,
                'Australia' AS lob,  -- ✅ added
                account_type,
                dr_amount,
                cr_amount
            FROM fact_general_ledger
            WHERE
                company_id = :company_id
                AND batch_id = :batch_id
                AND is_closing_entry = false
                AND order_date IS NOT NULL
        )

        INSERT INTO fact_monthly_pnl (
            company_id,
            batch_id,
            year,
            month,
            lob,  -- ✅ added

            assets_dr, assets_cr,
            liabilities_dr, liabilities_cr,
            equity_dr, equity_cr,
            expense_dr, expense_cr,
            income_dr, income_cr
        )
        SELECT
            company_id,
            batch_id,
            year,
            month,
            lob,  -- ✅ added

            -- Assets
            SUM(CASE WHEN account_type = 'Assets' THEN dr_amount ELSE 0 END),
            SUM(CASE WHEN account_type = 'Assets' THEN cr_amount ELSE 0 END),

            -- Liabilities
            SUM(CASE WHEN account_type = 'Liabilities' THEN dr_amount ELSE 0 END),
            SUM(CASE WHEN account_type = 'Liabilities' THEN cr_amount ELSE 0 END),

            -- Equity
            SUM(CASE WHEN account_type = 'Equity' THEN dr_amount ELSE 0 END),
            SUM(CASE WHEN account_type = 'Equity' THEN cr_amount ELSE 0 END),

            -- Expense
            SUM(CASE WHEN account_type = 'Expense' THEN dr_amount ELSE 0 END),
            SUM(CASE WHEN account_type = 'Expense' THEN cr_amount ELSE 0 END),

            -- Income
            SUM(CASE WHEN account_type = 'Income' THEN dr_amount ELSE 0 END),
            SUM(CASE WHEN account_type = 'Income' THEN cr_amount ELSE 0 END)

        FROM base
        GROUP BY
            company_id,
            batch_id,
            year,
            month,
            lob  -- ✅ added

        ON CONFLICT (company_id, batch_id, year, month, lob)  -- ✅ updated
        DO UPDATE SET
            assets_dr = EXCLUDED.assets_dr,
            assets_cr = EXCLUDED.assets_cr,
            liabilities_dr = EXCLUDED.liabilities_dr,
            liabilities_cr = EXCLUDED.liabilities_cr,
            equity_dr = EXCLUDED.equity_dr,
            equity_cr = EXCLUDED.equity_cr,
            expense_dr = EXCLUDED.expense_dr,
            expense_cr = EXCLUDED.expense_cr,
            income_dr = EXCLUDED.income_dr,
            income_cr = EXCLUDED.income_cr
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()