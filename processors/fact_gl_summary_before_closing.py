from sqlalchemy import text

def populate_gl_summary_before_closing(db, company_id: int, batch_id: int):

    # ❌ DO NOT DELETE (you want history)
    # Instead UPSERT

    db.execute(text("""

    INSERT INTO fact_gl_summary_before_closing (
        company_id,
        batch_id,
        year,
        assets,
        liabilities,
        income,
        expense,
        equity,
        recon_balance,
        net_income,
        sl_net_income,
        sl_comparison
    )

    SELECT
        company_id,
        batch_id,
        year,

        -- =========================
        -- ASSETS
        -- =========================
        SUM(CASE WHEN account_type = 'Assets'
            THEN (total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- LIABILITIES
        -- =========================
        SUM(CASE WHEN account_type = 'Liabilities'
            THEN -(total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- INCOME
        -- =========================
        SUM(CASE WHEN account_type = 'Income'
            THEN -(total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- EXPENSE
        -- =========================
        SUM(CASE WHEN account_type = 'Expense'
            THEN (total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- EQUITY
        -- =========================
        SUM(CASE WHEN account_type = 'Equity'
            THEN -(total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- RECON BALANCE
        -- =========================
        SUM(CASE WHEN account_type = 'Assets'
            THEN (total_dr - total_cr) ELSE 0 END)
        -
        (
            SUM(CASE WHEN account_type = 'Liabilities'
                THEN -(total_dr - total_cr) ELSE 0 END)
            +
            SUM(CASE WHEN account_type = 'Income'
                THEN -(total_dr - total_cr) ELSE 0 END)
            -
            SUM(CASE WHEN account_type = 'Expense'
                THEN (total_dr - total_cr) ELSE 0 END)
            +
            SUM(CASE WHEN account_type = 'Equity'
                THEN -(total_dr - total_cr) ELSE 0 END)
        ),

        -- =========================
        -- NET INCOME
        -- =========================
        SUM(CASE WHEN account_type = 'Income'
            THEN -(total_dr - total_cr) ELSE 0 END)
        -
        SUM(CASE WHEN account_type = 'Expense'
            THEN (total_dr - total_cr) ELSE 0 END),

        -- =========================
        -- SL NET INCOME (JOIN)
        -- =========================
        (
            SELECT COALESCE(SUM(gross_profit - sga), 0)
            FROM fact_slaccounting_wide sl
            WHERE sl.company_id = fr.company_id
            AND sl.batch_id = fr.batch_id
            AND sl.year = fr.year
        ),

        -- =========================
        -- SL COMPARISON
        -- =========================
        (
            (
                SUM(CASE WHEN account_type = 'Income'
                    THEN -(total_dr - total_cr) ELSE 0 END)
                -
                SUM(CASE WHEN account_type = 'Expense'
                    THEN (total_dr - total_cr) ELSE 0 END)
            )
            -
            (
                SELECT COALESCE(SUM(gross_profit - sga), 0)
                FROM fact_slaccounting_wide sl
                WHERE sl.company_id = fr.company_id
                AND sl.batch_id = fr.batch_id
                AND sl.year = fr.year
            )
        )

    FROM fact_gl_recon fr
    WHERE company_id = :company_id
      AND batch_id = :batch_id

    GROUP BY company_id, batch_id, year

    ON CONFLICT (company_id, batch_id, year)
    DO UPDATE SET
        assets = EXCLUDED.assets,
        liabilities = EXCLUDED.liabilities,
        income = EXCLUDED.income,
        expense = EXCLUDED.expense,
        equity = EXCLUDED.equity,
        recon_balance = EXCLUDED.recon_balance,
        net_income = EXCLUDED.net_income,
        sl_net_income = EXCLUDED.sl_net_income,
        sl_comparison = EXCLUDED.sl_comparison

    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()