# StudyAI — Product Requirements Document
## Phase 2: The 12-Agent Pipeline, Paper DNA System & Database Schema

> **Document:** 2 of 3  
> **Builds on:** Phase 1 (Product Strategy, Tech Stack, AI Routing)  
> **Focus:** Exact execution logic of every agent, Paper DNA deep dive, and complete database schema with field-level constraints  
> **Source authority:** Verified against `orchestrator.py`, all agent files, all schema JSONs, `queries.py`, `writer_invariant.txt`

---

## 1. Pipeline Execution Architecture — The Three Phases

The entire pipeline is orchestrated by `backend/pipeline/orchestrator.py` (836 lines). It runs as a FastAPI `BackgroundTask` — meaning it starts immediately and I can watch the progress live while it runs. The pipeline is divided into three strictly sequential phases.

```
POST /generate  →  run_pipeline(upc)
                        │
               ┌────────▼────────┐
               │   PHASE A       │  Serial — must complete before B starts
               │  Agents 1–4     │  ~60–120 seconds
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │   PHASE B       │  Parallel across units + topics
               │  Agents 5–9B    │  ~15–45 min (depends on topic count)
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │   PHASE C       │  Serial per unit, then paper-level
               │  Agents 10–12   │  ~10–20 min
               └────────┬────────┘
                        │
               pipeline_status = "complete"
```

### Pipeline Entry Points

| Trigger | Function | Behaviour |
|---|---|---|
| `POST /generate` | `run_pipeline(upc)` | Full pipeline from start |
| `POST /generate/rerun` with `from_agent: N` | `run_pipeline(upc, force_rerun_from=N)` | Calls `clear_downstream_from_agent(N)` first, then runs full pipeline |
| CLI directly | `python -m pipeline.orchestrator BSCMT201 --force-rerun-from=5` | Same as above, runs via `asyncio.run()` |

### Internal Exceptions

| Exception | Meaning | Pipeline Response |
|---|---|---|
| `_PipelineHaltError` | Clean stop — unrecoverable data problem | Sets `pipeline_status = "failed"` |
| `CostKillSwitchError` | 120 API calls or $8.00 limit exceeded | Sets `pipeline_status = "partial"` — completed units stay readable |
| `Exception` (uncaught) | Unexpected crash | Sets `pipeline_status = "partial"` and re-raises |

---

## 2. Phase A — Pre-Generation (Serial, ~60–120 seconds)

Phase A runs agents 1 through 4 in strict sequence. Each agent gates the next. Phase B cannot start until Phase A is 100% complete. **This is intentional** — the DNA and mapper output from Phase A is what makes Phase B's parallel notes generation exam-calibrated.

---

### Agent 1 — Decoder

**File:** `backend/pipeline/agents/agent_01_decoder.py`  
**Model:** None (no AI call)  
**Purpose:** Bootstrap the `papers` row in Supabase from the manual registry

**Logic:**
1. Reads `backend/source_map/upc_registry.json`
2. Looks up the UPC key (e.g. `"2352203601"`)
3. Constructs the `papers` row payload from the registry entry
4. Calls `q.upsert_paper(upc, paper_meta)` — inserts or updates the row

**Skip condition:** If `q.get_paper(upc)` already returns a row → Agent 1 is skipped entirely  
**Halt condition:** If row is still not present after Agent 1 runs → `_PipelineHaltError`

**Registry entry fields mapped to `papers` table:**
```
department, programme, semester, paper_name, paper_type,
diagram_heavy, practical_component, documentation_tier,
pyq_years_available, primary_textbook, all_prescribed_textbooks,
syllabus_url
```

---

### Agent 2 — Researcher

**File:** `backend/pipeline/agents/agent_02_researcher.py`  
**Model:** Gemini 2.5 Pro (`gemini-2.5-pro`)  
**Purpose:** Read syllabus.pdf + PYQ PDFs → extract structured syllabus JSON + raw PYQ list

**Skip condition:** If `q.paper_has_syllabus(upc)` returns `True` (units already seeded) → entire Agent 2 block skipped

**Logic (when not skipped):**
1. Reads `backend/source_pdfs/{upc}/syllabus.pdf` via PyMuPDF (fitz)
2. Collects all `pyq_{year}.pdf` files from `backend/source_pdfs/{upc}/`
3. Sends syllabus text to Gemini 2.5 Pro with `researcher.txt` prompt
4. Receives structured `syllabus_json` matching this schema:
   ```
   {
     "units": [
       {
         "unit_number": int,
         "unit_name": str,
         "topics": [str, str, ...],
         "hours": float | null
       }
     ],
     "prescribed_books": [str]
   }
   ```
5. Collects raw PYQ text from each PDF into `raw_pyq_list`

**Output handed to:**
- Agent 2B (for verification)
- `_seed_units_and_topics()` (creates unit + topic rows in Supabase after verification passes)
- Agent 2C (for PYQ normalisation)

---

### Agent 2B — Researcher Verifier

**File:** `backend/pipeline/agents/agent_02b_researcher_verifier.py`  
**Model:** Groq `llama3-70b-8192`  
**Purpose:** Binary pass/fail gate on Agent 2's syllabus JSON

**This agent does NOT fix anything. It only catches failures.**

**Three checks it runs:**
| Check | Question | Failure triggers |
|---|---|---|
| 1. Unit names present | Does every JSON unit name appear in the raw PDF text? | If any unit name is absent from the PDF |
| 2. No hallucinated topics | Are sample topics traceable to PDF text? | If multiple sample topics appear invented |
| 3. No missing units | Are there unit headings in the PDF not captured in JSON? | If visible units are missing |

**Fallback when PDF text unavailable (pdftotext not installed):**  
Runs JSON-structure-only checks — verifies all units have names, all units have topics, no empty arrays.

**Retry loop:**
- Called up to 2 times by orchestrator
- If Groq unavailable: automatically passes with flag (`"Groq unavailable: verification skipped"`)
- If parse error: automatically passes (non-blocking) with flag
- If both attempts fail verification: `_PipelineHaltError` raised — "Syllabus verification failed after 2 retries."

**Return value:** `bool` — `True` (pass) or `False` (fail, triggers Agent 2 retry)

---

### Agent 2C — PYQ Normaliser

**File:** `backend/pipeline/agents/agent_02c_pyq_normaliser.py`  
**Model:** Groq `llama3-70b-8192`  
**Purpose:** Convert raw PYQ PDF text into structured JSON per exam year

**Called once per PYQ PDF file found in `source_pdfs/{upc}/`**  
**2 retry attempts per PDF. On failure: that PYQ year is skipped (not fatal).**

**Output stored as:** `papers.paper_dna._raw_normalised_pyqs[]` via `_append_normalised_pyq()`

**Normalised PYQ structure per year:**
```
{
  "year": int,
  "year_confirmed": bool,
  "year_confidence": "confirmed" | "unconfirmed",
  "questions": [
    {
      "question_number": str,
      "unit": int | null,
      "parts": [
        {
          "part_label": str,
          "question_text": str,
          "marks": int,
          "instruction_word": str,
          "topic_hint": str | null,
          "unit": int | null
        }
      ]
    }
  ],
  "total_marks": int | null,
  "time_allowed_minutes": int | null
}
```

**This normalised output is the primary input to Agent 3 (Paper DNA).**

---

### Seeding Units and Topics

After Agent 2 + 2B + 2C complete, `_seed_units_and_topics(upc, syllabus_json)` creates the database rows:

1. For each `unit_data` in `syllabus_json["units"]`:
   - If unit_number not already in DB → calls `q.create_unit(upc, unit_number, unit_name, hours)` → `status = "queued"`
2. For each `topic_name` in `unit_data["topics"]`:
   - If topic_name not already in DB → calls `q.create_topic(unit_id, upc, topic_name, topic_number)` → `status = "queued"`

**These are the skeleton rows that Phase B will write content into.**

---

### Agent 3 — Paper DNA

**File:** `backend/pipeline/agents/agent_03_paper_dna/` (4 sub-modules)  
**Skip condition:** `q.paper_has_dna(upc)` → already populated → skip entire Agent 3

**Input:** `_raw_normalised_pyqs[]` from `papers.paper_dna` column  
**Output:** Assembled DNA blob stored in `papers.paper_dna` via `q.set_paper_dna()`

**Architecture:** 4 completely separate sub-modules, orchestrated by `_run_paper_dna()` in orchestrator.

#### Sub-Module A: Structural DNA
**File:** `agent_03_paper_dna/structural_dna.py`  
**Model:** Groq `llama3-70b-8192` (rule-based extraction + Groq for JSON formatting)  
**No AI reasoning needed** — this is mechanical counting and extraction

**What it extracts from normalised PYQs:**
```
{
  "total_marks": int,
  "time_allowed_minutes": int | null,
  "sections": [
    {
      "section_label": str,       // "Section A", "Part I", "Main"
      "marks_per_question": int,
      "total_questions": int,
      "attempt_count": int,       // how many must be answered
      "compulsory": bool
    }
  ],
  "question_distribution": [
    {
      "unit_number": int,
      "appearances_across_years": int,
      "avg_marks_per_year": float
    }
  ],
  "attempt_all": bool,
  "attempt": int
}
```

**Critical logic:** `_compute_question_distribution()` runs as a **pure Python arithmetic fallback** regardless of Groq's output. This means the question distribution is always mechanically correct even if Groq produces a bad response.

**Empty PYQ fallback:** If no normalised PYQs exist → returns `_empty_structural_dna()` scaffold with all `None` values.

#### Sub-Module B: Topic DNA + Language DNA (Combined Call)
**File:** `agent_03_paper_dna/topic_dna.py`  
**Model:** Gemini 2.0 Flash (single combined call returning both arrays)  
**Semaphore:** `_PRO_SEM` (2 concurrent max)  
**Retries:** 2 attempts

**Topic DNA output per topic:**
```
[
  {
    "topic_name": str,
    "appearances": [
      { "year": int, "marks": int, "question_type": str, "unit": int }
    ],
    "total_appearances": int,
    "marks_trend": "increasing" | "stable" | "decreasing" | "single_appearance",
    "priority": "high" | "medium" | "low" | "never_asked",
    "never_asked": bool,
    "recency_weight": float  // 1.0–1.5 (1.5 = most recent year)
  }
]
```

**Priority classification rules (from schema):**
| Priority | Condition |
|---|---|
| `high` | 2+ PYQ appearances OR recent 6-mark topic |
| `medium` | 1 appearance, 3–6 marks |
| `low` | 1 appearance, 2 marks |
| `never_asked` | On syllabus, zero PYQ appearances |

**Language DNA output per topic:**
```
[
  {
    "topic_name": str,
    "instruction_words": {
      "find": int, "prove": int, "define": int, "state": int,
      "explain": int, "derive": int, "calculate": int, "describe": int
    },
    "examiner_vocabulary": [str],   // verbatim repeated phrases from PYQ text
    "typical_phrasing": str          // most common full question phrasing, verbatim
  }
]
```

**On failure (both attempts):** Returns `{"topic_dna": [], "language_dna": []}` — Writer falls back to syllabus-hours depth signal.

#### Sub-Module C: Combination DNA
**File:** `agent_03_paper_dna/combination_dna.py`  
**Model:** Gemini 2.0 Flash (separate second call)  
**Semaphore:** `_PRO_SEM`  
**Retries:** 2 attempts

**Combination DNA output per topic:**
```
[
  {
    "topic_name": str,
    "always_asked_with": [str],          // topic names always co-appearing in PYQs
    "combination_pattern": str,           // description of co-occurrence pattern
    "standalone_frequency": float,        // 0.0–1.0, how often asked alone
    "diagram_required": bool,
    "numerical_always": bool
  }
]
```

**Used by:** Agent 5 (Writer) to ensure combination topics get cross-referenced examples; Agent 8 (Critic) to flag missing combination coverage.

**On failure:** Returns `{"combination_dna": []}` — Combination-aware examples not generated.

**Final DNA blob assembled by orchestrator:**
```python
{
  "structural_dna": struct,
  "topic_dna": topic_lang["topic_dna"],
  "language_dna": topic_lang["language_dna"],
  "combination_dna": combo["combination_dna"],
  "_raw_normalised_pyqs": [...],      # kept in blob for Agent 12
  "_independence_map": {...}           # added by Agent 4
}
```

---

### Agent 4 — Mental Model Mapper

**File:** `backend/pipeline/agents/agent_04_mental_model_mapper.py`  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_PRO_SEM` (2 concurrent max)  
**Skip condition:** `q.units_have_mapper_data(upc)` → topics already have non-null `topic_number` → skip  
**Retries:** 2 attempts  
**On failure:** Falls back to fully sequential topic ordering — Phase B still runs, just without parallel optimisation

**Input:** List of all units with their topics (from DB) + full paper row (with DNA)

**What it produces:**
1. **Optimised topic sequence** — reorders `topic_number` to build concept prerequisites first
2. **Prerequisite links** — `prerequisite_topic_id` + `prerequisite_bridge` (a single sentence connecting the two concepts)
3. **Concept bridges** — `connects_to_topic_id` + `connects_to_reason` (forward connections)
4. **`split_generation` flag** — marks topics that are too large for a single Writer call
5. **Independence map** — which topics within each unit can run in parallel vs must be sequential

**DB writes per topic (via orchestrator after mapper returns):**
```python
db.table("topics").update({
  "topic_number": optimised_sequence_number,
  "split_generation": bool
}).eq("id", tid)

q.set_topic_prerequisite(tid, prerequisite_topic_id, prerequisite_bridge)
q.set_topic_connects_to(tid, connects_to_topic_id, connects_to_reason)
```

**Independence map stored on paper:**
```python
paper_dna["_independence_map"] = {
  "independent_unit_ids": [uuid, uuid, ...],   # can run Phase B in parallel
  "dependent_unit_ids": [uuid, uuid, ...],      # must run after independents
  "independent_topic_ids": {
    unit_id: [topic_uuid, topic_uuid, ...]      # topics within unit that are independent
  }
}
```

**Cycle detection:** `backend/utils/cycle_detector.py` (13 KB) is used inside Agent 4 to prevent circular prerequisite chains (Topic A requires Topic B requires Topic A). The cycle detector resolves these by breaking the weakest link and surfacing a bridge sentence instead.

---

## 3. Phase B — Content Generation (Parallel)

Phase B runs Agents 5 through 9B. It is the most compute-intensive phase and the source of the actual study notes.

### Parallelism Architecture

**Unit-level parallelism** (controlled by independence map):
```python
batches = _build_unit_batches(units, independence_map)
# Batch 1: independent units → run in parallel (asyncio.gather)
# Batch 2+: dependent units → run sequentially after batch 1
```

**Topic-level parallelism within each unit:**
```python
parallel_topics = [t for t in pending if t["id"] in independent_topic_ids]
sequential_topics = [t for t in pending if t["id"] not in independent_topic_ids]

await asyncio.gather(*[_write_single_topic(t, paper, cost) for t in parallel_topics])
for t in sequential_topics:
    await _write_single_topic(t, paper, cost)
```

**Unit resume loop:** Each unit gets up to `MAX_UNIT_RESUME_ATTEMPTS = 3` tries. On retry, only topics that aren't `complete` are re-run (Writer's skip logic).

---

### Agent 5 — Writer

**File:** `backend/pipeline/agents/agent_05_writer.py` (878 lines, 42 KB — the largest agent)  
**Model:** Gemini 2.0 Flash (`gemini-2.0-flash`)  
**Semaphore:** `_FLASH_SEM` (5 concurrent max)  
**Retries:** `MAX_WRITER_RETRIES = 3` per topic  
**Retry backoff:** `attempt × 5 seconds` (linear, not exponential — in-agent retry, separate from `with_backoff()`)

**This is the most important agent.** Its output is what I read and study from.

#### Prompt Architecture

The Writer uses a **two-part prompt** loaded once per process at module import:

| Part | File | Contents | Changes Per Call? |
|---|---|---|---|
| System prompt (invariant) | `writer_invariant.txt` (13.7 KB, 233 lines) | The Note Standard — all rules, LaTeX requirements, depth calibration, field-by-field rules | Never — same across all topics |
| User message (variant) | `writer_variant.py` (13.5 KB) — `build_writer_user_prompt()` | Topic name, DNA signals, prerequisite bridge, adjacent topics, split-mode flag | Yes — rebuilt per topic call |

#### What the Variant Prompt Injects Per Topic

```
- topic_name: str
- priority: "high" | "medium" | "low" | "never_asked"
- depth_signal_source: "pyq" | "cbcs_estimate" | "syllabus_hours"
- topic_dna: [...] (from paper_dna)
- language_dna for this topic: {...}
- combination_dna for this topic: {...}
- prerequisite_bridge: str (from Agent 4)
- left_adjacent_topic: str (for boundary enforcement)
- right_adjacent_topic: str (for boundary enforcement)
- documentation_tier: 1 | 2 | 3 | 4
- paper_type: "theory" | "numerical" | "mixed" | "life_sciences"
- diagram_heavy: bool
- SPLIT GENERATION MODE: "content" | "examples" | null
```

#### Split Generation Mode

Agent 4 flags certain topics with `split_generation = True`. These are topics with both high content depth (6-mark) AND complex numerical examples. For these:

**Call 1 (content mode):** Generates everything EXCEPT `examples` and `pyqs` — those are set to `[]`  
**Call 2 (examples mode):** Generates ONLY `examples` and `pyqs`  
**Merge:** `output = {**content_output, **examples_output}`  

This avoids exceeding context window limits for complex topics.

#### Schema Validation

After each Writer call, `jsonschema.validate(output, topic_schema)` runs. If validation fails:
- Retry with more explicit schema constraints added to the prompt
- On 3rd failure: `set_topic_status(topic_id, "failed")` → raises exception → unit resume loop catches it

#### LaTeX Pre-Processing

Before sending to Critic: `auto_fix_latex()` from `utils/latex_formatter.py` runs on the output. This catches the most common Writer LaTeX errors:
- Raw Greek letters → LaTeX (ε → `\varepsilon`, λ → `\lambda`, etc.)
- Raw number sets → LaTeX (ℝ → `\mathbb{R}`)
- Bare `dy/dx` → `$\frac{dy}{dx}$`

Residual errors that slip through become Critic flags.

#### The Mandatory Scratchpad (From writer_invariant.txt)

Before generating any field, the Writer must internally answer:
1. What is this topic really about in one sentence?
2. How does DU actually test this — which instruction words, which PYQ patterns?
3. What does a full-marks student know that a passing student doesn't?
4. What is the single most important thing to communicate?

This reasoning never appears in output — it is silent pre-generation reasoning.

#### Depth Calibration Rules (Direct from writer_invariant.txt)

| Priority | Content Generated |
|---|---|
| `never_asked` | One line only: "On syllabus. Has not appeared in any NEP DU exam." All other fields `null`. `rapid_revision` still required at minimum viable level. |
| `2-mark` topics | `definition` + one `example` only. `core_concept`, `analogy`, `answer_writing_technique` → `null`. |
| `3–4 mark` topics | `definition` + `core_concept` + one `example`. `answer_writing_technique` → `null`. |
| `6-mark` topics | Full treatment — ALL fields populated. `answer_writing_technique` MANDATORY with `word_count_target`. Two examples required (clean worked + edge case / combination). |

#### Word Economy Enforced Rules

Every sentence must do exactly one of:
- **DEFINE** something
- **EXPLAIN** something
- **DEMONSTRATE** something
- **WARN** about something

Forbidden phrases (zero exam value): "it is important to note", "this concept plays a crucial role", "understanding this is essential", "this is a key idea" — any variation.

---

### Agent 6 — Coverage Checker

**File:** `backend/pipeline/agents/agent_06_coverage_checker.py` (9 KB)  
**Model:** Groq `llama3-70b-8192`  
**Semaphore:** `_GROQ_SEM` (3 concurrent max)  
**Called:** Once per unit, after all topics in that unit complete writing  
**On Groq failure:** Returns empty `{}` — unit proceeds to Critic without coverage flags

**Input:**
- The unit row (with unit name)
- All `complete` topics in the unit (their full content JSON)
- The paper row (for syllabus reference)

**What it checks:**
- Are all syllabus topics for this unit represented in the written content?
- Are any PYQ instruction words from Language DNA missing from the coverage?

**Output:** `coverage_flags: dict` — passed to Agent 8 (Critic) to include in its critique

---

### Agent 7 — Verifier

**File:** `backend/pipeline/agents/agent_07_verifier.py` (18.6 KB)  
**Model:** Cerebras  
**Semaphore:** `_GROQ_SEM` (used for Cerebras too in current orchestrator — 3 concurrent)  
**Called:** Once per `high`-priority topic only  
**Retries:** `MAX_VERIFIER_RETRIES = 2`  
**On failure:** Sets `verify_result = {"verified": False, "flagged_steps": []}` — topic continues to Critic

**Purpose:** Step-by-step mathematical/logical verification of the Writer's examples and proofs

**Verification modes (set by Writer in `verification_mode` field):**
| Mode | Applied When | What Verifier Does |
|---|---|---|
| `numerical_single` | Medium/low priority numerical topics | Checks final answer and one intermediate step |
| `numerical_dual` | High priority numerical topics | Full step-by-step recomputation |
| `proof` | Proof topics | Checks logical validity, hypothesis stated, conclusion exact |
| `none` | Theory examples | Verifier skips — no mathematical content to verify |

**Output sets on examples in DB:**
- `examples[i].verified = true` if step passes
- `examples[i].verification_passed = true/false`
- `verify_result.flagged_steps` → passed to Critic for awareness

**Topics not verified (by design):**
- `medium`, `low`, `never_asked` priority topics skip Agent 7 entirely
- `verify_result = {"verified": None, "flagged_steps": []}` is passed to Critic

---

### Agent 8 — Critic

**File:** `backend/pipeline/agents/agent_08_critic.py` (13 KB)  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_FLASH_SEM` (5 concurrent max)  
**Called:** Once per topic (parallel across topics, same as Verifier)  
**Retries:** `MAX_CRITIC_RETRIES = 2`  
**On exhaustion:** Topic proceeds uncorrected (no Rewriter called)

**Input:**
- The full topic content from DB
- The paper row
- `verify_result` from Agent 7 (including `flagged_steps`)
- `coverage_flags` from Agent 6

**Output:** `diff_schema.json` — a surgical correction document

**Critic Diff Schema (complete specification):**
```json
{
  "topic_id": "uuid",
  "corrections": [
    {
      "field": "exact.field.path",   // e.g. "definition", "examples[0].steps[2].units_shown"
      "issue": "specific problem",    // not generic — names the exact issue
      "correction": "actionable fix", // tells Rewriter exactly what to change
      "severity": "critical" | "major" | "minor"
    }
  ]
}
```

**Severity meanings:**
- `critical` = marks will be lost if this stays — Rewriter must fix it
- `major` = answer is incomplete — Rewriter should fix it
- `minor` = polish — Rewriter may fix if within scope

**Max 10 corrections per topic.** If more than 10 exist: Critic must prioritise by marks impact.

**Powered by `critic_constitution.txt`** (4.2 KB) — the bible of what makes a DU exam note good or bad.

**If `diff.corrections` is empty:** Critic found no issues → Rewriter is NOT called → topic considered complete.

---

### Agent 9 — Rewriter

**File:** `backend/pipeline/agents/agent_09_rewriter.py` (12 KB)  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_FLASH_SEM`  
**Called only if:** Critic produced a non-empty `corrections` list

**Input:**
- Full topic content from DB
- Critic's `diff` object
- Paper row

**Logic:** Applies the Critic's surgical corrections field-by-field. Each correction specifies the exact field path, so the Rewriter doesn't need to re-generate the entire topic — it patches only the named fields.

**Output:** Patched topic dict (same shape as Writer output, `topic_schema.json` compliant)

**Does NOT write to DB directly** — output goes to Agent 9B for validation first.

---

### Agent 9B — Micro-Validator

**File:** `backend/pipeline/agents/agent_09b_micro_validator.py` (10.8 KB)  
**Model:** Groq `llama3-70b-8192`  
**Semaphore:** `_GROQ_SEM`  
**Retries:** 2 attempts

**Purpose:** Verify that the Rewriter's patched output:
1. Actually addressed the Critic's corrections (didn't ignore them)
2. Didn't break any fields that were already correct (regression check)
3. Has `rapid_revision` populated (mandatory field existence check)

**Return:** `{"passed": bool}`

**On pass:** `q.save_topic_content(topic_id, patched)` → topic is saved with rewritten content  
**On fail (both attempts):** Logs warning, **retains the pre-rewrite value** (the Writer's original output) — does NOT overwrite with a failed rewrite

---

## 4. Phase C — Coverage and Patching (Serial Per Unit)

Phase C runs Agents 10, 11, 11B per unit, then Agent 12 once for the entire paper.

---

### Agent 10 — Final Examiner

**File:** `backend/pipeline/agents/agent_10_final_examiner.py` (11.6 KB)  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_FLASH_SEM`  
**Retries:** `MAX_EXAMINER_RETRIES = 2`  
**On exhaustion:** Uses `{"uncovered_pyqs": [], "marks_incomplete_topics": []}` — skips to summary

**Called:** Once per unit, sequentially  
**Skips failed units:** `if unit["status"] != "complete": continue`

**Input:** Unit row + all topics in unit + `paper_dna` blob + paper row

**What it checks:**
- Are all normalised PYQs for this unit addressed somewhere in the topic content?
- Are there topics where the marks calibration seems incomplete (based on `answer_writing_technique` + marks)?

**Output:**
```
{
  "uncovered_pyqs": [
    {
      "question_text": str,
      "marks": int,
      "year": int,
      "suggested_topic": str | null
    }
  ],
  "marks_incomplete_topics": [
    {
      "topic_id": str,
      "topic_name": str,
      "issue": str
    }
  ]
}
```

**If no uncovered PYQs and no incomplete topics:** Skips directly to `_generate_unit_summary()`.

---

### Agent 11 — Patcher

**File:** `backend/pipeline/agents/agent_11_patcher.py` (13.4 KB)  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_FLASH_SEM`  
**Retries:** `MAX_PATCHER_RETRIES = 2`  
**On exhaustion:** `{"topic_patches": [], "unit_patches": []}` — no patch applied

**Purpose:** Add the missing PYQ coverage identified by Agent 10

**Output:**
```
{
  "topic_patches": [
    {
      "topic_id": str,
      "patched_fields": {
        "pyqs": [...],            // appends missing PYQs to existing list
        "examiners_note": str,    // updated if needed
        ...
      }
    }
  ],
  "unit_patches": [
    {
      "unit_id": str,
      "conceptual_summary": {
        "what_this_unit_is_about": str,
        "how_topics_connect": str,
        "unifying_idea": str
      }
    }
  ]
}
```

**DB writes:**
```python
q.save_topic_patch(tp["topic_id"], tp["patched_fields"])
# Sets topics.patched = True as a flag
q.save_unit_summary(up["unit_id"], conceptual_summary=cs, unit_closer={})
```

---

### Agent 11B — Post-Patch Regeneration

**File:** `backend/pipeline/agents/agent_11b_post_patch_regen.py` (9.7 KB)  
**Model:** Gemini 2.0 Flash  
**Semaphore:** `_FLASH_SEM`

**Two functions in one file:**

**`run(patched_topic_ids, unit, paper, cost)`** — Rapid revision regen:
- Called only if any topics were patched by Agent 11
- For each patched topic: re-generates `rapid_revision`, `quick_checks`, and `summary` fields
- Ensures `rapid_revision` stays accurate after content patches
- Output written via `q.save_topic_patch(topic_regen["topic_id"], topic_regen["fields"])`

**`run_unit_summary(unit, topics, paper, cost)`** — Unit-level conceptual summary:
- Called for every unit (patched or not) after Phase C completes
- Generates `conceptual_summary` + `unit_closer.exam_ready_checklist`
- Written via `q.save_unit_summary(unit_id, conceptual_summary, unit_closer)`

**Unit Closer Output (`unit_schema.json`):**
```
{
  "conceptual_summary": {
    "what_this_unit_is_about": str,   // 2 plain sentences
    "how_topics_connect": str,         // 1-2 sentences
    "unifying_idea": str               // 1 sentence — the anchor concept
  },
  "unit_closer": {
    "exam_ready_checklist": [str, str, str]  // 2-4 capability statements
  }
}
```

---

### Agent 12 — Consistency Checker

**File:** `backend/pipeline/agents/agent_12_consistency_checker.py` (16.8 KB, 381 lines)  
**Model:** Groq `llama-3.3-70b-versatile`  
**Semaphore:** `_GROQ_SEM`  
**Called:** Once, after all units complete, paper-level — the final automated gate  
**On Groq failure:** Notation/definition checks skipped; rule-based checks (LaTeX, PYQ year) still run

**Five Checks:**

| Check | Method | Severity |
|---|---|---|
| 1. Notation consistency | Groq AI — same quantity, same symbol across all topics | major/critical → re-route to Critic |
| 2. Definition consistency | Groq AI — same term, compatible definitions across topics | major/critical → re-route to Critic |
| 3. PYQ year conflicts | Pure Python — same question text, different year tag in two topics | critical → `needs_human_review` (me) |
| 4. Priority tag consistency | Pure Python — topic tagged `never_asked` but appears in normalised PYQs | major → re-route to Critic |
| 5. LaTeX auto-patch | Pure Python + regex — Unicode math chars in any string field | minor → auto-patched in-place |

**LaTeX auto-patch table (regex-based, no AI):**
```
ε → \varepsilon     λ → \lambda       ω → \omega
θ → \theta          φ → \phi          ψ → \psi
σ → \sigma          μ → \mu           π → \pi
ℝ → \mathbb{R}      ℕ → \mathbb{N}    ℚ → \mathbb{Q}
ℤ → \mathbb{Z}      ℂ → \mathbb{C}
dy/dx (bare) → $\frac{dy}{dx}$
```

**Output routing:**
```
latex_violations    → auto-patched silently (saved to DB)
major violations    → topics re-routed to Agent 8 (Critic) via asyncio.gather
critical violations → added to needs_human_review (I review these manually)
```

After Agent 12 completes: `pipeline_status = "complete"` is set.

---

## 5. The Complete Topic Output Schema

This is the canonical JSON schema that every topic must conform to. Agent 5 writes it, Agent 8 critiques it, Agent 9 patches it, Agent 9B validates it.

### Required Fields (schema `required` array)
`topic_name`, `priority`, `difficulty`, `rapid_revision`, `definition`, `core_concept`, `examiners_note`, `common_mistakes`, `pyqs`, `quick_checks`

### Complete Field Reference

| Field | Type | Required | Who Sets It | Key Constraints |
|---|---|---|---|---|
| `topic_name` | `string` | ✓ | Agent 5 | Exact syllabus name |
| `priority` | `enum` | ✓ | Agent 5 (from Topic DNA) | `high/medium/low/never_asked` |
| `difficulty` | `enum` | ✓ | Agent 5 | `easy/medium/hard` |
| `estimated_study_minutes` | `int\|null` | — | Agent 5 | Calibrated: never_asked=5, 2-mark=15, 3-4 mark=25, 6-mark=45–60 |
| `depth_signal_source` | `enum\|null` | — | Agent 5 | `pyq/cbcs_estimate/syllabus_hours` |
| `rapid_revision` | `object` | ✓ | Agent 5 (generated last, placed first) | 3 sub-fields all required |
| `rapid_revision.definition_one_line` | `string` | ✓ | Agent 5 | Under 15 words. Answers a 2-mark "define" |
| `rapid_revision.key_formula_or_concept` | `string` | ✓ | Agent 5 | Single most-tested LaTeX expression |
| `rapid_revision.examiner_pattern` | `string` | ✓ | Agent 5 | Exact instruction word + typical phrasing. Tier 3: "No NEP exam data available." |
| `definition` | `string\|null` | ✓ | Agent 5 | Under 40 words. All math in LaTeX. DU-acceptable for 2-mark answer. |
| `core_concept` | `string\|null` | ✓ | Agent 5 | Plain language. No assumed knowledge beyond prerequisite bridge |
| `analogy` | `string\|null` | — | Agent 5 | Must connect to prerequisite bridge |
| `analogy_verified` | `bool\|null` | — | Agent 5 | `true` only if factually correct comparison. Never just "evocative" |
| `examples` | `array\|null` | — | Agent 5 | Full step-by-step with LaTeX on every step for numerical |
| `examples[].type` | `enum` | ✓ | Agent 5 | `numerical/theory/biological` |
| `examples[].steps[].step_text` | `string` | ✓ | Agent 5 | Full LaTeX on every math step |
| `examples[].steps[].units_shown` | `bool\|null` | — | Agent 5 | `true` on every intermediate with numeric value |
| `examples[].answer_boxed` | `bool\|null` | — | Agent 5 | `true` for ALL numerical — mandatory |
| `examples[].verified` | `bool` | ✓ | Agent 5 sets `false`; Agent 7 sets `true` | — |
| `examples[].verification_mode` | `enum\|null` | — | Agent 5 | `numerical_single/numerical_dual/proof/none` |
| `examples[].verification_passed` | `bool\|null` | — | Agent 7 | `null` until Agent 7 runs |
| `examples[].common_error` | `string\|null` | — | Agent 5 | DU-specific, not generic |
| `diagram_block` | `object\|null` | — | Agent 5 | `null` unless `diagram_heavy=true` or 6-mark PYQ requires diagram |
| `diagram_block.svg_source` | `enum` | — | Agent 5 | `library` (complex bio) or `generated` (simple geometric) |
| `diagram_block.svg_code` | `string\|null` | — | Agent 5 | `null` for library. Minimal renderable SVG for generated |
| `examiners_note` | `string\|null` | ✓ | Agent 5 | Exact instruction word from Language DNA. PYQ year ref (Tier 1/2). What full marks needs |
| `examiners_note_pyq_refs` | `string[]\|null` | — | Agent 5 | e.g. `["2024", "2023"]` |
| `instruction_word_frequency` | `object\|null` | — | Agent 5 (from Language DNA) | e.g. `{"find": 2, "prove": 1}`. `null` if no Language DNA |
| `common_mistakes` | `array` | ✓ | Agent 5 | 1–3 items. DU-specific marks impact on each |
| `common_mistakes[].marks_impact` | `string` | ✓ | Agent 5 | Exact marks lost with evidence |
| `answer_writing_technique` | `object\|null` | — | Agent 5 | Present for ALL 6+ mark topics. `null` otherwise (Critic flags if missing) |
| `answer_writing_technique.structure` | `string[]` | — | Agent 5 | Sentence-by-sentence, not paragraph |
| `answer_writing_technique.marks_distribution` | `object` | — | Agent 5 | Which structure element earns which marks |
| `answer_writing_technique.word_count_target` | `int\|null` | — | Agent 5 | Theory: 150–200 words. Numerical: `null` |
| `pyqs` | `array` | ✓ | Agent 5 (from normalised PYQs) | All relevant PYQs. Exact verbatim question text — never paraphrased |
| `pyqs[].year_confirmed` | `bool\|null` | — | Agent 2C | `true` only if confirmed from document text |
| `pyqs[].instruction_word` | `string` | ✓ | Agent 5 | `find/prove/define/state/explain/derive/calculate/describe` |
| `pyqs[].recency_weight` | `float\|null` | — | Agent 5 | `1.5` for most recent year, `1.0` otherwise |
| `quick_checks` | `string[]` | ✓ | Agent 5 | Exactly 3 items. No answers — EVER. At least 1 requires application |
| `flagged_fields` | `object\|null` | — | Agent 5 | Self-flags: e.g. `{"definition": "syllabus_too_vague"}` |

---

## 6. Database Schema — Complete Field-Level Specification

The database is the single source of truth. All 10 tables are created by `backend/database/migrations/001_initial_schema.sql`.

**Access rule:** Backend writes ONLY through `backend/database/queries.py`. Client singleton (`database.client.db`) uses the **service-role key** — bypasses RLS entirely (appropriate for personal use).

---

### Table: `papers`

One row per UPC. The top-level container for all pipeline data.

| Column | Type | Default | Who Writes | Notes |
|---|---|---|---|---|
| `upc` | `TEXT PRIMARY KEY` | — | Agent 1 (Decoder) | e.g. `"2352203601"` |
| `department` | `TEXT NOT NULL` | — | Agent 1 | From `upc_registry.json` |
| `programme` | `TEXT NOT NULL` | — | Agent 1 | e.g. `"B.Sc. (H) Mathematics"` |
| `semester` | `INTEGER NOT NULL` | — | Agent 1 | `3` |
| `paper_name` | `TEXT NOT NULL` | — | Agent 1 | e.g. `"Probability and Statistics"` |
| `paper_type` | `TEXT NOT NULL` | — | Agent 1 | `theory/numerical/mixed/life_sciences` |
| `diagram_heavy` | `BOOLEAN` | `FALSE` | Agent 1 | Drives `diagram_block` generation in Agent 5 |
| `practical_component` | `BOOLEAN` | `FALSE` | Agent 1 | e.g. `true` for Excel lab component |
| `syllabus_url` | `TEXT` | `NULL` | Agent 1 | `null` if no official URL |
| `syllabus_last_verified` | `TIMESTAMPTZ` | — | Reserved | Not currently written by pipeline |
| `syllabus_hash` | `TEXT` | — | Reserved | For future change detection |
| `syllabus_confidence` | `TEXT` | `'high'` | Agent 1 | `high/medium/low` — maps to documentation tier |
| `pyq_years_available` | `INTEGER[]` | — | Agent 1 | e.g. `[2023]` |
| `documentation_tier` | `INTEGER` | `2` | Agent 1 | `1/2/3/4` — governs pipeline behaviour |
| `primary_textbook` | `TEXT` | — | Agent 1 | Full bibliographic reference |
| `all_prescribed_textbooks` | `JSONB` | — | Agent 1 | Array of bibliographic references |
| `paper_dna` | `JSONB` | — | Agents 2C, 3, 4 | All DNA components + `_raw_normalised_pyqs` + `_independence_map` |
| `pipeline_status` | `TEXT` | `'queued'` | Orchestrator | `queued/generating/complete/failed/partial` |
| `generated_at` | `TIMESTAMPTZ` | `NOW()` | — | Auto |
| `last_updated` | `TIMESTAMPTZ` | `NOW()` | — | Auto |
| `english_content_ready` | `BOOLEAN` | `FALSE` | Reserved | Not yet set by pipeline |
| `hindi_content_ready` | `BOOLEAN` | `FALSE` | Reserved | Not yet implemented |

---

### Table: `units`

One row per unit. Status transitions trigger frontend Realtime updates.

| Column | Type | Default | Who Writes | Notes |
|---|---|---|---|---|
| `id` | `UUID PRIMARY KEY` | `gen_random_uuid()` | Supabase | Auto-generated |
| `upc` | `TEXT NOT NULL` | — | Agent 2 (seed) | FK → papers.upc ON DELETE CASCADE |
| `unit_number` | `INTEGER NOT NULL` | — | Agent 2 (seed) | 1-indexed |
| `unit_name` | `TEXT NOT NULL` | — | Agent 2 (seed) | From syllabus extraction |
| `estimated_study_hours` | `FLOAT` | — | Agent 2 (seed) | From registry or syllabus (e.g. `15.0`) |
| `marks_weightage` | `INTEGER` | — | Reserved | Not currently set |
| `status` | `TEXT` | `'queued'` | Orchestrator | `queued/generating/verifying/complete/failed` — **Realtime trigger** |
| `conceptual_summary` | `JSONB` | — | Agent 11B | `{what_this_unit_is_about, how_topics_connect, unifying_idea}` |
| `unit_closer` | `JSONB` | — | Agent 11B | `{exam_ready_checklist: [str]}` — 2–4 capability statements |
| `generated_at` | `TIMESTAMPTZ` | `NOW()` | — | Auto |
| `last_updated` | `TIMESTAMPTZ` | `NOW()` | — | Auto |

**Indexes:** `idx_units_upc ON units(upc)`, `idx_units_status ON units(status)`

---

### Table: `topics`

The most important table. One row per topic. All content generated by agents lives here.

| Column | Type | Default | Who Writes | Notes |
|---|---|---|---|---|
| `id` | `UUID PRIMARY KEY` | `gen_random_uuid()` | Supabase | Auto |
| `unit_id` | `UUID NOT NULL` | — | Agent 2 (seed) | FK → units.id ON DELETE CASCADE |
| `upc` | `TEXT NOT NULL` | — | Agent 2 (seed) | FK → papers.upc |
| `topic_name` | `TEXT NOT NULL` | — | Agent 2 (seed) | Exact syllabus name |
| `topic_number` | `INTEGER NOT NULL` | — | Agent 2 (seed), rewritten by Agent 4 | Optimised sequence after Mapper |
| `difficulty` | `TEXT` | — | Agent 5 | `easy/medium/hard` |
| `estimated_study_minutes` | `INTEGER` | — | Agent 5 | 5/15/25/45–60 |
| `priority` | `TEXT` | — | Agent 5 | `high/medium/low/never_asked` |
| `prerequisite_topic_id` | `UUID` | — | Agent 4 | FK → topics.id (self-referential) |
| `prerequisite_bridge` | `TEXT` | — | Agent 4 | Single sentence connecting concepts |
| `status` | `TEXT` | `'queued'` | Orchestrator | `queued/generating/complete/failed` — **Realtime trigger** |
| `connects_to_topic_id` | `UUID` | — | Agent 4 | Forward connection (self-referential FK) |
| `connects_to_reason` | `TEXT` | — | Agent 4 | Why these topics connect |
| `split_generation` | `BOOLEAN` | `FALSE` | Agent 4 | If `true`: Writer runs two separate calls |
| `depth_signal_source` | `TEXT` | — | Agent 5 | `pyq/cbcs_estimate/syllabus_hours` |
| `rapid_revision` | `JSONB` | — | Agent 5 | `{definition_one_line, key_formula_or_concept, examiner_pattern}` |
| `definition` | `TEXT` | — | Agent 5 | Under 40 words, LaTeX |
| `core_concept` | `TEXT` | — | Agent 5 | Plain language explanation |
| `analogy` | `TEXT` | — | Agent 5 | Connected to prerequisite bridge |
| `analogy_verified` | `BOOLEAN` | `FALSE` | Agent 5 | Only `true` if factually accurate |
| `examples` | `JSONB` | — | Agent 5 | Array of worked examples with steps, verification |
| `diagram_block` | `JSONB` | — | Agent 5 | `{diagram_name, svg_source, svg_code, labeled_parts, ...}` |
| `examiners_note` | `TEXT` | — | Agent 5 | Exact instruction word + PYQ year reference |
| `examiners_note_pyq_refs` | `TEXT[]` | — | Agent 5 | e.g. `["2024", "2023"]` |
| `instruction_word_frequency` | `JSONB` | — | Agent 5 | `{"find": 2, "prove": 1, ...}` |
| `common_mistakes` | `JSONB` | — | Agent 5 | Array of `{description, marks_impact}` — 1–3 items |
| `answer_writing_technique` | `JSONB` | — | Agent 5 | Required for 6+ mark topics |
| `pyqs` | `JSONB` | — | Agent 5, patched by Agent 11 | Array of `{year, marks, question_text, key_steps, ...}` |
| `quick_checks` | `TEXT[]` | — | Agent 5, patched by Agent 11B | Exactly 3 — no answers, ever |
| `flagged_fields` | `JSONB` | — | Agent 5 | Self-flags for uncertain content |
| `patched` | `BOOLEAN` | `FALSE` | Agent 11 | Set `true` when Patcher modifies this topic |
| `generated_at` | `TIMESTAMPTZ` | — | Agent 5 | Set on first write |
| `last_updated` | `TIMESTAMPTZ` | `NOW()` | — | Auto |

**Indexes:** `idx_topics_unit_id ON topics(unit_id)`, `idx_topics_upc ON topics(upc)`

**DB write functions (`queries.py`):**

| Function | Purpose |
|---|---|
| `save_topic_content(topic_id, content)` | Full Writer output — whitelisted field write, sets `status="complete"` |
| `save_topic_patch(topic_id, patched_fields)` | Partial field write from Patcher — sets `patched=True` |
| `set_topic_status(topic_id, status)` | Status transition only |
| `set_topic_prerequisite(tid, prereq_id, bridge)` | Agent 4 bridge write |
| `set_topic_connects_to(tid, connects_id, reason)` | Agent 4 connection write |

**`save_topic_content` whitelist** (only these fields accepted — guards against schema drift):
```
difficulty, estimated_study_minutes, priority, depth_signal_source, rapid_revision,
definition, core_concept, analogy, analogy_verified, examples, diagram_block,
examiners_note, examiners_note_pyq_refs, instruction_word_frequency,
common_mistakes, answer_writing_technique, pyqs, quick_checks,
connects_to_reason, flagged_fields
```

---

### Table: `field_flags`

Student-submitted flags (written by frontend, reviewed by me manually).

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Auto |
| `topic_id` | `UUID NOT NULL` | FK → topics.id |
| `field_name` | `TEXT NOT NULL` | Which field I flagged |
| `flag_type` | `TEXT NOT NULL` | `seems_wrong/outdated/missing_something` |
| `student_note` | `TEXT` | My note about the issue |
| `session_id` | `TEXT` | My browser session UUID |
| `flags_in_session` | `INTEGER` | `DEFAULT 1` — rate limit tracked in frontend |
| `groq_verdict` | `TEXT` | Reserved: `confirmed/unconfirmed/manual` — for future auto-review |
| `status` | `TEXT` | `DEFAULT 'open'` — `open/under_review/resolved` |
| `resolved_at` | `TIMESTAMPTZ` | When I manually resolve |

**Rate limit:** Frontend (`sessions.ts`) enforces max 10 flags per paper per session. The `FLAG_LIMIT = 10` constant.

---

### Table: `pyq_submissions`

PYQ PDFs I upload to unlock Tier 3/4 papers.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Auto |
| `upc` | `TEXT NOT NULL` | The paper this PYQ belongs to |
| `year_tagged_by_student` | `INTEGER NOT NULL` | The year I say it is |
| `year_extracted_from_doc` | `INTEGER` | Extracted from PDF content (pipeline sets this) |
| `year_confidence` | `TEXT` | `confirmed/unconfirmed` |
| `file_url` | `TEXT` | Supabase Storage URL |
| `file_deleted` | `BOOLEAN` | `DEFAULT FALSE` |
| `extracted_json` | `JSONB` | Agent 2C normalised output after processing |
| `verification_status` | `TEXT` | `DEFAULT 'pending'` — `pending/verified/failed/manual_review` |
| `quality_scores` | `JSONB` | `{scan_readability, completeness, upc_match, failure_reason}` |
| `reward_issued` | `BOOLEAN` | `DEFAULT FALSE` |
| `reward_type` | `TEXT` | `early_access/cross_paper_credit` |
| `reward_paper_upc` | `TEXT` | For cross-paper rewards |
| `submitted_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

---

### Remaining Tables (Reserved / Scaffolded)

| Table | Purpose | Status |
|---|---|---|
| `problem_sets` | Worked problem sets per unit | Schema created, pipeline not yet writing to it |
| `formula_sheets` | Formula/diagram/key-terms reference per unit | Schema created, pipeline not yet writing to it |
| `syllabus_change_log` | Detects syllabus hash changes between runs | Schema created, detection logic not built |
| `sessions` | Server-side session tracking | Schema created, not used (client-side sessions only) |
| `session_paper_views` | Per-session paper access + progress | Schema created, not used yet |

---

## 7. Force-Rerun Data Clearing (`clear_downstream_from_agent`)

When I run `POST /generate/rerun` with `from_agent: N`, the orchestrator calls `q.clear_downstream_from_agent(upc, N)` first. Here is exactly what gets cleared:

| `from_agent` ≤ | Cleared Data |
|---|---|
| `3` | `papers.paper_dna = NULL` |
| `4` | All topic `prerequisite_topic_id`, `prerequisite_bridge`, `connects_to_topic_id`, `connects_to_reason`, `split_generation` reset to `NULL/FALSE` |
| `5` | All topic content fields → `NULL`, all topic `status = "queued"`, all unit `status = "queued"` |
| `12` (any agent) | `papers.pipeline_status = "queued"` |

**Example — re-tuning the Writer:**
```bash
# Edit writer_invariant.txt to improve note quality
# Then re-run from Agent 5 only (Phase A data is preserved)
curl -X POST localhost:8000/generate/rerun \
  -H "Content-Type: application/json" \
  -d '{"upc": "2352203601", "from_agent": 5}'
```
This clears all topic content + unit statuses but keeps the Paper DNA, Mapper data, and unit skeleton rows intact. Agent 5 re-runs in ~15–45 minutes instead of the full pipeline.

---

*Phase 3 covers: Frontend UI Component Architecture (15 note field components, 6 shared UI components), Progressive Rendering integration with Supabase Realtime, and all Failure/Error Handling pathways rendered in the browser.*
