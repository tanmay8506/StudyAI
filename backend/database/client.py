"""
backend/database/client.py
──────────────────────────
Supabase client singleton.  Import `db` from here everywhere.
Never create a second client — one connection, shared across the whole process.

Usage:
    from database.client import db
    result = db.table("papers").select("*").eq("upc", upc).execute()
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()  # reads backend/.env

_SUPABASE_URL: str = os.environ["SUPABASE_URL"]
_SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]  # service-role key (bypasses RLS)

db: Client = create_client(_SUPABASE_URL, _SUPABASE_KEY)