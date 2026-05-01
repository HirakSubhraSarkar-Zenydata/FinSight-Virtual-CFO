# from sqlalchemy import text


# def populate_fact_gl_summary_after_closing(db, company_id: int, batch_id: int):

#     db.execute(text("""
#         INSERT INTO fact_gl_summary_after_closing (
#             company_id,
#             batch_id,
#             year,
#             total_assets,
#             total_liabilities,
#             total_equity,
#             difference
#         )
#         SELECT
#             company_id,
#             batch_id,
#             year,

#             -- ✅ ASSETS
#             SUM(
#                 CASE
#                     WHEN account_type = 'Assets'
#                     THEN (total_dr - total_cr)
#                     ELSE 0
#                 END
#             ) AS total_assets,

#             -- ✅ LIABILITIES (NEGATED)
#             SUM(
#                 CASE
#                     WHEN account_type = 'Liabilities'
#                     THEN -(total_dr - total_cr)
#                     ELSE 0
#                 END
#             ) AS total_liabilities,

#             -- ✅ EQUITY (Income + Expense + Equity, all NEGATED)
#             SUM(
#                 CASE
#                     WHEN account_type IN ('Income', 'Expense', 'Equity')
#                     THEN -(total_dr - total_cr)
#                     ELSE 0
#                 END
#             ) AS total_equity,

#             -- ✅ FINAL CHECK: A - (L + E)
#             SUM(
#                 CASE WHEN account_type = 'Assets'
#                 THEN (total_dr - total_cr) ELSE 0 END
#             )
#             -
#             (
#                 SUM(
#                     CASE WHEN account_type = 'Liabilities'
#                     THEN -(total_dr - total_cr) ELSE 0 END
#                 )
#                 +
#                 SUM(
#                     CASE WHEN account_type IN ('Income', 'Expense', 'Equity')
#                     THEN -(total_dr - total_cr) ELSE 0 END
#                 )
#             ) AS difference

#         FROM fact_gl_recon
#         WHERE
#             company_id = :company_id
#             AND batch_id = :batch_id

#         GROUP BY
#             company_id,
#             batch_id,
#             year

#         ON CONFLICT (company_id, batch_id, year)
#         DO UPDATE SET
#             total_assets = EXCLUDED.total_assets,
#             total_liabilities = EXCLUDED.total_liabilities,
#             total_equity = EXCLUDED.total_equity,
#             difference = EXCLUDED.difference
#     """), {
#         "company_id": company_id,
#         "batch_id": batch_id
#     })

#     db.commit()



from sqlalchemy import text


def populate_fact_gl_summary_after_closing(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH base AS (
            SELECT
                company_id,
                batch_id,
                year,
                account_type,
                (total_dr - total_cr) AS dr_cr
            FROM fact_gl_recon
            WHERE
                company_id = :company_id
                AND batch_id = :batch_id
        )

        INSERT INTO fact_gl_summary_after_closing (
            company_id,
            batch_id,
            year,
            total_assets,
            total_liabilities,
            total_equity,
            difference
        )
        SELECT
            company_id,
            batch_id,
            year,

            -- ✅ ASSETS
            SUM(CASE WHEN account_type = 'Assets' THEN dr_cr ELSE 0 END),

            -- ✅ LIABILITIES
            SUM(CASE WHEN account_type = 'Liabilities' THEN -dr_cr ELSE 0 END),

            -- ✅ EQUITY
            SUM(CASE WHEN account_type IN ('Income','Expense','Equity') THEN -dr_cr ELSE 0 END),

            -- ✅ DIFFERENCE
            SUM(CASE WHEN account_type = 'Assets' THEN dr_cr ELSE 0 END)
            -
            (
                SUM(CASE WHEN account_type = 'Liabilities' THEN -dr_cr ELSE 0 END)
                +
                SUM(CASE WHEN account_type IN ('Income','Expense','Equity') THEN -dr_cr ELSE 0 END)
            )

        FROM base
        GROUP BY
            company_id,
            batch_id,
            year

        ON CONFLICT (company_id, batch_id, year)
        DO UPDATE SET
            total_assets = EXCLUDED.total_assets,
            total_liabilities = EXCLUDED.total_liabilities,
            total_equity = EXCLUDED.total_equity,
            difference = EXCLUDED.difference
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()