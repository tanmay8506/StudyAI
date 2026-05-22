"""
cycle_detector.py
─────────────────
Detects and resolves cycles in the prerequisite dependency graph before
the Mapper attempts to produce a study sequence.

Called by: 04_mental_model_mapper.py
Input:     List of (topic_name, prerequisite_topic_name | None) tuples
Output:    CycleReport — detected cycles + recommended entry points + safe graph

A cycle in the dependency graph means the Mapper would produce an infinite
sequence. Every cycle must be broken before sequencing begins.

Resolution strategy:
  - Find all strongly connected components (Tarjan's SCC algorithm).
  - For each SCC with more than one node: choose the entry point by lowest
    dependency_depth heuristic (most foundational topic in the cycle).
  - Break the cycle by removing the edge INTO the chosen entry point.
  - Report every cycle and every edge removal so the Mapper can add the
    mutual dependency note to the affected concept_bridge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TopicNode:
    """Represents one topic in the dependency graph."""
    name: str
    prerequisite: Optional[str]  # None = root node (no prerequisite)


@dataclass
class CycleWarning:
    """A single detected cycle and how it was resolved."""
    cycle_topics: list[str]          # all topics forming the cycle
    entry_point: str                  # topic chosen as cycle entry
    removed_edge_from: str            # which prerequisite edge was cut
    removed_edge_to: str              # the topic that no longer has a prerequisite
    resolution_note: str              # human-readable note for concept_bridge injection


@dataclass
class CycleReport:
    """Complete cycle detection result."""
    has_cycles: bool
    warnings: list[CycleWarning]
    safe_graph: list[TopicNode]       # graph with all cycle edges removed
    removed_edges: list[tuple[str, str]]  # (from_topic, to_topic) pairs removed


# ──────────────────────────────────────────────────────────────────────────────
# Tarjan's SCC algorithm
# ──────────────────────────────────────────────────────────────────────────────

class _TarjanSCC:
    """
    Tarjan's strongly connected components algorithm.
    Finds all SCCs in O(V + E). An SCC with more than one node is a cycle.
    """

    def __init__(self, adjacency: dict[str, list[str]]):
        self._adj = adjacency
        self._index_counter = [0]
        self._stack: list[str] = []
        self._lowlink: dict[str, int] = {}
        self._index: dict[str, int] = {}
        self._on_stack: dict[str, bool] = {}
        self._sccs: list[list[str]] = []

    def run(self) -> list[list[str]]:
        for node in self._adj:
            if node not in self._index:
                self._strongconnect(node)
        return self._sccs

    def _strongconnect(self, v: str) -> None:
        self._index[v] = self._index_counter[0]
        self._lowlink[v] = self._index_counter[0]
        self._index_counter[0] += 1
        self._stack.append(v)
        self._on_stack[v] = True

        for w in self._adj.get(v, []):
            if w not in self._index:
                self._strongconnect(w)
                self._lowlink[v] = min(self._lowlink[v], self._lowlink[w])
            elif self._on_stack.get(w, False):
                self._lowlink[v] = min(self._lowlink[v], self._index[w])

        if self._lowlink[v] == self._index[v]:
            scc: list[str] = []
            while True:
                w = self._stack.pop()
                self._on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            self._sccs.append(scc)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def detect_and_resolve_cycles(topics: list[TopicNode]) -> CycleReport:
    """
    Detect all prerequisite cycles and return a safe (acyclic) graph.

    Args:
        topics: Full list of TopicNode objects from the syllabus.

    Returns:
        CycleReport with:
          - has_cycles: whether any cycles were found
          - warnings:   one CycleWarning per cycle detected
          - safe_graph: topics with cycle edges removed (Mapper uses this)
          - removed_edges: list of (source, target) edges that were cut

    Usage:
        nodes = [TopicNode("Uniform Convergence", "Pointwise Convergence"), ...]
        report = detect_and_resolve_cycles(nodes)
        if report.has_cycles:
            # log report.warnings, then use report.safe_graph
    """
    topic_map: dict[str, TopicNode] = {t.name: t for t in topics}
    all_names: set[str] = set(topic_map.keys())

    # Build adjacency list: prerequisite → dependent (direction of dependency)
    adjacency: dict[str, list[str]] = {name: [] for name in all_names}
    for topic in topics:
        if topic.prerequisite and topic.prerequisite in all_names:
            adjacency[topic.prerequisite].append(topic.name)
        elif topic.prerequisite and topic.prerequisite not in all_names:
            logger.warning(
                "Topic '%s' references prerequisite '%s' which is not in the syllabus. "
                "Treating as no prerequisite.",
                topic.name, topic.prerequisite
            )

    # Run Tarjan's SCC
    scc_finder = _TarjanSCC(adjacency)
    sccs = scc_finder.run()
    cyclic_sccs = [scc for scc in sccs if len(scc) > 1]

    if not cyclic_sccs:
        logger.info("Cycle detection: no cycles found in dependency graph.")
        return CycleReport(
            has_cycles=False,
            warnings=[],
            safe_graph=list(topics),
            removed_edges=[]
        )

    logger.warning(
        "Cycle detection: found %d cycle(s). Resolving before Mapper runs.",
        len(cyclic_sccs)
    )

    warnings: list[CycleWarning] = []
    removed_edges: list[tuple[str, str]] = []

    # Work on a mutable copy of prerequisites
    safe_prerequisites: dict[str, Optional[str]] = {
        t.name: t.prerequisite for t in topics
    }

    for scc in cyclic_sccs:
        entry_point = _choose_entry_point(scc, safe_prerequisites)

        # Find and remove the edge pointing INTO the entry point from within the cycle
        # (the edge that closes the loop)
        cycle_members = set(scc)
        removed_from: Optional[str] = None
        for member in scc:
            if member != entry_point:
                if safe_prerequisites.get(member) == entry_point:
                    removed_from = member
                    safe_prerequisites[member] = None
                    removed_edges.append((entry_point, member))
                    break

        # If we couldn't find the obvious incoming edge, just remove one edge in the cycle
        if removed_from is None:
            for member in scc:
                if member != entry_point and safe_prerequisites.get(member) in cycle_members:
                    removed_from = member
                    old_prereq = safe_prerequisites[member]
                    safe_prerequisites[member] = None
                    if old_prereq:
                        removed_edges.append((old_prereq, member))
                    break

        resolution_note = (
            f"Mutual dependency exists — introduce '{entry_point}' first with an intuitive "
            f"definition, then return for formal rigour after adjacent topics in this cycle "
            f"({', '.join(t for t in scc if t != entry_point)}) are covered."
        )

        warnings.append(CycleWarning(
            cycle_topics=scc,
            entry_point=entry_point,
            removed_edge_from=entry_point,
            removed_edge_to=removed_from or "unknown",
            resolution_note=resolution_note
        ))

        logger.info(
            "Cycle resolved: %s | Entry point: '%s' | Edge removed: '%s' → '%s'",
            scc, entry_point,
            entry_point, removed_from
        )

    # Rebuild safe graph
    safe_graph = [
        TopicNode(name=t.name, prerequisite=safe_prerequisites[t.name])
        for t in topics
    ]

    return CycleReport(
        has_cycles=True,
        warnings=warnings,
        safe_graph=safe_graph,
        removed_edges=removed_edges
    )


def _choose_entry_point(cycle: list[str], prerequisites: dict[str, Optional[str]]) -> str:
    """
    Choose the most foundational topic in a cycle as the entry point.

    Heuristic (in order):
    1. The topic whose prerequisite is OUTSIDE the cycle (most self-contained within the cycle).
    2. If all prerequisites are inside the cycle: the topic with the most generic/shortest name
       (proxy for most foundational concept).
    3. Fallback: first alphabetically.
    """
    cycle_set = set(cycle)

    # Heuristic 1: find the topic whose prerequisite is outside the cycle
    for topic in cycle:
        prereq = prerequisites.get(topic)
        if prereq is None or prereq not in cycle_set:
            return topic

    # Heuristic 2: shortest name as proxy for most foundational concept
    return min(cycle, key=lambda t: (len(t), t))


# ──────────────────────────────────────────────────────────────────────────────
# Helpers for the Mapper agent
# ──────────────────────────────────────────────────────────────────────────────

def compute_dependency_depths(safe_graph: list[TopicNode]) -> dict[str, int]:
    """
    Compute dependency_depth for every topic in the safe (acyclic) graph.

    Returns:
        dict mapping topic_name → depth integer.
        Root nodes (no prerequisite) = depth 0.
    """
    topic_map = {t.name: t for t in safe_graph}
    depth_cache: dict[str, int] = {}

    def _depth(name: str, visited: set[str]) -> int:
        if name in depth_cache:
            return depth_cache[name]
        if name in visited:
            # Should not happen on a safe (acyclic) graph — log and return 0
            logger.error(
                "Unexpected cycle in safe graph at topic '%s'. Returning depth 0.", name
            )
            return 0
        visited.add(name)
        node = topic_map.get(name)
        if node is None or node.prerequisite is None:
            result = 0
        else:
            result = 1 + _depth(node.prerequisite, visited)
        depth_cache[name] = result
        return result

    for topic in safe_graph:
        _depth(topic.name, set())

    return depth_cache


def build_processing_batches(safe_graph: list[TopicNode]) -> list[list[str]]:
    """
    Group topics into processing batches for parallel Writer calls.

    Batch 0: all root topics (no prerequisites).
    Batch N: all topics whose prerequisite is in batch N-1 or earlier.

    Returns:
        List of batches (each batch is a list of topic names).
        Topics in the same batch are safe to run in parallel.
    """
    depths = compute_dependency_depths(safe_graph)
    max_depth = max(depths.values(), default=0)

    batches: list[list[str]] = [[] for _ in range(max_depth + 1)]
    for topic in safe_graph:
        depth = depths[topic.name]
        batches[depth].append(topic.name)

    return [batch for batch in batches if batch]  # remove empty batches