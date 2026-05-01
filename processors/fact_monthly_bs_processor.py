from sqlalchemy import text


def populate_fact_monthly_bs(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH pnl AS (
            SELECT *
            FROM fact_monthly_pnl
            WHERE
                company_id = :company_id
                AND batch_id = :batch_id
        )

        INSERT INTO fact_monthly_bs (
            company_id,
            batch_id,
            year,
            month,
            lob,

            assets_dr, assets_cr,
            liabilities_dr, liabilities_cr,
            equity_dr, equity_cr,
            expense_dr, expense_cr,
            income_dr, income_cr
        )

        SELECT
            p1.company_id,
            p1.batch_id,
            p1.year,
            p1.month,
            p1.lob,

            -- =========================
            -- FAST CUMULATIVE (SELF JOIN)
            -- =========================

            SUM(p2.assets_dr),
            SUM(p2.assets_cr),

            SUM(p2.liabilities_dr),
            SUM(p2.liabilities_cr),

            SUM(p2.equity_dr),
            SUM(p2.equity_cr),

            SUM(p2.expense_dr),
            SUM(p2.expense_cr),

            SUM(p2.income_dr),
            SUM(p2.income_cr)

        FROM pnl p1
        JOIN pnl p2
            ON p1.company_id = p2.company_id
            AND p1.batch_id = p2.batch_id
            AND p1.year = p2.year
            AND p1.lob = p2.lob
            AND p2.month <= p1.month   -- 🔥 cumulative logic

        GROUP BY
            p1.company_id,
            p1.batch_id,
            p1.year,
            p1.month,
            p1.lob

        ON CONFLICT (company_id, batch_id, year, month, lob)
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