# from sqlalchemy import text


# def populate_fact_gl_recon(db, company_id: int, batch_id: int):

#     db.execute(text("""
#         WITH gl_base AS (
#             SELECT
#                 gl.company_id,
#                 gl.batch_id,
#                 EXTRACT(YEAR FROM gl.order_date)::int AS year,
#                 gl.account,
#                 split_part(gl.account, '-', 3)::bigint AS natural_account_key,
#                 SUM(gl.dr_amount) AS total_dr,
#                 SUM(gl.cr_amount) AS total_cr
#             FROM fact_general_ledger gl
#             WHERE
#                 gl.company_id = :company_id
#                 AND gl.batch_id = :batch_id
#                 AND gl.order_date IS NOT NULL
#                 AND gl.is_closing_entry = false
#             GROUP BY
#                 gl.company_id,
#                 gl.batch_id,
#                 year,
#                 gl.account
#         )

#         INSERT INTO fact_gl_recon (
#             company_id,
#             batch_id,
#             year,
#             account,
#             natural_account,
#             account_subclass,
#             account_type,
#             account_name,
#             total_dr,
#             total_cr,
#             coa_id,
#             balance
#         )
#         SELECT
#             g.company_id,
#             g.batch_id,
#             g.year,
#             g.account,
#             g.natural_account_key::text,
#             coa.subclass,

#             CASE
#                 WHEN lower(coa.subclass) = 'assets' THEN 'Assets'
#                 WHEN lower(coa.subclass) = 'liabilities' THEN 'Liabilities'
#                 WHEN lower(coa.subclass) = 'sales' THEN 'Income'
#                 WHEN lower(coa.subclass) = 'owners equity' THEN 'Equity'
#                 ELSE 'Expense'
#             END AS account_type,

#             coa.account AS account_name,

#             g.total_dr,
#             g.total_cr,
#             coa.id,
#             ABS(g.total_dr - g.total_cr) AS balance

#         FROM gl_base g

#         LEFT JOIN dim_coa coa
#             ON coa.account_key = g.natural_account_key
#             AND coa.company_id = g.company_id

#         ON CONFLICT (company_id, batch_id, year, account)
#         DO UPDATE SET
#             total_dr = EXCLUDED.total_dr,
#             total_cr = EXCLUDED.total_cr,
#             account_subclass = EXCLUDED.account_subclass,
#             account_type = EXCLUDED.account_type,
#             account_name = EXCLUDED.account_name,
#             coa_id = EXCLUDED.coa_id,
#             balance = EXCLUDED.balance
#     """), {
#         "company_id": company_id,
#         "batch_id": batch_id
#     })

#     db.commit()



from sqlalchemy import text


def populate_fact_gl_recon(db, company_id: int, batch_id: int):

    db.execute(text("""
        WITH gl_base AS (
            SELECT
                gl.company_id,
                gl.batch_id,
                EXTRACT(YEAR FROM gl.order_date)::int AS year,
                EXTRACT(MONTH FROM gl.order_date)::int AS month,
                gl.account,
                split_part(gl.account, '-', 3)::bigint AS natural_account_key,
                SUM(gl.dr_amount) AS total_dr,
                SUM(gl.cr_amount) AS total_cr
            FROM fact_general_ledger gl
            WHERE
                gl.company_id = :company_id
                AND gl.batch_id = :batch_id
                AND gl.order_date IS NOT NULL
                AND gl.is_closing_entry = false
            GROUP BY
                gl.company_id,
                gl.batch_id,
                EXTRACT(YEAR FROM gl.order_date),
                EXTRACT(MONTH FROM gl.order_date),
                gl.account
        )

        INSERT INTO fact_gl_recon (
            company_id,
            batch_id,
            year,
            month,
            account,
            natural_account,
            account_subclass,
            account_type,
            account_name,
            total_dr,
            total_cr,
            coa_id,
            balance
        )
        SELECT
            g.company_id,
            g.batch_id,
            g.year,
            g.month,
            g.account,
            g.natural_account_key::text,
            coa.subclass,

            CASE
                WHEN lower(coa.subclass) = 'assets' THEN 'Assets'
                WHEN lower(coa.subclass) = 'liabilities' THEN 'Liabilities'
                WHEN lower(coa.subclass) = 'sales' THEN 'Income'
                WHEN lower(coa.subclass) = 'owners equity' THEN 'Equity'
                ELSE 'Expense'
            END AS account_type,

            coa.account AS account_name,

            g.total_dr,
            g.total_cr,
            coa.id,

            -- keep your logic unchanged
            ABS(g.total_dr - g.total_cr) AS balance

        FROM gl_base g

        LEFT JOIN dim_coa coa
            ON coa.account_key = g.natural_account_key
            AND coa.company_id = g.company_id

        ON CONFLICT (company_id, batch_id, year, month, account)
        DO UPDATE SET
            total_dr = EXCLUDED.total_dr,
            total_cr = EXCLUDED.total_cr,
            account_subclass = EXCLUDED.account_subclass,
            account_type = EXCLUDED.account_type,
            account_name = EXCLUDED.account_name,
            coa_id = EXCLUDED.coa_id,
            balance = EXCLUDED.balance
    """), {
        "company_id": company_id,
        "batch_id": batch_id
    })

    db.commit()