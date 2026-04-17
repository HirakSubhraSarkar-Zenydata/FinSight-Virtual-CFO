import pandas as pd
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "File Storage"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_df(file_path: str):
    signed = supabase.storage.from_(BUCKET_NAME).create_signed_url(
        file_path,
        expires_in=3600
    )
    url = signed["signedURL"]
    return pd.read_csv(url)


def clean_money(val):
    if pd.isna(val):
        return 0
    return float(str(val).replace("$", "").replace(",", "").strip())