from sqlalchemy import text


def populate_fact_yearly_pnl_report(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH base AS (
            SELECT
                f.company_id,
                f.batch_id,
                f.year,

                -- 🔥 LOB (Country from Geography)
                COALESCE(f.lob, 'Unknown') AS lob,

                LOWER(f.account_subclass) AS subclass,

                SUM(f.balance::numeric) AS amount

            FROM fact_gl_recon f

            WHERE f.company_id = :company_id
              AND f.batch_id = :batch_id

            GROUP BY
                f.company_id,
                f.batch_id,
                f.year,
                f.lob,
                LOWER(f.account_subclass)
        ),

        agg AS (
            SELECT
                company_id,
                batch_id,
                year,
                lob,

                -- 🔥 METRICS
                SUM(CASE WHEN subclass = 'sales'
                    THEN amount ELSE 0 END) AS sales,

                SUM(CASE WHEN subclass = 'cost of sales'
                    THEN amount ELSE 0 END) AS cos,

                SUM(CASE WHEN subclass = 'depreciation & amortization'
                    THEN amount ELSE 0 END) AS depreciation,

                SUM(CASE WHEN subclass = 'operating expenses'
                    THEN amount ELSE 0 END) AS opex,

                SUM(CASE WHEN subclass = 'taxation'
                    THEN amount ELSE 0 END) AS tax

            FROM base
            GROUP BY company_id, batch_id, year, lob
        )

        INSERT INTO fact_yearly_pnl_report (
            company_id,
            batch_id,
            year,
            lob,
            metric_name,
            metric_order,
            amount
        )

        -- SALES
        SELECT company_id, batch_id, year, lob,
               'Sales', 1,
               sales::money
        FROM agg

        UNION ALL

        -- COST OF SALES
        SELECT company_id, batch_id, year, lob,
               'Cost of Sales', 2,
               cos::money
        FROM agg

        UNION ALL

        -- GROSS INCOME
        SELECT company_id, batch_id, year, lob,
               'Gross Income', 3,
               (sales - cos)::money
        FROM agg

        UNION ALL

        -- DEPRECIATION
        SELECT company_id, batch_id, year, lob,
               'Depreciation and Amortization', 4,
               depreciation::money
        FROM agg

        UNION ALL

        -- OPERATING EXPENSES
        SELECT company_id, batch_id, year, lob,
               'Operating Expenses', 5,
               opex::money
        FROM agg

        UNION ALL

        -- EBIT
        SELECT company_id, batch_id, year, lob,
               'EBIT', 6,
               (sales - cos - depreciation - opex)::money
        FROM agg

        UNION ALL

        -- TAXATION
        SELECT company_id, batch_id, year, lob,
               'Taxation', 7,
               tax::money
        FROM agg

        UNION ALL

        -- NET INCOME
        SELECT company_id, batch_id, year, lob,
               'Net Income', 8,
               (sales - cos - depreciation - opex - tax)::money
        FROM agg

        ON CONFLICT (company_id, batch_id, year, lob, metric_name)
        DO UPDATE SET
            amount = EXCLUDED.amount,
            metric_order = EXCLUDED.metric_order
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()