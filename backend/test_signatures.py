import inspect
from pipeline.agents import (
    agent_01_decoder as decoder,
    agent_02_researcher as researcher,
    agent_02b_researcher_verifier as researcher_verifier,
    agent_02c_pyq_normaliser as pyq_normaliser,
    agent_04_mental_model_mapper as mapper,
    agent_05_writer as writer,
    agent_06_coverage_checker as coverage_checker,
    agent_07_verifier as verifier,
    agent_08_critic as critic,
    agent_09_rewriter as rewriter,
    agent_09b_micro_validator as micro_validator,
    agent_10_final_examiner as final_examiner,
    agent_11_patcher as patcher,
    agent_11b_post_patch_regen as post_patch_regen,
    agent_12_consistency_checker as consistency_checker,
)
from pipeline.agents.agent_03_paper_dna import (
    structural_dna,
    topic_dna,
    language_dna,
    combination_dna,
)

agents = {
    "decoder": decoder,
    "researcher": researcher,
    "researcher_verifier": researcher_verifier,
    "pyq_normaliser": pyq_normaliser,
    "structural_dna": structural_dna,
    "topic_dna": topic_dna,
    "language_dna": language_dna,
    "combination_dna": combination_dna,
    "mapper": mapper,
    "writer": writer,
    "coverage_checker": coverage_checker,
    "verifier": verifier,
    "critic": critic,
    "rewriter": rewriter,
    "micro_validator": micro_validator,
    "final_examiner": final_examiner,
    "patcher": patcher,
    "post_patch_regen": post_patch_regen,
    "consistency_checker": consistency_checker,
}

for name, module in agents.items():
    if not hasattr(module, 'run'):
        print(f"[{name}] ERROR: no 'run' function!")
        continue
        
    func = getattr(module, 'run')
    is_async = inspect.iscoroutinefunction(func)
    sig = inspect.signature(func)
    print(f"[{name}] {'async def' if is_async else 'def'} run{sig}")

# special cases
if hasattr(post_patch_regen, 'run_unit_summary'):
    is_async = inspect.iscoroutinefunction(post_patch_regen.run_unit_summary)
    sig = inspect.signature(post_patch_regen.run_unit_summary)
    print(f"[post_patch_regen] {'async def' if is_async else 'def'} run_unit_summary{sig}")
else:
    print("[post_patch_regen] ERROR: no 'run_unit_summary' function!")
