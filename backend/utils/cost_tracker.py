"""
backend/utils/cost_tracker.py
──────────────────────────────
Tracks API spend per pipeline run and enforces a kill switch.

Constants (tuned for personal use — 1-2 exams):
  MAX_API_CALLS_PER_RUN    = 120   # hard call-count limit
  MAX_ESTIMATED_COST_PER_RUN = 8.00  # USD
  WARN_COST_THRESHOLD      = 5.00  # USD — logs a warning

Usage:
    cost = CostTracker(upc)
    cost.record("writer", "gemini-2.0-flash", in_tokens=2100, out_tokens=900, latency_ms=3400)
    # raises CostKillSwitchError if limits breached

Every call is logged.  Summary printed at pipeline end.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

log = logging.getLogger("studyai.cost")

# ── Approximate cost per 1M tokens (USD) — update as pricing changes ─────────
# Gemini 2.0 Flash: free via AI Studio for personal use → $0
# Groq Llama 3:     free tier → $0
# Cerebras:         free tier → $0
# These are set to 0 but the tracker still counts calls for the call-count kill switch.
COST_PER_MTK: dict[str, dict[str, float]] = {
    "gemini-2.0-flash":  {"input": 0.0,   "output": 0.0},
    "gemini-2.5-pro":    {"input": 0.0,   "output": 0.0},   # AI Studio free tier
    "groq-llama3":       {"input": 0.0,   "output": 0.0},
    "groq-mixtral":      {"input": 0.0,   "output": 0.0},
    "cerebras":          {"input": 0.0,   "output": 0.0},
    # Add paid models here if you ever switch
}

MAX_API_CALLS_PER_RUN: int = 120
MAX_ESTIMATED_COST_PER_RUN: float = 8.00
WARN_COST_THRESHOLD: float = 5.00


class CostKillSwitchError(Exception):
    """Raised when a spending or call-count hard limit is breached."""


@dataclass
class _CallRecord:
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    success: bool
    retry_count: int
    estimated_cost: float
    timestamp: float = field(default_factory=time.time)


class CostTracker:
    def __init__(self, upc: str) -> None:
        self.upc = upc
        self._calls: list[_CallRecord] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def record(
        self,
        agent: str,
        model: str,
        in_tokens: int = 0,
        out_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        retry_count: int = 0,
    ) -> None:
        """Record one API call.  Raises CostKillSwitchError if limits breached."""
        pricing = COST_PER_MTK.get(model, {"input": 0.0, "output": 0.0})
        cost = (in_tokens * pricing["input"] + out_tokens * pricing["output"]) / 1_000_000

        rec = _CallRecord(
            agent=agent, model=model,
            input_tokens=in_tokens, output_tokens=out_tokens,
            latency_ms=latency_ms, success=success,
            retry_count=retry_count, estimated_cost=cost,
        )
        self._calls.append(rec)

        log.debug(
            "[cost] %-25s %-22s in=%5d out=%5d lat=%4.0fms cost=$%.4f",
            agent, model, in_tokens, out_tokens, latency_ms, cost,
        )

        self._check_limits()

    @property
    def total_calls(self) -> int:
        return len(self._calls)

    @property
    def total_usd(self) -> float:
        return sum(r.estimated_cost for r in self._calls)

    def summary(self) -> str:
        by_agent: dict[str, dict] = {}
        for r in self._calls:
            agg = by_agent.setdefault(r.agent, {"calls": 0, "cost": 0.0})
            agg["calls"] += 1
            agg["cost"] += r.estimated_cost

        lines = [f"Cost summary for {self.upc}"]
        lines.append(f"  Total calls : {self.total_calls}")
        lines.append(f"  Total cost  : ${self.total_usd:.4f}")
        lines.append("  By agent:")
        for agent, data in sorted(by_agent.items()):
            lines.append(f"    {agent:<30} calls={data['calls']}  cost=${data['cost']:.4f}")
        return "\n".join(lines)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_limits(self) -> None:
        if self.total_calls >= MAX_API_CALLS_PER_RUN:
            raise CostKillSwitchError(
                f"Call limit reached: {self.total_calls} calls ≥ {MAX_API_CALLS_PER_RUN}"
            )
        if self.total_usd >= MAX_ESTIMATED_COST_PER_RUN:
            raise CostKillSwitchError(
                f"Cost limit reached: ${self.total_usd:.4f} ≥ ${MAX_ESTIMATED_COST_PER_RUN}"
            )
        if self.total_usd >= WARN_COST_THRESHOLD:
            log.warning("[cost] Warning threshold hit: $%.4f for %s", self.total_usd, self.upc)