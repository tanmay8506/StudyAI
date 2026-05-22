"""
03_paper_dna package
────────────────────
Paper DNA sub-agents for Agent 3.

Sub-agents:
  structural_dna   — Groq (Llama 3): marks/sections mechanical extraction
  topic_dna        — Claude: topic frequency, priority, recency weights
  language_dna     — Claude: examiner vocabulary and instruction words
  combination_dna  — Claude: cross-topic combination patterns (also orchestrates all 4)

Entry point for the orchestrator:
  from pipeline.agents.03_paper_dna.combination_dna import run_paper_dna_pipeline
"""

from .combination_dna import run_paper_dna_pipeline
from .language_dna import (
    build_examiner_pattern_string,
    get_combination_dna_for_topic,
    get_dominant_instruction_word,
    get_language_dna_for_topic,
    get_topic_dna_for_topic,
)

__all__ = [
    "run_paper_dna_pipeline",
    "get_language_dna_for_topic",
    "get_topic_dna_for_topic",
    "get_combination_dna_for_topic",
    "get_dominant_instruction_word",
    "build_examiner_pattern_string",
]
