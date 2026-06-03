# StudyAI — Product Requirements Document
## Phase 1: Product Strategy, Philosophy, Scope & Tech Stack

> **Document:** 1 of 3  
> **Who this is for:** Me. One developer. My own DU exams.  
> **Guiding principle:** This is not a startup. It is a personal power tool. No scaling, no auth, no deployment infra — just a precision pipeline that generates the best possible study notes for my specific papers, running on my own machine.  
> **Source authority:** Grounded exclusively in the actual codebase — `backend/`, `frontend/`, `PLAN/`, `.env`, `requirements.txt`, `package.json`, `upc_registry.json`  
> **Last sync:** Verified against all implementation files

---

## 1. What This Is (And What It Is Not)

### What it IS:
- A **local, personal AI pipeline** that takes my DU B.Sc. NEP 2022 paper code (UPC), reads my manually collected syllabus + PYQ PDFs, and generates the most exam-calibrated study notes possible
- A **12-agent system** that runs on my laptop (`localhost:8000` backend, `localhost:3000` frontend)
- Something I run **once per exam paper**, watch it process, and then study from the output
- A tool that gets **iteratively better** — I tune `writer_invariant.txt` and `critic_constitution.txt`, wipe the Supabase rows, and re-run until the notes are perfect for how DU actually asks questions

### What it is NOT:
- A product for other students
- Deployed anywhere — no cloud server, no Vercel, no Docker in production
- Multi-user — there is no authentication, no accounts, no session server
- Constantly running — I start it when I need it, it runs for one paper, I stop it

### The Single Most Important Fact:
> **I am the user. The quality of the notes determines if I pass my exams. Every architectural decision exists to serve that one goal.**

---

## 2. Current Live Paper

From `backend/source_map/upc_registry.json` — the only paper registered so far:

| Field | Value |
|---|---|
| **UPC** | `2352203601` |
| **Paper Name** | Probability and Statistics |
| **Paper Code** | DSC-3 |
| **Programme** | B.Sc. (H) Mathematics |
| **Semester** | 3 |
| **Paper Type** | `numerical` (mixed theory + heavy calculation) |
| **Documentation Tier** | `1` (fully documented — best case) |
| **PYQ Years Available** | `[2023]` |
| **Primary Textbook** | Devore, J.L. (2016) — Probability and Statistics for Engineering and the Sciences, 9th ed., Cengage |
| **Secondary Textbook** | Mood, Graybill & Boes (1974) — Introduction to the Theory of Statistics, 3rd ed., Tata McGraw-Hill |
| **Units** | 3 units — Descriptive Stats + Probability, Continuous Distributions, CLT + Regression |
| **Study Hours** | 15 hrs × 3 units = 45 hrs total |
| **Practical Component** | Yes — 30 hours software labs (Microsoft Excel) |

This is the test paper for the full end-to-end pipeline run. Everything is built and tuned around making these notes perfect first.

---

## 3. Core Product Philosophy — The Note Standard

> This is the most important section. Every agent, every prompt, every component is measured against this philosophy. If an agent's output doesn't serve this, it's wrong.

### 3.1 The Exam-Calibration Principle

I don't want "good notes." I want **notes that help me pass my DU exam**. The difference:

- Content depth is determined by **how many marks DU has historically awarded to this topic** and **exactly how the examiner phrases the question** — not by how interesting or comprehensive a topic feels
- Every definition I read must be **directly answerable in an exam setting** without needing external context
- Every PYQ reference must be **year-confirmed** — not guessed, not approximated
- Mathematical notation must be **consistent across the entire paper** so I'm not confused by different symbols in different units

### 3.2 The Note Standard — 8 Non-Negotiable Rules

These are hard rules encoded into the prompts and enforced by specific agents. If any of these fail, the output is wrong.

| # | Rule | Enforced By |
|---|---|---|
| 1 | Every definition must be DU-exam-answerable as a standalone sentence | Agent 5 (`writer_invariant.txt`) |
| 2 | Every analogy must be verifiable — `analogy_verified: bool` must be `true` or flagged | Agent 5 outputs the field; Agent 7 may flag it |
| 3 | PYQ year attributions require explicit source confirmation — `year_confirmed` + `year_confidence` fields | Agent 2C (PYQ Normaliser) sets these |
| 4 | Mathematical notation must be consistent across all topics in a paper | Agent 12 (Consistency Checker) — auto-fixes Unicode → LaTeX |
| 5 | No topic may reach `complete` status without passing through the Critic → Rewriter → Micro-Validator gate | Orchestrator enforces this sequence |
| 6 | `rapid_revision` block must exist for every topic — it is the last-minute study anchor | Agent 9B (Micro-Validator) checks this field exists |
| 7 | Content depth is driven by PYQ priority signal, not word count — `priority: high/medium/low/never_asked` | Topic DNA → Agent 5 writer injection |
| 8 | `flagged_fields` JSONB must surface to me when anything is uncertain | Agent pipeline writes flags; frontend renders them visibly |

### 3.3 Strict Architectural Separation

Three systems. Each has one job and must not bleed into the other.

```
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE  (FastAPI + 12 Agents)                            │
│  → Write-only. Triggered once per UPC.                      │
│  → All output stored in Supabase. Nothing held in memory.   │
└───────────────────────────┬─────────────────────────────────┘
                            │ writes to
┌───────────────────────────▼─────────────────────────────────┐
│  DATABASE  (Supabase PostgreSQL)                             │
│  → Canonical source of truth.                               │
│  → Agents write ONLY via queries.py abstraction.            │
│  → No agent ever imports database.client.db directly.       │
└───────────────────────────┬─────────────────────────────────┘
                            │ reads from / subscribes to
┌───────────────────────────▼─────────────────────────────────┐
│  FRONTEND  (Next.js 16)                                      │
│  → Read-only during viewing. Pure renderer.                  │
│  → Never calls FastAPI after pipeline is triggered.          │
│  → Writes ONLY to field_flags and pyq_submissions tables.   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. The 4-Tier Documentation Trust Model

This determines what the pipeline can do with a paper based on what source material I've manually provided. It's set in `upc_registry.json` before running.

| Tier | Name | What I Have | Syllabus Confidence | Pipeline Behaviour | My Access |
|---|---|---|---|---|---|
| **1** | Fully Documented | Official syllabus PDF + ≥ 3 confirmed PYQ year PDFs | `high` | Full pipeline — all DNA + full PYQ coverage | Always unlocked |
| **2** | Partially Documented | Official syllabus + 1–2 PYQ years | `medium` | Full pipeline — PYQ coverage will have gaps | Always unlocked |
| **3** | Syllabus-Only | Syllabus PDF only, no PYQs | `low` | Runs in syllabus-based mode — no PYQ DNA | Requires PYQ submission unlock |
| **4** | Reconstructed | No official docs — reconstructed from course structure | `low` | Most speculative output | Requires PYQ submission unlock |

**Implementation in code:**
- `papers.documentation_tier INTEGER DEFAULT 2` — written by Agent 1 (Decoder) from `upc_registry.json`
- `papers.syllabus_confidence TEXT DEFAULT 'high'` — enum: `high/medium/low`
- Frontend gate: `frontend/lib/sessions.ts` → `isPaperUnlocked(upc, tier)` — Tier 1/2 always `true`; Tier 3/4 check `SessionData.unlockedPapers[]`

**My current paper (`2352203601`) is Tier 1** — best case, full pipeline runs with PYQ coverage enabled.

---

## 5. Scope — Exactly What I'm Building and Nothing More

### 5.1 In Scope (Personal v1.0)

- Running the pipeline locally for 1–2 exam papers at a time
- Triggering via `POST /generate` with a UPC → 12-agent pipeline runs → notes appear in browser
- Watching pipeline progress live (Supabase Realtime on `units` + `topics` tables)
- Reading the final notes in a clean Next.js UI with KaTeX math rendering
- Flagging fields I think are wrong (up to 10 per paper — stored in `field_flags` table)
- Uploading PYQ PDFs I find myself (stored in `pyq_submissions` — for Tier 3/4 unlock)
- Force-reruns: `POST /generate/rerun` with `from_agent: N` — wipe and re-run from any agent
- Iterative prompt tuning: edit `writer_invariant.txt` → `reset_db.py` → re-run → better notes
- Exporting notes as PDF for offline revision (via `html2canvas`)

### 5.2 Explicitly Not Building (v1.0)

| What | Why Not |
|---|---|
| User authentication / accounts | It's just me |
| Production deployment (Vercel, Docker, AWS) | Runs locally on my machine |
| Multi-paper parallel runs | One paper at a time is all I need |
| Admin dashboard | I check the terminal log directly |
| Hindi content generation | Reserved column in DB, not implemented yet |
| Vector similarity search | pgvector installed but unused |
| Temporal workflow orchestration | Not needed for local personal use |
| Syllabus change detection | Reserved table, logic not built |
| Scaling / rate limiting for multiple users | There are no other users |
| CI/CD pipelines | I run `uvicorn main:app --reload` myself |

---

## 6. Tech Stack

### 6.1 Backend — Python / FastAPI

I run this from `cd backend && uvicorn main:app --reload --port 8000`.

| Component | Technology | Version Constraint | What It Does |
|---|---|---|---|
| Language | Python | 3.11+ | All backend logic |
| API Framework | FastAPI | latest | 4 REST endpoints + background task execution |
| ASGI Server | Uvicorn | latest | Serves the FastAPI app locally with hot-reload |
| PDF Extract (Primary) | PyMuPDF (`fitz`) | ≥ 1.24.0 | Fast text extraction from syllabus + PYQ PDFs |
| PDF Extract (Fallback) | pdfplumber | ≥ 0.11.0 | Table/layout extraction when fitz is insufficient |
| Schema Validation | jsonschema | ≥ 4.22.0 | Validates every agent JSON output against its schema |
| Retry Decorator | tenacity | ≥ 8.2.0 | Decorator-based retry for fragile API calls |
| Env Management | python-dotenv | ≥ 1.0.0 | Loads `backend/.env` on startup |
| Database Client | supabase-py | ≥ 2.4.0 | All Supabase reads/writes via PostgREST |

**The 4 API Endpoints (all I need):**

```
POST /generate              → 202 Accepted — kicks off full 12-agent pipeline as BackgroundTask
GET  /status/{upc}          → Returns current pipeline_status + per-unit statuses (fallback poll)
POST /generate/rerun        → 202 Accepted — force re-runs from agent N, clears downstream DB data
GET  /health                → {"status": "ok"} — sanity check
```

**CORS:** Locked to `http://localhost:3000` only. This is never exposed to the internet.

**Duplicate run guard:** `_active_runs: set[str]` in memory — if I accidentally submit the same UPC twice, returns `409 Conflict` instead of running two parallel pipelines.

---

### 6.2 Frontend — Next.js / React

I run this from `cd frontend && npm run dev` (Turbopack).

| Component | Technology | Version | What It Does |
|---|---|---|---|
| Framework | Next.js | ^16.2.6 | App Router, React Server Components, Turbopack |
| Language | TypeScript | ^5 | All frontend code typed |
| UI Runtime | React | ^19.0.0 | Component rendering |
| Styling | Tailwind CSS | ^3.4.17 | Utility-first styling |
| Animation | Framer Motion | ^12.38.0 | Topic card animations, progressive reveal transitions |
| Math Rendering | KaTeX + react-katex | ^0.16.15 / ^3.0.1 | All LaTeX formulas rendered inline + block |
| DB Client (Browser) | @supabase/supabase-js | ^2.105.4 | Direct Supabase reads + Realtime subscriptions |
| DB Client (SSR) | @supabase/ssr | ^0.10.3 | SSR-safe Supabase client for server components |
| Data Fetching | @tanstack/react-query | ^5.100.10 | Server state, caching, background refetch |
| Icons | lucide-react | ^1.16.0 | UI icons throughout |
| PDF Export | html2canvas | ^1.4.1 | Lets me export rendered notes as PDF |
| Class Utilities | clsx + tailwind-merge | ^2.1.1 / ^2.5.5 | Conditional class merging without conflicts |

**The 3 Routes (all I need):**

```
/                     → Home — I type my UPC here, hit Generate
/pipeline/[upc]/      → Live view — shows pipeline running, unit-by-unit progress
/paper/[upc]/         → The notes — fully rendered study document, this is what I study from
```

**Session (no auth — it's just me):**

My browser gets a UUID stored in `localStorage` under `studyai_session_id`. The `SessionData` object (`studyai_session_data`) tracks:
- `flagCounts: Record<upc, number>` — how many fields I've flagged on this paper (max 10)
- `flaggedPapers: string[]` — which papers I've flagged
- `unlockedPapers: string[]` — Tier 3/4 papers I've unlocked via PYQ submission

This is entirely client-side. SSR returns a placeholder UUID — no server session.

---

### 6.3 Database — Supabase / PostgreSQL

I use the free Supabase tier. I have one project. All pipeline data goes into it.

| Component | Technology | Purpose |
|---|---|---|
| Database | PostgreSQL 15+ (via Supabase) | All persistent agent output data |
| REST API | Supabase PostgREST | How supabase-py and the JS client read/write |
| Realtime | Supabase Realtime (WebSocket) | Frontend subscribes to `units` + `topics` changes live |
| Extension | pgvector | Installed, not used in v1.0 |
| Auth | None | No RLS, no auth — free tier, personal project |

**The 10 Tables at a Glance:**

| Table | Who Writes | Who Reads | What It Stores |
|---|---|---|---|
| `papers` | Agents 1–3 | Frontend (read) | One row per UPC — all metadata, Paper DNA blob, pipeline status |
| `units` | Agents 2, 9–12 | Frontend (Realtime) | One row per unit — status, conceptual_summary, unit_closer |
| `topics` | Agents 5–12 | Frontend (read) | One row per topic — ALL content fields (20+ JSONB + text columns) |
| `problem_sets` | Reserved | Frontend | Worked problem sets per unit |
| `formula_sheets` | Reserved | Frontend | Formula/diagram/key-terms reference per unit |
| `pyq_submissions` | Frontend (write) | Backend (future) | PYQs I upload myself — for Tier 3/4 unlock rewards |
| `syllabus_change_log` | Reserved | Reserved | Detected syllabus hash changes — not built yet |
| `field_flags` | Frontend (write) | Reserved | Fields I've flagged as wrong/uncertain |
| `sessions` | Reserved | Reserved | Server-side session tracking — not used yet |
| `session_paper_views` | Reserved | Reserved | Paper access tracking — not used yet |

**Access Pattern — The Hard Rule:**
- **Backend writes:** ONLY through functions in `backend/database/queries.py`. No agent ever calls `db.table(...)` directly.
- **Frontend reads:** Direct Supabase JS client. No calls to FastAPI during viewing.
- **Frontend writes:** Only to `field_flags` and `pyq_submissions`.

**Realtime Subscriptions (what makes progressive rendering work):**

```typescript
// When I open /pipeline/[upc]/, these channels are opened:
subscribeToUnitStatus(upc, onUpdate)
  → channel: `units:upc:${upc}`
  → event: postgres_changes INSERT/UPDATE
  → filter: upc=eq.{upc}
  → triggers: unit card appears/updates in my browser

subscribeToTopicStatus(unitId, onUpdate)
  → channel: `topics:unit_id:${unitId}`
  → event: postgres_changes INSERT/UPDATE
  → filter: unit_id=eq.{unitId}
  → triggers: individual topic sections populate as they complete
```

---

### 6.4 AI Provider Stack and Routing Strategy

This is the most important infrastructure decision. Each provider is free at the tier I'm using. Provider selection is based on **what kind of reasoning the task requires**, not cost.

#### 6.4.1 The Four Providers

| Provider | Model | What It's Good At | My Free Tier Limit |
|---|---|---|---|
| **Google AI Studio** | `gemini-2.0-flash` | Fast, large context, excellent instruction-following — primary workhorse | ~15 RPM (free) |
| **Google AI Studio** | `gemini-2.5-pro` | Deep multi-document reasoning — for complex extraction tasks | ~5 RPM (free, strict) |
| **Groq** | `llama-3` | Extremely fast, high throughput — for binary/structural/verification tasks | ~30 RPM (generous) |
| **Cerebras** | Cerebras inference | Ultra-fast numerical reasoning — for math step verification | ~15 RPM |

> **Why multiple providers?** Not for redundancy — for capability matching. Gemini 2.5 Pro for deep syllabus extraction. Flash for creative note-writing. Groq for fast binary checks. Cerebras for math proofs. Using the wrong provider on the wrong task wastes capacity and produces worse output.

#### 6.4.2 Exact Agent → Provider → Model Routing Table

| Agent | # | Provider | Model | Why This Provider |
|---|---|---|---|---|
| Decoder | 1 | **None** | — | Pure JSON registry lookup — no AI needed |
| Researcher | 2 | **Gemini 2.5 Pro** | `gemini-2.5-pro` | Reading a dense PDF syllabus, extracting structured units/topics JSON — needs deep reasoning |
| Researcher Verifier | 2B | **Groq** | `llama-3` | Binary pass/fail on extracted JSON — fast, no creativity needed |
| PYQ Normaliser | 2C | **Groq** | `llama-3` | Structured normalization of raw PYQ text — high throughput, deterministic |
| Paper DNA — Structural | 3 | **None** | — | Rule-based stats from normalized PYQ JSON — pure Python, no AI |
| Paper DNA — Topic + Language | 3 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Single combined Flash call → returns `topic_dna[]` + `language_dna[]` arrays |
| Paper DNA — Combination | 3 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Second Flash call — topic co-occurrence + examiner combination patterns |
| Mental Model Mapper | 4 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Dependency graph construction + topic sequence optimisation across all units |
| Writer | 5 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | **The most important call.** One call per topic. Largest context. Writes the actual notes I study from |
| Coverage Checker | 6 | **Groq** | `llama-3` | Fast cross-reference: output JSON vs syllabus JSON — structural check, not creative |
| Verifier | 7 | **Cerebras** | Cerebras | Step-by-step proof/numerical verification — ultra-low latency for math checks |
| Critic | 8 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Quality critique — must understand the note deeply to produce surgical JSON diffs |
| Rewriter | 9 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Applies Critic diffs — targeted field-level rewrites |
| Micro-Validator | 9B | **Groq** | `llama-3` | Validates the rewrite didn't regress — fast binary check |
| Final Examiner | 10 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Compares unit content against PYQ question list — marks what's missing |
| Patcher | 11 | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Adds missing PYQ coverage + fills incomplete fields |
| Post-Patch Regen | 11B | **Gemini 2.0 Flash** | `gemini-2.0-flash` | Regenerates `rapid_revision`, `quick_checks`, `conceptual_summary` after patching |
| Consistency Checker | 12 | **Groq** | `llama-3` | Paper-level notation/definition/year consistency audit — fast, deterministic rules |

**Net Flash calls per topic (worst case):** Agent 5 (1) + Agent 8 (1) + Agent 9 (1) + Agent 10 (1) + Agent 11 (1) + Agent 11B (1) = **6 Flash calls per topic**. My `BSCMT201` style paper with ~12 topics across 3 units = ~72 Flash calls total — well under the 120-call kill switch.

#### 6.4.3 Concurrency Control — How Parallelism is Gated

All concurrency is managed by `asyncio.Semaphore` — **no threading semaphores, no `time.sleep()`** (these would block the entire event loop and kill parallelism).

Semaphores are created lazily inside the running uvicorn event loop via `rate_limiter.py`:

| Semaphore | Provider | Max Concurrent | Where Defined |
|---|---|---|---|
| `_FLASH_SEM` | Gemini 2.0 Flash | **5** | `orchestrator.py` line ~95 |
| `_PRO_SEM` | Gemini 2.5 Pro | **2** | `orchestrator.py` line ~96 |
| `_GROQ_SEM` | Groq Llama 3 | **3** (orchestrator) / 8 (rate_limiter max) | `orchestrator.py` line ~97 |
| `_CEREBRAS_SEM` | Cerebras | **3** | `orchestrator.py` line ~98 |

> **Note:** `rate_limiter.py` defines `groq: 8` as the theoretical maximum. `orchestrator.py` uses `_GROQ_SEM = asyncio.Semaphore(3)` as the actual operating limit. The orchestrator value governs runtime.

#### 6.4.4 Exponential Backoff Specification

Implemented in `backend/utils/rate_limiter.py` → `with_backoff()`:

| Parameter | Value |
|---|---|
| Base delay | `2.0 seconds` |
| Max delay cap | `60.0 seconds` |
| Max retry attempts | `5` |
| Jitter | `random.uniform(0, delay × 0.3)` added per retry |
| Backoff growth | `delay = min(delay × 2, 60.0)` each attempt |
| Triggers | `"429"`, `"rate limit"`, `"too many requests"`, `"ratelimit"`, `"quota"` (case-insensitive) |

**Important:** `with_backoff()` handles retry logic only. The caller must acquire the semaphore first (`async with _FLASH_SEM:`). The backoff function never re-acquires the semaphore on retry.

#### 6.4.5 The Cost Kill-Switch

From `backend/utils/cost_tracker.py`:

| Limit | Value | Behaviour on Breach |
|---|---|---|
| Max API calls per pipeline run | **120 calls** | Raises `CostKillSwitchError` immediately |
| Max estimated cost per run | **$8.00 USD** | Raises `CostKillSwitchError` immediately |
| Warning threshold | **$5.00 USD** | Logs a warning, continues running |

**All current providers are free** — cost is always `$0.00`. The call-count limit (120) is the real guard. If something goes wildly wrong and agents start looping, the kill-switch stops it at 120 calls.

**On `CostKillSwitchError`:** `pipeline_status` is set to `"partial"` (not `"failed"`). This means any units already completed remain fully readable in my browser. The pipeline stops gracefully.

**Tracking fields per API call:** `agent`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `success: bool`, `retry_count`, `estimated_cost_usd`, `timestamp`

---

## 7. Pipeline Status State Machine

These are the exact status values written to Supabase by `orchestrator.py`. My frontend Realtime subscriptions trigger on every change.

### 7.1 Paper Level (`papers.pipeline_status`)

```
queued
  └─→ generating
         ├─→ complete          ← Happy path — I can read all notes
         ├─→ failed            ← Pipeline halted (PipelineHaltError)
         └─→ partial           ← Cost kill-switch or unexpected crash — completed units still readable
```

### 7.2 Unit Level (`units.status`)

```
queued
  └─→ generating               ← Writer is running on this unit's topics
         └─→ verifying         ← Coverage Checker, Verifier, Critic running
                ├─→ complete   ← All topics done, unit summary generated
                └─→ failed     ← Retried up to MAX_UNIT_RESUME_ATTEMPTS = 3 times, then failed
```

### 7.3 Topic Level (`topics.status`)

```
queued
  └─→ generating               ← Writer (Agent 5) is running
         ├─→ complete           ← Writer + Critic + Rewriter + Micro-Validator all passed
         └─→ failed             ← Writer retried MAX_WRITER_RETRIES = 3 times, then failed
```

---

## 8. Retry Budget

How many times each agent will attempt before giving up or escalating:

| Agent / Gate | Max Attempts | What Happens on Exhaustion |
|---|---|---|
| Researcher (Agent 2) | 2 | `_PipelineHaltError` — syllabus extraction critical |
| Researcher Verifier (2B) | 2 | `_PipelineHaltError` — cannot proceed without verified syllabus |
| PYQ Normaliser (2C) | 2 per PDF | Skips that PYQ file, logs warning, continues |
| Paper DNA — Topic/Language (3) | 2 | Uses empty DNA, logs warning, continues |
| Paper DNA — Combination (3) | 2 | Uses empty combination, logs warning, continues |
| Mapper (Agent 4) | 2 | Falls back to fully sequential topic processing |
| **Writer (Agent 5)** | **3** (`MAX_WRITER_RETRIES`) | Sets topic `status = "failed"`, raises exception |
| **Unit Resume** | **3** (`MAX_UNIT_RESUME_ATTEMPTS`) | Unit marked `failed`, pipeline continues with other units |
| Verifier (Agent 7) | 2 (`MAX_VERIFIER_RETRIES`) | Uses empty verify result, topic continues to Critic |
| Critic (Agent 8) | 2 (`MAX_CRITIC_RETRIES`) | Topic proceeds uncorrected (skips Rewriter) |
| Micro-Validator (9B) | 2 | Retains pre-rewrite value (safe fallback) |
| Final Examiner (Agent 10) | 2 (`MAX_EXAMINER_RETRIES`) | Uses empty examiner output, skips to summary |
| Patcher (Agent 11) | 2 (`MAX_PATCHER_RETRIES`) | No patch applied, logs warning |
| Exponential backoff (all) | 5 per API call | Raises last exception |

---

## 9. Observability — What I Can See

v1.0 uses Python's built-in `logging` module only. This is all I need for personal use.

**Terminal output** (where I watch the pipeline run):

| Logger Namespace | Level | What It Prints |
|---|---|---|
| `studyai.main` | `INFO` | Pipeline queued/started messages |
| `studyai.orchestrator` | `INFO/WARNING/ERROR` | Phase A/B/C progress, agent completions, failures |
| `studyai.db` | `INFO` | Every status transition written to Supabase |
| `studyai.cost` | `DEBUG/WARNING` | Per-call token counts + cumulative cost |
| `rate_limiter` | `WARNING` | Rate limit hits + backoff delays |

**Log format:** `HH:MM:SS  LEVEL    namespace  message`

**Pipeline run log:** Output is also written to `backend/pipeline_run.log` (18 KB from the last full run — real data, not mock).

**Cost summary at end of run:**
```
Cost summary for 2352203601
  Total calls : 73
  Total cost  : $0.0000
  By agent:
    writer                         calls=12  cost=$0.0000
    critic                         calls=12  cost=$0.0000
    ...
```

**Rate limiter stats** (callable during runtime, not yet exposed as API):
```python
from utils.rate_limiter import get_stats
get_stats()
# → {"requests": {"gemini_flash": 72, "groq": 18}, "failures": {"groq": 2}}
```

---

## 10. Complete Folder Structure Reference

### 10.1 Backend (`backend/`)

```
backend/
│
├── .env                                    ← API keys (GEMINI, GROQ, CEREBRAS, SUPABASE_URL, SUPABASE_KEY)
├── main.py                                 ← FastAPI app: /generate, /status/{upc}, /generate/rerun, /health
├── requirements.txt                        ← All Python deps: gemini SDK, groq, pymupdf, pdfplumber, supabase, jsonschema, tenacity, dotenv
├── pipeline_run.log                        ← Log file from last full pipeline execution (18 KB)
│
├── ── Dev/Debug Scripts ──
├── audit_agents.py                         ← Scans all agent files, verifies run() signatures match orchestrator calls
├── fix_all_agents.py                       ← Auto-patches agent files with correct run() wrappers
├── patch_writer.py                         ← Targeted hot-patch script for agent_05_writer.py
├── test_signatures.py                      ← Runs signature verification tests
├── reset_db.py                             ← Wipes Supabase rows for a UPC (used between tuning iterations)
│
├── pipeline/
│   ├── orchestrator.py                     ← 836-line async engine: Phase A → B → C, semaphores, resume logic, kill-switch
│   ├── phase5_pipeline.py                  ← Standalone test runner for Phase B (Agents 5–9B only)
│   │
│   ├── agents/
│   │   ├── __init__.py                     ← Exposes all agents so orchestrator can do `from pipeline.agents import agent_05_writer as writer`
│   │   │
│   │   ├── agent_01_decoder.py             ← Reads upc_registry.json → writes papers row to Supabase
│   │   ├── agent_02_researcher.py          ← Reads syllabus.pdf → Gemini 2.5 Pro → structured syllabus JSON
│   │   ├── agent_02b_researcher_verifier.py ← Groq binary pass/fail on syllabus JSON (11.5 KB)
│   │   ├── agent_02c_pyq_normaliser.py     ← Groq normalises raw PYQ text → structured JSON (12 KB)
│   │   │
│   │   ├── agent_03_paper_dna/             ← 4 sub-modules for the Paper DNA analysis
│   │   │   ├── structural_dna.py           ← Rule-based stats (no AI): mark distribution, instruction words, PYQ patterns
│   │   │   ├── topic_dna.py                ← Gemini Flash: topic frequency + priority across PYQ years
│   │   │   ├── language_dna.py             ← Gemini Flash (combined with topic): instruction word patterns
│   │   │   └── combination_dna.py          ← Gemini Flash: topic co-occurrence + examiner combo patterns
│   │   │
│   │   ├── agent_04_mental_model_mapper.py ← Gemini Flash: dependency graph, optimised sequence, concept bridges (18 KB)
│   │   ├── agent_05_writer.py              ← Gemini Flash: full note writer per topic — THE core agent (42 KB)
│   │   ├── agent_06_coverage_checker.py    ← Groq: syllabus vs output cross-reference per unit (9 KB)
│   │   ├── agent_07_verifier.py            ← Cerebras: proof + numerical step verification (18.6 KB)
│   │   ├── agent_08_critic.py              ← Gemini Flash: quality critique → diff_schema JSON output (13 KB)
│   │   ├── agent_09_rewriter.py            ← Gemini Flash: applies Critic diffs per field (12 KB)
│   │   ├── agent_09b_micro_validator.py    ← Groq: validates rewrite didn't regress (10.8 KB)
│   │   ├── agent_10_final_examiner.py      ← Gemini Flash: PYQ coverage audit per unit (11.6 KB)
│   │   ├── agent_11_patcher.py             ← Gemini Flash: adds missing PYQs + field patches (13.4 KB)
│   │   ├── agent_11b_post_patch_regen.py   ← Gemini Flash: regen rapid_revision, quick_checks, conceptual_summary (9.7 KB)
│   │   └── agent_12_consistency_checker.py ← Groq: cross-topic notation/definition/year consistency (16.8 KB)
│   │
│   ├── prompts/
│   │   ├── researcher.txt                  ← Syllabus extraction instructions (38 bytes — minimal, logic in schema)
│   │   ├── paper_dna_topic.txt             ← Topic DNA + Language DNA combined prompt (6 KB)
│   │   ├── paper_dna_language.txt          ← Language pattern prompt (supplementary to topic DNA)
│   │   ├── mapper.txt                      ← Mental model mapping + dependency ordering prompt (6.8 KB)
│   │   ├── writer_invariant.txt            ← THE NOTE STANDARD — core writer rules that never change (13.7 KB)
│   │   ├── writer_variant.py               ← Dynamic prompt builder — injects topic DNA + bridges per call (13.5 KB)
│   │   ├── proof_verifier.txt              ← Constitution for proof/step verification (4.2 KB)
│   │   ├── critic_constitution.txt         ← "What makes a DU exam note good or bad" — the Critic's bible (4.2 KB)
│   │   ├── coverage_checker.txt            ← Coverage audit instructions (1.8 KB)
│   │   ├── final_examiner.txt              ← PYQ coverage check prompt (2 KB)
│   │   ├── patcher.txt                     ← Patch generation instructions (3.6 KB)
│   │   └── consistency_checker.txt         ← Cross-topic consistency rules (2.6 KB)
│   │
│   └── schemas/
│       ├── topic_schema.json               ← THE most critical schema — full topic output structure (15.8 KB)
│       ├── paper_dna_schema.json           ← Paper DNA blob validation (5.5 KB)
│       ├── diff_schema.json                ← Critic diff output format (1.6 KB)
│       ├── critic_diff_schema.json         ← Critic diff variant (1 KB)
│       └── unit_schema.json                ← Unit-level output schema (4.3 KB)
│
├── database/
│   ├── client.py                           ← Supabase client singleton (`db`) — imported only by queries.py
│   ├── queries.py                          ← ALL database operations — 304 lines, single source of truth
│   └── migrations/
│       └── 001_initial_schema.sql          ← Complete 10-table schema — run once in Supabase SQL editor
│
├── utils/
│   ├── cost_tracker.py                     ← API spend tracker + 120-call kill switch (134 lines)
│   ├── rate_limiter.py                     ← Async semaphores + exponential backoff (150 lines)
│   ├── cycle_detector.py                   ← Prevents infinite loops in topic prerequisite graphs (13 KB)
│   ├── latex_formatter.py                  ← Unicode math → LaTeX auto-correction rules
│   ├── depth_signal.py                     ← Topic depth signal source classifier (pyq/cbcs_estimate/syllabus_hours)
│   ├── pdf_detector.py                     ← PDF type detection (scanned vs digital)
│   ├── svg_library.py                      ← SVG diagram library reference
│   ├── textbook_resolver.py               ← Maps topic to prescribed textbook section
│   └── tier_classifier.py                  ← Documentation tier classification logic
│
├── source_map/
│   ├── upc_registry.json                   ← Manual registry: UPC → paper metadata (department, textbooks, units, tier)
│   ├── master_source_map.json              ← Reserved: master cross-paper source index
│   └── textbook_registry.json              ← Reserved: textbook metadata registry
│
└── source_pdfs/
    └── {upc}/
        ├── syllabus.pdf                    ← Official DU syllabus PDF — I download this manually
        └── pyq_{year}.pdf                  ← Previous year question papers — I collect these manually
```

### 10.2 Frontend (`frontend/`)

```
frontend/
│
├── package.json                            ← All deps: Next.js 16, React 19, Tailwind 3, KaTeX, Framer Motion, Supabase, TanStack Query
├── next.config.ts                          ← Next.js config
├── tailwind.config.ts                      ← Tailwind config
├── tsconfig.json                           ← TypeScript config
├── postcss.config.js                       ← PostCSS / Autoprefixer
├── .env.local                              ← NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY
├── .env.example                            ← Template showing required env vars
│
├── app/                                    ← Next.js App Router
│   ├── layout.tsx                          ← Root layout — font loading, metadata, QueryClientProvider wrapper
│   ├── page.tsx                            ← Home: UPC input form → POST /generate → route to /pipeline or /paper
│   ├── globals.css                         ← Global base styles
│   ├── providers.tsx                       ← TanStack Query client provider
│   │
│   ├── paper/
│   │   └── [upc]/
│   │       └── page.tsx                    ← Full study notes view — reads completed data from Supabase
│   │
│   └── pipeline/
│       └── [upc]/
│           └── page.tsx                    ← Live pipeline monitor — Realtime subscriptions, progressive topic reveal
│
├── components/
│   ├── notes/                              ← 15 components — one per topic content field (see PRD Phase 3)
│   │
│   ├── pipeline/                           ← Pipeline progress UI components
│   │
│   └── ui/                                 ← 6 shared utility UI components (see PRD Phase 3)
│
├── lib/
│   ├── supabase.ts                         ← Supabase browser client singleton (461 bytes)
│   ├── queries.ts                          ← All reads, Realtime subscriptions, field flag + PYQ submission writes (195 lines)
│   ├── sessions.ts                         ← Session UUID, flag rate limiting, Tier 3/4 unlock logic (148 lines)
│   └── katex.ts                            ← KaTeX rendering helpers, LaTeX detection, safe render wrapper (2.5 KB)
│
└── types/
    └── database.ts                         ← TypeScript interfaces: Paper, Unit, Topic, FormulaSheet, ProblemSet, PYQSubmission
```

---

## 11. My Personal Iteration Workflow

This is the actual loop I run to make the notes better:

```
1. Tune writer_invariant.txt or critic_constitution.txt
         ↓
2. python reset_db.py  (wipes all rows for my UPC)
         ↓
3. curl -X POST localhost:8000/generate -d '{"upc": "2352203601"}'
         ↓
4. Open localhost:3000/pipeline/2352203601  — watch it run live
         ↓
5. Read the notes at localhost:3000/paper/2352203601
         ↓
6. Flag anything wrong using the flag button on any field
         ↓
7. If a specific agent is the problem:
   curl -X POST localhost:8000/generate/rerun -d '{"upc": "2352203601", "from_agent": 5}'
   (re-runs from Agent 5 only, clears downstream data, keeps Phase A intact)
         ↓
8. Repeat until notes are perfect
```

---

*Phase 2 covers: The 12-Agent Pipeline Execution Logic (all three phases A/B/C), Paper DNA System in depth, and complete Database Schema field-by-field constraints.*

*Phase 3 covers: Frontend UI Component Architecture (15 note components, 6 UI components), Progressive Rendering integration, and all Failure/Error Handling pathways rendered in the UI.*
