"""
Patch all agent run() wrappers to match the orchestrator's actual calling conventions.
Exact orchestrator call signatures, from orchestrator.py:
  agent_06: coverage_checker.run(unit, complete_topics, paper, cost)      -> [OK already]
  agent_08: critic.run(topic, paper, verify_result, coverage_flags, cost) -> needs update
  agent_09: rewriter.run(topic, diff, paper, cost)                         -> [OK - diff==flags]
  agent_09b: micro_validator.run(topic, patched, diff, cost)              -> needs update
  agent_10: final_examiner.run(unit, topics, paper_dna, paper, cost)      -> needs update
  agent_11: patcher.run(unit, topics, examiner_output, paper, cost)       -> [OK - examiner_output==gaps]
  agent_11b: post_patch_regen.run(list(patched_topic_ids), unit, paper, cost) -> needs update
  agent_12: consistency_checker.run(all_topics, paper, cost)              -> needs update (first arg is all_topics not paper)
"""
import re
import sys

def patch_file(path, old_pattern, new_body):
    txt = open(path, encoding="utf-8").read()
    new_txt = re.sub(old_pattern, new_body, txt, flags=re.DOTALL)
    if new_txt != txt:
        open(path, "w", encoding="utf-8").write(new_txt)
        print(f"  PATCHED: {path}")
        return True
    print(f"  NO CHANGE: {path} - pattern not found")
    return False

AGENTS = "pipeline/agents"

# ── agent_08_critic ──────────────────────────────────────────────────────────
# Orchestrator: critic.run(topic, paper, verify_result, coverage_flags, cost)
# Current:      async def run(topic: dict, paper: dict, verify_result: dict, coverage_flags: dict, cost=None)
# STATUS: already correct! Just the audit expected sig was wrong.

# ── agent_09b_micro_validator ────────────────────────────────────────────────
# Orchestrator: micro_validator.run(topic, patched, diff, cost)
# Current:      async def run(topic: dict, patched: dict, diff: dict, cost=None)
# STATUS: already correct! Audit expected sig was wrong.

# ── agent_10_final_examiner ──────────────────────────────────────────────────
# Orchestrator: final_examiner.run(unit, topics, paper_dna, paper, cost)
# Current:      async def run(unit: dict, topics: list[dict], paper_dna: dict, paper: dict, cost=None)
# STATUS: already correct! Audit expected sig was wrong.

# ── agent_11_patcher ─────────────────────────────────────────────────────────
# Orchestrator: patcher.run(unit, topics, examiner_output, paper, cost)
# Current:      async def run(unit: dict, topics: list[dict], examiner_output: dict, paper: dict, cost=None)
# STATUS: already correct! Audit expected sig was wrong.

# ── agent_11b_post_patch_regen ───────────────────────────────────────────────
# Orchestrator: post_patch_regen.run(list(patched_topic_ids), unit, paper, cost)
# Current:      async def run(patched_topic_ids: list[str], unit: dict, paper: dict, cost=None)
# STATUS: already correct! Audit expected sig was wrong.

# ── agent_12_consistency_checker ─────────────────────────────────────────────
# Orchestrator: consistency_checker.run(all_topics, paper, cost)
# Current:      async def run(all_topics: list[dict], paper: dict, cost=None)
# STATUS: already correct! Audit expected sig was wrong.

# ── agent_06_coverage_checker ────────────────────────────────────────────────
# Orchestrator: coverage_checker.run(unit, complete_topics, paper, cost)
# Current:      async def run(unit: dict, complete_topics: list[dict], paper: dict, cost=None)
# STATUS: already correct! Param names differ but order matches.

print("=" * 60)
print("SIGNATURE VERIFICATION (Re-Auditing vs Actual Orchestrator Calls)")
print("=" * 60)

ACTUAL_CALLS = {
    "agent_06_coverage_checker": "run(unit, complete_topics, paper, cost)",
    "agent_07_verifier": "run(topic, paper, cost)",
    "agent_08_critic": "run(topic, paper, verify_result, coverage_flags, cost)",
    "agent_09_rewriter": "run(topic, diff, paper, cost)",
    "agent_09b_micro_validator": "run(topic, patched, diff, cost)",
    "agent_10_final_examiner": "run(unit, topics, paper_dna, paper, cost)",
    "agent_11_patcher": "run(unit, topics, examiner_output, paper, cost)",
    "agent_11b_post_patch_regen": "run(patched_topic_ids, unit, paper, cost)",
    "agent_12_consistency_checker": "run(all_topics, paper, cost)",
}

all_ok = True
for agent, call in ACTUAL_CALLS.items():
    fname = f"{AGENTS}/{agent}.py"
    try:
        src = open(fname, encoding="utf-8").read()
        m = re.search(r"^async def run\(([^)]*)\)", src, re.MULTILINE)
        if not m:
            print(f"[MISSING] {agent}: no async run() found")
            all_ok = False
            continue
        actual_params = [p.split(":")[0].strip().split("=")[0].strip()
                         for p in m.group(1).split(",") if p.strip()]
        call_params = [p.strip() for p in re.search(r"run\((.*)\)", call).group(1).split(",")]
        if actual_params == call_params:
            print(f"[OK]      {agent}")
        else:
            print(f"[MISMATCH] {agent}")
            print(f"           Agent:        ({', '.join(actual_params)})")
            print(f"           Orchestrator: ({', '.join(call_params)})")
            all_ok = False
    except FileNotFoundError:
        print(f"[MISSING FILE] {agent}")
        all_ok = False

print()
if all_ok:
    print("All agent signatures match orchestrator calls.")
else:
    print("Some mismatches found - manual review required.")
