from supabase import create_client
import json

import os
from dotenv import load_dotenv

load_dotenv()
client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

print("=== Completed Topics in DB ===")
result = client.from_('topics').select('id, topic_name, status, content').eq('upc', '2352283601').execute()

completed = [t for t in result.data if t['content'] is not None]
print(f"Total topics: {len(result.data)}")
print(f"Topics with content: {len(completed)}")

for t in completed:
    print(f"\n- Topic: {t['topic_name']} ({t['status']})")
    content = t['content']
    print(f"  Content Keys: {list(content.keys())}")
    print("  Definition:")
    print(f"    {content.get('definition', '')[:200]}...")
