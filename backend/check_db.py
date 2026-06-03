from supabase import create_client
import json

import os
from dotenv import load_dotenv

load_dotenv()
client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

print("=== All papers in DB ===")
result = client.from_('papers').select('upc, paper_name, pipeline_status').execute()
for p in result.data:
    print(f"  UPC={p['upc']} | name={p['paper_name']} | status={p['pipeline_status']}")

print(f"\nTotal: {len(result.data)} papers")

print("\n=== Check specific UPC 2352283601 ===")
r2 = client.from_('papers').select('*').eq('upc', '2352283601').execute()
print(f"Found: {len(r2.data)} rows")
if r2.data:
    print(json.dumps(r2.data[0], indent=2, default=str))

print("\n=== All units for 2352283601 ===")
r3 = client.from_('units').select('unit_number, unit_name, status').eq('upc', '2352283601').execute()
print(f"Found: {len(r3.data)} units")
for u in r3.data:
    print(f"  Unit {u['unit_number']}: {u['unit_name']} [{u['status']}]")
