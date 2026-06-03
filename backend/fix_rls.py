"""
Fix Supabase RLS policies so the frontend (anon key) can read data.
Run this once: python fix_rls.py
"""
import os, requests, json
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service-role / secret key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

# Tables that need public SELECT access for the frontend
READ_TABLES = [
    "papers",
    "units",
    "topics",
    "problem_sets",
    "formula_sheets",
    "field_flags",
    "sessions",
    "session_paper_views",
    "pyq_submissions",
    "syllabus_change_log",
]

# Build SQL: enable RLS (if not already) + add policy per table
sql_statements = []
for table in READ_TABLES:
    sql_statements.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    sql_statements.append(
        f"DROP POLICY IF EXISTS allow_public_read ON {table};"
    )
    sql_statements.append(
        f"CREATE POLICY allow_public_read ON {table} FOR SELECT TO anon USING (true);"
    )

full_sql = "\n".join(sql_statements)
print("=== SQL to execute ===")
print(full_sql)
print("=" * 40)

# Supabase exposes a /rest/v1/rpc endpoint and also allows raw SQL
# via the management API or the pg connection. Here we use the
# Supabase REST SQL execution endpoint available with the service key.
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# Try the Supabase SQL endpoint (requires service-role key)
sql_endpoint = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"

# Supabase doesn't have a built-in exec_sql by default,
# so we use the pg REST approach via the management API.
# Alternative: use psycopg2 / supabase-py to run raw SQL.

# The simplest approach: use supabase-py with the service key.
try:
    from supabase import create_client, Client
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Execute each statement separately via a stored procedure call
    # Since supabase-py doesn't expose raw SQL directly on the client,
    # we'll use the postgrest-py interface workaround.
    # 
    # Actually, supabase-py v2 has client.rpc() and client.table()
    # but not raw SQL. We need the Supabase Management API or pg driver.
    print("supabase-py loaded. Attempting via requests to Supabase SQL API...")
except ImportError:
    print("supabase-py not installed, will use requests directly")

# Use Supabase's undocumented but available pg-over-REST endpoint
# by posting to /pg/query (available in self-hosted) or via the
# Supabase Management REST API.

# The reliable approach: POST to /rest/v1/ with the SQL via the
# internal Supabase query mechanism.

# Let's try the direct approach: Supabase allows executing SQL via
# the /pg endpoint when using the service-role key.
# Actually the proper way is the Supabase Management API:
# POST https://api.supabase.com/v1/projects/{ref}/database/query

# Extract project ref from URL
project_ref = SUPABASE_URL.replace("https://", "").split(".")[0]
print(f"Project ref: {project_ref}")

# Try Management API (requires personal access token, not service key)
# Instead, let's use psycopg2 or pg8000 via the connection string

# Try pg8000 first (pure Python, no binary deps)
DB_HOST = f"db.{project_ref}.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
# The postgres password for Supabase is set during project creation
# We don't have it here. Let's try via the API approach instead.

# Best approach without direct DB password:
# Use the Supabase REST API with service role to call a PostgreSQL function
# that we first create, then drop.

# Actually, the SIMPLEST approach is to just switch the frontend to use
# the service key on the server side (in a Next.js server component/API route).
# OR we can disable RLS via the Supabase Dashboard.

# Let's try posting raw SQL via the Supabase internal REST endpoint
# The supabase API gateway accepts raw SQL via /rest/v1/rpc if a function exists.

# REAL SOLUTION: Create a stored procedure via a migration that adds the policies,
# then call it. But since we can't run raw SQL easily without the DB password,
# let's instead DISABLE RLS on these tables (simpler for dev).

# We'll use psycopg2 with the connection pooler URL format
print("\nAttempting connection via psycopg2...")
try:
    import psycopg2
    
    # Supabase connection pooler (transaction mode) - works with service key
    # The user is postgres, password is the database password
    # We'll try to get it from the SUPABASE_KEY since it might be embedded
    
    # For Supabase, you can connect directly if you know the DB password
    # Let's try the session pooler on port 5432
    conn_string = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER}"
    print(f"Connection string (without password): {conn_string}")
    print("We need the database password. Trying alternative approach...")
    
except ImportError:
    print("psycopg2 not available")

# FINAL APPROACH: Use supabase-py's internal postgrest client
# to POST raw SQL via the /pg/query endpoint
print("\nUsing direct HTTP to Supabase's internal SQL endpoint...")

# Supabase hosted projects expose this endpoint with the service role key:
# POST /rest/v1/ - for CRUD
# But for DDL we need the SQL API

# Try the Supabase SQL API via the special endpoint
for stmt in sql_statements:
    if not stmt.strip():
        continue
    
    # Use supabase's REST API to execute via rpc
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec",
        headers={**headers, "Prefer": "return=representation"},
        json={"sql": stmt},
    )
    if resp.status_code not in (200, 201, 204):
        print(f"  exec rpc failed ({resp.status_code}): {resp.text[:200]}")
    else:
        print(f"  OK: {stmt[:60]}...")

print("\nDone. If the above failed, run the SQL manually in the Supabase Dashboard SQL Editor.")
print("\nManual SQL to run in Supabase Dashboard > SQL Editor:")
print(full_sql)
