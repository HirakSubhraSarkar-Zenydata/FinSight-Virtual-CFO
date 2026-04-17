
# import re
# from datetime import datetime
# from models import DimAssetValue, DimCOA
# from processors.utils import get_df, clean_money


# ASSET_TO_COA_MAPPING = {
#     "machinery": "equipment",
#     "equipment": "equipment",
#     "furniture": "furniture and fixtures",
#     "office furniture": "furniture and fixtures",
#     "vehicles": "vehicles",
# }


# def extract_useful_life(asset_name: str):
#     match = re.search(r"\((\d+)\s*yrs?\)", str(asset_name).lower())
#     return int(match.group(1)) if match else None


# def extract_account_key(asset_name: str):
#     match = re.search(r"\((\d+)", str(asset_name))
#     return int(match.group(1)) if match else None


# def build_coa_map(db, company_id, batch_id):
#     coa_map = {}

#     query = db.query(DimCOA).filter(
#         DimCOA.company_id == company_id,
#         DimCOA.batch_id == batch_id,
#     )

#     for coa in query.yield_per(500):
#         key = (coa.account or "").strip().lower()
#         if key:
#             coa_map[key] = {
#                 "coa_id": coa.id,
#                 "account_key": coa.account_key
#             }

#     return coa_map


# def match_coa(asset_name, coa_map):
#     asset_lower = asset_name.lower()

#     account_key = extract_account_key(asset_name)
#     if account_key:
#         for v in coa_map.values():
#             if v["account_key"] == account_key:
#                 return v

#     for keyword, mapped in ASSET_TO_COA_MAPPING.items():
#         if keyword in asset_lower and mapped in coa_map:
#             return coa_map[mapped]

#     for name, data in coa_map.items():
#         if name in asset_lower:
#             return data

#     return {"coa_id": None, "account_key": None}


# def process_asset_value(db, company_id, file, batch_id):
#     try:
#         df = get_df(file.file_path)
#         df.columns = [c.strip() for c in df.columns]

#         coa_map = build_coa_map(db, company_id, batch_id)

#         year_col = next((c for c in df.columns if str(c).isdigit()), None)

#         for _, row in df.iterrows():

#             asset_name_raw = str(row.get("Assets") or row.get("Asset Name") or "").strip()
#             if not asset_name_raw:
#                 continue

#             value = clean_money(row.get(year_col) or row.get("Cost"))
#             if value is None:
#                 continue

#             useful_life = extract_useful_life(asset_name_raw)
#             if not useful_life:
#                 try:
#                     useful_life = int(row.get("Useful Life"))
#                 except:
#                     useful_life = None

#             year = None
#             if year_col:
#                 year = int(year_col)
#             else:
#                 try:
#                     year = datetime.strptime(str(row.get("Purchase Date")), "%d-%b-%Y").year
#                 except:
#                     pass

#             asset_name = re.sub(r"\(.*?\)", "", asset_name_raw).strip()

#             coa_data = match_coa(asset_name_raw, coa_map)

#             db.add(DimAssetValue(
#                 company_id=company_id,
#                 asset_name=asset_name,
#                 year=year,
#                 asset_value=value,
#                 useful_life_years=useful_life,
#                 coa_id=coa_data["coa_id"],
#                 account_key=coa_data["account_key"],
#                 batch_id=batch_id,
#                 file_id=file.id
#             ))

#         db.commit()

#     except Exception as e:
#         db.rollback()
#         raise


import re
from datetime import datetime
from models import DimAssetValue, DimCOA
from processors.utils import get_df, clean_money


# ============================================================
# 🔹 NORMALIZER
# ============================================================
def normalize(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())


# ============================================================
# 🔹 EXTRACT USEFUL LIFE
# ============================================================
def extract_useful_life(asset_name: str):
    match = re.search(r"\((\d+)\s*yrs?\)", str(asset_name).lower())
    return int(match.group(1)) if match else None


# ============================================================
# 🔹 EXTRACT ACCOUNT KEY (PRIMARY SOURCE)
# ============================================================
def extract_account_key(asset_name: str):
    match = re.search(r"\((\d+)\)", str(asset_name))
    return int(match.group(1)) if match else None


# ============================================================
# 🔹 BUILD COA HIERARCHY
# ============================================================
def build_coa_hierarchy(db, company_id, batch_id):

    coa_lookup = {}
    ppe_accounts = []
    acc_dep_accounts = []

    query = db.query(DimCOA).filter(
        DimCOA.company_id == company_id,
        DimCOA.batch_id == batch_id,
        DimCOA.is_deleted == False
    )

    for coa in query:

        report = normalize(coa.report)
        class_name = normalize(coa.class_name)
        subclass = normalize(coa.subclass)
        subclass2 = normalize(coa.subclass2)
        account = normalize(coa.account)
        subaccount = normalize(coa.subaccount)

        # =========================
        # ✅ GLOBAL LOOKUP
        # =========================
        coa_lookup[coa.account_key] = {
            "coa_id": coa.id,
            "account_key": coa.account_key,
            "account": account,
            "subaccount": subaccount
        }

        # =========================
        # ✅ PPE (ASSET)
        # =========================
        if (
            report == "balance sheet"
            and class_name == "assets"
            and subclass == "assets"
            and subclass2 == "non-current assets"
            and "property, plant" in account
        ):
            ppe_accounts.append({
                "coa_id": coa.id,
                "account_key": coa.account_key,
                "name": subaccount
            })

        # =========================
        # ✅ ACCUMULATED DEPRECIATION (STRICT)
        # =========================
        if (
            report == "balance sheet"
            and class_name == "assets"
            and subclass == "assets"
            and subclass2 == "contra asset"
            and "accumulated depreciation" in account
        ):
            acc_dep_accounts.append({
                "coa_id": coa.id,
                "account_key": coa.account_key,
                "name": subaccount
            })

    return coa_lookup, ppe_accounts, acc_dep_accounts


# ============================================================
# 🔹 MATCH ASSET → PPE
# ============================================================
def match_asset_to_ppe(asset_name, coa_lookup, ppe_accounts):

    asset_lower = normalize(asset_name)

    # =========================
    # ✅ STEP 1: ACCOUNT KEY (HIGHEST PRIORITY)
    # =========================
    account_key = extract_account_key(asset_name)

    if account_key and account_key in coa_lookup:
        return coa_lookup[account_key]

    # =========================
    # ✅ STEP 2: HIERARCHY MATCHING
    # =========================
    for acc in ppe_accounts:
        name = acc["name"]

        # Land & Building bucket
        if "land" in name or "building" in name:
            if any(x in asset_lower for x in ["machinery", "machine", "vehicle", "truck", "car"]):
                return acc

        # Furniture bucket
        if "furniture" in name or "equipment" in name:
            if any(x in asset_lower for x in ["furniture", "desk", "chair", "equipment"]):
                return acc

    # =========================
    # ✅ STEP 3: DIRECT MATCH
    # =========================
    for acc in ppe_accounts:
        if acc["name"] in asset_lower:
            return acc

    # =========================
    # ❗ FINAL FALLBACK
    # =========================
    return ppe_accounts[0] if ppe_accounts else {
        "coa_id": None,
        "account_key": None
    }


# ============================================================
# 🔹 MATCH ACCUMULATED DEPRECIATION (NO +1)
# ============================================================
def match_accumulated_dep(asset_name, acc_dep_accounts):

    asset_lower = normalize(asset_name)

    # =========================
    # ✅ STEP 1: DIRECT MATCH
    # =========================
    for acc in acc_dep_accounts:
        if acc["name"] in asset_lower:
            return acc

    # =========================
    # ✅ STEP 2: LOGICAL MATCH
    # =========================
    for acc in acc_dep_accounts:
        name = acc["name"]

        if "machinery" in asset_lower and "machinery" in name:
            return acc

        if "vehicle" in asset_lower and "vehicle" in name:
            return acc

        if "furniture" in asset_lower and "furniture" in name:
            return acc

        if "equipment" in asset_lower and "equipment" in name:
            return acc

    # =========================
    # ❗ NO FALLBACK (STRICT)
    # =========================
    return {
        "coa_id": None,
        "account_key": None
    }


# ============================================================
# 🔹 MAIN PROCESS FUNCTION
# ============================================================
def process_asset_value(db, company_id, file, batch_id):
    try:
        df = get_df(file.file_path)
        df.columns = [c.strip() for c in df.columns]

        # ✅ Build COA hierarchy
        coa_lookup, ppe_accounts, acc_dep_accounts = build_coa_hierarchy(
            db, company_id, batch_id
        )

        # Detect year column
        year_col = next((c for c in df.columns if str(c).isdigit()), None)

        for _, row in df.iterrows():

            # =========================
            # 🔹 ASSET NAME
            # =========================
            asset_name_raw = str(
                row.get("Assets") or row.get("Asset Name") or ""
            ).strip()

            if not asset_name_raw:
                continue

            asset_name_clean = re.sub(r"\(.*?\)", "", asset_name_raw).strip()

            # =========================
            # 🔹 VALUE
            # =========================
            value = clean_money(row.get(year_col) or row.get("Cost"))
            if value is None:
                continue

            # =========================
            # 🔹 USEFUL LIFE
            # =========================
            useful_life = extract_useful_life(asset_name_raw)

            if not useful_life:
                try:
                    useful_life = int(row.get("Useful Life"))
                except:
                    useful_life = None

            # =========================
            # 🔹 YEAR
            # =========================
            year = None
            if year_col:
                year = int(year_col)
            else:
                try:
                    year = datetime.strptime(
                        str(row.get("Purchase Date")), "%d-%b-%Y"
                    ).year
                except:
                    pass

            # =========================
            # 🔹 COA MATCHING
            # =========================
            asset_coa = match_asset_to_ppe(
                asset_name_raw, coa_lookup, ppe_accounts
            )

            acc_dep_coa = match_accumulated_dep(
                asset_name_raw, acc_dep_accounts
            )

            # =========================
            # 🔹 INSERT
            # =========================
            db.add(
                DimAssetValue(
                    company_id=company_id,
                    asset_name=asset_name_clean,
                    year=year,
                    asset_value=value,
                    useful_life_years=useful_life,

                    # ✅ BS Asset
                    bs_asset_coa_id=asset_coa["coa_id"],
                    bs_asset_account_key=asset_coa["account_key"],

                    # ✅ Accumulated Depreciation
                    bs_accumulated_dep_coa_id=acc_dep_coa["coa_id"],
                    bs_accumulated_dep_account_key=acc_dep_coa["account_key"],

                    batch_id=batch_id,
                    file_id=file.id,
                )
            )

        db.commit()

    except Exception as e:
        db.rollback()
        raise e