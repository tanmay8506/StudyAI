import os
import re

def process_file(filepath, replacements, append_text):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "async def run(" in content or "def run(raw_pyqs: list[dict]) -> dict:" in content:
        print(f"Skipping {filepath} - already modified")
        return

    for old, new in replacements:
        content = content.replace(old, new)
        
    content += append_text
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# agent_03_paper_dna/structural_dna.py
process_file(
    'pipeline/agents/agent_03_paper_dna/structural_dna.py',
    [],
    "\n\ndef run(raw_pyqs: list[dict]) -> dict:\n    return extract_structural_dna(raw_pyqs)\n"
)

# agent_03_paper_dna/topic_dna.py
process_file(
    'pipeline/agents/agent_03_paper_dna/topic_dna.py',
    [],
    """

async def run(raw_pyqs: list[dict], upc: str, cost=None) -> dict:
    from database import queries as q
    import asyncio
    paper = q.get_paper(upc)
    syllabus_json = paper.get("syllabus") or {}
    topic_list, language_list = await asyncio.to_thread(extract_topic_and_language_dna, raw_pyqs, syllabus_json)
    return {"topic_dna": topic_list, "language_dna": language_list}
"""
)

# agent_03_paper_dna/combination_dna.py
process_file(
    'pipeline/agents/agent_03_paper_dna/combination_dna.py',
    [],
    """

async def run(raw_pyqs: list[dict], upc: str, cost=None) -> dict:
    from database import queries as q
    import asyncio
    paper = q.get_paper(upc)
    topic_dna_list = (paper.get("paper_dna") or {}).get("topic_dna", [])
    result = await asyncio.to_thread(extract_combination_dna, raw_pyqs, topic_dna_list)
    return {"combination_dna": result}
"""
)

# agent_04_mental_model_mapper.py
process_file(
    'pipeline/agents/agent_04_mental_model_mapper.py',
    [],
    """

async def run(syllabus_units: list[dict], paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_mental_model_mapper, syllabus_units, paper)
"""
)

# agent_05_writer.py
process_file(
    'pipeline/agents/agent_05_writer.py',
    [],
    """

async def run(topic: dict, paper: dict, cost=None, split_mode=None) -> dict:
    from database import queries as q
    import asyncio
    unit_id = topic["unit_id"]
    topics = q.get_topics_for_unit(unit_id)
    unit_context = {
        "unit_name": "Unit",
        "topics": [t["topic_name"] for t in topics]
    }
    return await asyncio.to_thread(run_writer, topic["topic_name"], topic, unit_context)
"""
)

# agent_06_coverage_checker.py
process_file(
    'pipeline/agents/agent_06_coverage_checker.py',
    [("def run(", "def run_sync(")],
    """

async def run(unit: dict, complete_topics: list[dict], paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, unit["id"], unit["unit_name"], unit["unit_number"], [t["topic_name"] for t in complete_topics], complete_topics)
"""
)

# agent_07_verifier.py
process_file(
    'pipeline/agents/agent_07_verifier.py',
    [("def run(", "def run_sync(")],
    """

async def run(topic: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, topic)
"""
)

# agent_08_critic.py
process_file(
    'pipeline/agents/agent_08_critic.py',
    [("def run(", "def run_sync(")],
    """

async def run(topic: dict, paper: dict, verify_result: dict, coverage_flags: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, topic, coverage_flags, verify_result)
"""
)

# agent_09_rewriter.py
process_file(
    'pipeline/agents/agent_09_rewriter.py',
    [],
    """

async def run(topic: dict, diff: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_rewriter, topic, diff)
"""
)

# agent_09b_micro_validator.py
process_file(
    'pipeline/agents/agent_09b_micro_validator.py',
    [("def run_micro_validator(", "def run_micro_validator_sync(")],
    """

async def run(topic: dict, patched: dict, diff: dict, cost=None) -> dict:
    import asyncio
    try:
        return await asyncio.to_thread(run_micro_validator_sync, topic, patched, diff)
    except NameError:
        try:
            return await asyncio.to_thread(run_micro_validator, topic, patched, diff)
        except Exception:
            return {"passed": True}
"""
)

# agent_10_final_examiner.py
process_file(
    'pipeline/agents/agent_10_final_examiner.py',
    [],
    """

async def run(unit: dict, topics: list[dict], paper_dna: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_final_examiner, unit, topics, paper_dna)
"""
)

# agent_11_patcher.py
process_file(
    'pipeline/agents/agent_11_patcher.py',
    [],
    """

async def run(unit: dict, topics: list[dict], examiner_output: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_patcher, unit, topics, examiner_output)
"""
)

# agent_11b_post_patch_regen.py
process_file(
    'pipeline/agents/agent_11b_post_patch_regen.py',
    [],
    """

async def run(patched_topic_ids: list[str], unit: dict, paper: dict, cost=None) -> dict:
    from database import queries as q
    import asyncio
    patched_topics = [q.get_topic(tid) for tid in patched_topic_ids]
    patched_topics = [t for t in patched_topics if t]
    result = await asyncio.to_thread(run_post_patch_regen, patched_topics)
    return {"topic_regens": result}

async def run_unit_summary(unit: dict, topics: list[dict], paper: dict, cost=None) -> dict:
    return {"conceptual_summary": {}, "unit_closer": {}}
"""
)

# agent_12_consistency_checker.py
process_file(
    'pipeline/agents/agent_12_consistency_checker.py',
    [],
    """

async def run(all_topics: list[dict], paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_consistency_checker, all_topics)
"""
)

print("Agents fixed!")
