# from sqlalchemy import text


# def populate_fact_yearly_bs_report(db, company_id: int, batch_id: int):

#     db.execute(text("""
#         WITH base AS (
#             SELECT
#                 f.company_id,
#                 f.batch_id,
#                 f.year,
#                 COALESCE(g.country, 'Unknown') AS lob,

#                 f.account_type AS account_type,
#                 f.account_subclass AS subclass,
#                 f.account_name AS account_name,

#                 SUM(f.balance::numeric) AS amount

#             FROM fact_gl_recon f

#             LEFT JOIN dim_bsv_tax_rate b
#                 ON split_part(f.account, '-', 1) = b.bsv_code
#                 AND b.company_id = f.company_id

#             LEFT JOIN dim_geography g
#                 ON b.geography_id = g.id

#             WHERE f.company_id = :company_id
#               AND f.batch_id = :batch_id

#             GROUP BY
#                 f.company_id,
#                 f.batch_id,
#                 f.year,
#                 g.country,
#                 f.account_type,
#                 f.account_subclass,
#                 f.account_name
#         ),

#         agg AS (
#             SELECT
#                 company_id,
#                 batch_id,
#                 year,
#                 lob,

#                 SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'cash & cash equivalents'
#                     THEN amount ELSE 0 END) AS cash,

#                 SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'receivables'
#                     THEN amount ELSE 0 END) AS receivables,

#                 SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'property, plant & equipment'
#                     THEN amount ELSE 0 END) AS ppe,

#                 SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'accumulated depreciation'
#                     THEN amount ELSE 0 END) AS acc_dep,

#                 SUM(CASE WHEN lower(account_type) = 'liabilities' AND lower(account_name) = 'trade payables'
#                     THEN amount ELSE 0 END) AS trade_payables,

#                 SUM(CASE WHEN lower(account_type) = 'liabilities' AND lower(account_name) = 'other payables'
#                     THEN amount ELSE 0 END) AS other_payables,

#                 SUM(CASE WHEN lower(account_type) = 'equity' AND lower(account_name) = 'share capital'
#                     THEN amount ELSE 0 END) AS share_capital

#             FROM base
#             GROUP BY company_id, batch_id, year, lob
#         ),

#         pnl AS (
#             SELECT
#                 company_id,
#                 batch_id,
#                 year,
#                 lob,
#                 SUM(amount::numeric) AS net_income
#             FROM fact_yearly_pnl_report
#             WHERE metric_name = 'Net Income'
#               AND company_id = :company_id
#               AND batch_id = :batch_id
#             GROUP BY company_id, batch_id, year, lob
#         )

#         INSERT INTO fact_yearly_bs_report (
#             company_id,
#             batch_id,
#             year,
#             lob,
#             section,
#             account_subclass,
#             metric_name,
#             amount
#         )

#         -- ASSETS
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Cash & Cash Equivalents',
#                a.cash::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Receivables',
#                a.receivables::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Current Assets',
#                (a.cash + a.receivables)::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Property, Plant & Equipment',
#                a.ppe::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Accumulated Depreciation',
#                a.acc_dep::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'asset', 'asset', 'Total Assets',
#                (a.cash + a.receivables + a.ppe + a.acc_dep)::money
#         FROM agg a

#         -- LIABILITIES
#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'liabilities', 'liabilities', 'Trade Payables',
#                a.trade_payables::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'liabilities', 'liabilities', 'Other Payables',
#                a.other_payables::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'liabilities', 'liabilities', 'Current Liabilities',
#                (a.trade_payables + a.other_payables)::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'liabilities', 'liabilities', 'Total Liabilities',
#                (a.trade_payables + a.other_payables)::money
#         FROM agg a

#         -- EQUITY
#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'equity', 'equity', 'Share Capital',
#                a.share_capital::money
#         FROM agg a

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'equity', 'equity', 'Retained Earnings',
#                COALESCE(p.net_income, 0)::money
#         FROM agg a
#         LEFT JOIN pnl p
#           ON a.company_id = p.company_id
#          AND a.batch_id = p.batch_id
#          AND a.year = p.year
#          AND a.lob = p.lob

#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'equity', 'equity', 'Equity',
#                (a.share_capital + COALESCE(p.net_income,0))::money
#         FROM agg a
#         LEFT JOIN pnl p
#           ON a.company_id = p.company_id
#          AND a.batch_id = p.batch_id
#          AND a.year = p.year
#          AND a.lob = p.lob

#         -- TOTAL
#         UNION ALL
#         SELECT a.company_id, a.batch_id, a.year, a.lob,
#                'total', 'total', 'Total Liabilities & Equity',
#                ((a.trade_payables + a.other_payables)
#                 + (a.share_capital + COALESCE(p.net_income,0)))::money
#         FROM agg a
#         LEFT JOIN pnl p
#           ON a.company_id = p.company_id
#          AND a.batch_id = p.batch_id
#          AND a.year = p.year
#          AND a.lob = p.lob

#         ON CONFLICT (company_id, batch_id, year, lob, metric_name)
#         DO UPDATE SET
#             amount = EXCLUDED.amount,
#             section = EXCLUDED.section,
#             account_subclass = EXCLUDED.account_subclass
#     """), {
#         "company_id": company_id,
#         "batch_id": batch_id
#     })

#     db.commit()



# --------------------------------------------------------------------
# 
from sqlalchemy import text


def populate_fact_yearly_bs_report(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH base AS (
            SELECT
                f.company_id,
                f.batch_id,
                f.year,

                -- ✅ USE LOB FROM FACT TABLE
                COALESCE(f.lob, 'Unknown') AS lob,

                f.account_type AS account_type,
                f.account_subclass AS subclass,
                f.account_name AS account_name,

                SUM(f.balance::numeric) AS amount

            FROM fact_gl_recon f

            WHERE f.company_id = :company_id
              AND f.batch_id = :batch_id

            GROUP BY
                f.company_id,
                f.batch_id,
                f.year,
                f.lob,
                f.account_type,
                f.account_subclass,
                f.account_name
        ),

        agg AS (
            SELECT
                company_id,
                batch_id,
                year,
                lob,

                SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'cash & cash equivalents'
                    THEN amount ELSE 0 END) AS cash,

                SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'receivables'
                    THEN amount ELSE 0 END) AS receivables,

                SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'property, plant & equipment'
                    THEN amount ELSE 0 END) AS ppe,

                SUM(CASE WHEN lower(account_type) = 'assets' AND lower(account_name) = 'accumulated depreciation'
                    THEN amount ELSE 0 END) AS acc_dep,

                SUM(CASE WHEN lower(account_type) = 'liabilities' AND lower(account_name) = 'trade payables'
                    THEN amount ELSE 0 END) AS trade_payables,

                SUM(CASE WHEN lower(account_type) = 'liabilities' AND lower(account_name) = 'other payables'
                    THEN amount ELSE 0 END) AS other_payables,

                SUM(CASE WHEN lower(account_type) = 'equity' AND lower(account_name) = 'share capital'
                    THEN amount ELSE 0 END) AS share_capital

            FROM base
            GROUP BY company_id, batch_id, year, lob
        ),

        pnl AS (
            SELECT
                company_id,
                batch_id,
                year,
                lob,
                SUM(amount::numeric) AS net_income
            FROM fact_yearly_pnl_report
            WHERE metric_name = 'Net Income'
              AND company_id = :company_id
              AND batch_id = :batch_id
            GROUP BY company_id, batch_id, year, lob
        )

        INSERT INTO fact_yearly_bs_report (
            company_id,
            batch_id,
            year,
            lob,
            section,
            account_subclass,
            metric_name,
            amount
        )

        -- ASSETS
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Cash & Cash Equivalents',
               a.cash::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Receivables',
               a.receivables::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Current Assets',
               (a.cash + a.receivables)::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Property, Plant & Equipment',
               a.ppe::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Accumulated Depreciation',
               a.acc_dep::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'asset', 'asset', 'Total Assets',
               (a.cash + a.receivables + a.ppe + a.acc_dep)::money
        FROM agg a

        -- LIABILITIES
        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'liabilities', 'liabilities', 'Trade Payables',
               a.trade_payables::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'liabilities', 'liabilities', 'Other Payables',
               a.other_payables::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'liabilities', 'liabilities', 'Current Liabilities',
               (a.trade_payables + a.other_payables)::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'liabilities', 'liabilities', 'Total Liabilities',
               (a.trade_payables + a.other_payables)::money
        FROM agg a

        -- EQUITY
        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'equity', 'equity', 'Share Capital',
               a.share_capital::money
        FROM agg a

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'equity', 'equity', 'Retained Earnings',
               COALESCE(p.net_income, 0)::money
        FROM agg a
        LEFT JOIN pnl p
          ON a.company_id = p.company_id
         AND a.batch_id = p.batch_id
         AND a.year = p.year
         AND a.lob = p.lob

        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'equity', 'equity', 'Equity',
               (a.share_capital + COALESCE(p.net_income,0))::money
        FROM agg a
        LEFT JOIN pnl p
          ON a.company_id = p.company_id
         AND a.batch_id = p.batch_id
         AND a.year = p.year
         AND a.lob = p.lob

        -- TOTAL
        UNION ALL
        SELECT a.company_id, a.batch_id, a.year, a.lob,
               'total', 'total', 'Total Liabilities & Equity',
               ((a.trade_payables + a.other_payables)
                + (a.share_capital + COALESCE(p.net_income,0)))::money
        FROM agg a
        LEFT JOIN pnl p
          ON a.company_id = p.company_id
         AND a.batch_id = p.batch_id
         AND a.year = p.year
         AND a.lob = p.lob

        ON CONFLICT (company_id, batch_id, year, lob, metric_name)
        DO UPDATE SET
            amount = EXCLUDED.amount,
            section = EXCLUDED.section,
            account_subclass = EXCLUDED.account_subclass
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()