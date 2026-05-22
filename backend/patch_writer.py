"""Patch the writer agent's run() method."""
import re

f = "pipeline/agents/agent_05_writer.py"
txt = open(f, encoding="utf-8").read()

pattern = r"async def run\(topic.*?\Z"
replacement = (
    "async def run(topic: dict, paper: dict, cost=None, split_mode=None) -> dict:\n"
    "    from database import queries as q\n"
    "    import asyncio\n"
    "    unit_id = topic.get(\"unit_id\")\n"
    "    unit_row: dict = {}\n"
    "    if unit_id:\n"
    "        units = q.get_units_for_paper(paper[\"upc\"])\n"
    "        unit_row = next((u for u in units if u[\"id\"] == unit_id), {})\n"
    "    mapper_output = paper.get(\"_mapper_output\") or {}\n"
    "    return await asyncio.to_thread(run_writer, topic, unit_row, paper, mapper_output)\n"
)

new_txt = re.sub(pattern, replacement, txt, flags=re.DOTALL)
if new_txt != txt:
    open(f, "w", encoding="utf-8").write(new_txt)
    print("PATCHED OK")
else:
    print("NO CHANGE - pattern not found")
    # show last 200 chars to debug
    print(repr(txt[-200:]))
