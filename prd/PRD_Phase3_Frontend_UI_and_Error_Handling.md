# StudyAI — Product Requirements Document
## Phase 3: Frontend UI Architecture, Progressive Rendering & Error Handling

> **Document:** 3 of 3  
> **Builds on:** Phase 1 (Strategy, Stack) + Phase 2 (Pipeline, Schema)  
> **Verified against:** Every line of every frontend file (read in full)  
> **Personal-use mandate:** No auth, no users table, no multi-tenancy. This runs on localhost:3000 for me alone.

---

## 1. Frontend Folder Structure — Exact Layout

```
frontend/
├── app/                          # Next.js App Router (all pages)
│   ├── layout.tsx                # Root layout — fonts, providers wrap
│   ├── globals.css               # Tailwind base + CSS variables
│   ├── providers.tsx             # TanStack Query client provider
│   ├── page.tsx                  # Route: / — Home / UPC input form
│   ├── paper/
│   │   └── [upc]/
│   │       ├── page.tsx          # Route: /paper/:upc — Paper overview
│   │       └── unit/
│   │           └── [unitId]/
│   │               └── page.tsx  # Route: /paper/:upc/unit/:unitId — Unit view (THE main reading page)
│   └── pipeline/
│       └── [upc]/
│           └── page.tsx          # Route: /pipeline/:upc — Live generation progress
├── components/
│   ├── notes/                    # 15 note-field rendering components
│   │   ├── RapidRevisionCard.tsx
│   │   ├── DefinitionBlock.tsx
│   │   ├── CoreConceptBlock.tsx
│   │   ├── ExampleBlock.tsx
│   │   ├── DiagramBlock.tsx
│   │   ├── ExaminersNoteBlock.tsx
│   │   ├── CommonMistakesBlock.tsx
│   │   ├── AnswerWritingTechniqueBlock.tsx
│   │   ├── PYQBlock.tsx
│   │   ├── QuickChecksBlock.tsx
│   │   ├── ConnectsToBlock.tsx
│   │   ├── FormulaSheet.tsx
│   │   ├── DiagramReferenceSheet.tsx
│   │   ├── KeyTermsSheet.tsx
│   │   └── ProblemSet.tsx
│   ├── ui/                       # 6 shared utility/status components
│   │   ├── FieldFlagButton.tsx
│   │   ├── VerifiedBadge.tsx
│   │   ├── TierBadge.tsx
│   │   ├── PartialDeliveryNotice.tsx
│   │   ├── PYQSubmissionBanner.tsx
│   │   └── Last4HoursToggle.tsx
│   └── pipeline/                 # 3 pipeline monitoring components
│       ├── PipelineProgressView.tsx
│       ├── AgentStatusCard.tsx
│       └── UnitProgressBar.tsx
├── lib/
│   ├── supabase.ts               # Supabase anon-key browser client singleton
│   ├── queries.ts                # All reads, writes, realtime subscriptions
│   ├── katex.ts                  # KaTeX rendering utility (3 functions)
│   └── sessions.ts               # localStorage session management
└── types/
    └── database.ts               # TypeScript interfaces for DB rows
```

---

## 2. Page Routes — Complete Rendering Logic

### Route 1: `/` — Home Page

**File:** [`app/page.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/app/page.tsx)  
**Mode:** `"use client"` — client-only (no SSR needed)  
**State:** `upc: string`, `loading: bool`, `error: string`

**UX Flow:**

```
User types UPC → submit →
    getPaper(upc) [lib/queries.ts]
        ↓
    Paper exists?
        YES → router.push('/paper/:upc')          [already generated]
        NO  → fetch POST localhost:8000/generate   [trigger backend]
              router.push('/pipeline/:upc')         [watch generation]
                (if backend unreachable → still routes to /pipeline, error logged to console only)
```

**Error handling on this page:**
- Backend unreachable → silent `console.error`, does NOT block routing. The pipeline page will display "units not loaded yet"
- `getPaper` Supabase error → `error` state shown inline with `<p className="text-destructive">`
- Empty UPC → button disabled via `!upc.trim()`

**Why this matters for personal use:** I can just run `npm run dev` on one terminal and the FastAPI server on another. The two are completely decoupled — the frontend doesn't care if the backend is slow to start.

---

### Route 2: `/pipeline/:upc` — Live Generation Progress

**File:** `app/pipeline/[upc]/page.tsx` → **renders `<PipelineProgressView upc={upc} />`**

This page exists for one reason: to show me what the pipeline is doing while I wait. I don't need to `curl` the backend or check logs — this page tells me exactly which agent is running and which units have finished.

**Complete PipelineProgressView logic** ([`PipelineProgressView.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/pipeline/PipelineProgressView.tsx)):

```
useEffect (on mount) →
    1. getUnitsForPaper(upc)     → initial unit list (polling fallback baseline)
    2. setInterval(3000ms)       → polling fallback: re-fetches and merges unit data
    3. subscribeToUnitStatus()   → Supabase Realtime: immediate on status change

    When allUnitsCompleted === true:
        setTimeout(3000ms) → router.push('/paper/:upc')  [auto-redirects to paper overview]
```

**Agent status computation** (derived from unit data, NOT from a backend status endpoint):
```javascript
// Inferred entirely from whether units exist and are complete:
hasUnits    = units.length > 0
anyComplete = units.some(u => u.status === 'complete')
allComplete = completedUnits === totalUnits

Agent 1:  always 'complete'   (Decoder just reads registry — instant)
Agent 2:  hasUnits ? 'complete' : 'running'
Agent 3:  hasUnits ? 'complete' : 'queued'
Agent 4:  hasUnits ? 'complete' : 'queued'
Agent 5:  allComplete ? 'complete' : (hasUnits ? 'running' : 'queued')
Agent 6:  allComplete ? 'complete' : (anyComplete ? 'running' : 'queued')
Agents 7–9:  allComplete ? 'complete' : 'queued'
Agents 10–12: allComplete ? 'complete' : 'queued'
```

**Key design decision:** The agent status is an **approximation** computed from unit row status — it is NOT read from a separate "agent status" table. This is intentional for personal use (simpler, no extra table needed). The approximation is good enough since I can see which units are completing in real time.

---

### Route 3: `/paper/:upc` — Paper Overview

**File:** [`app/paper/[upc]/page.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/app/paper/%5Bupc%5D/page.tsx) (248 lines)  
**Mode:** `"use client"` — subscribes to Realtime

**What it fetches on load:**
1. `getPaper(upc)` → paper metadata (name, department, tier, pyq_years_available)
2. `getUnitsForPaper(upc)` → all unit rows with status
3. `subscribeToUnitStatus(upc)` → live updates if any unit changes status while I'm on this page

**Renders per unit based on `unit.status`:**

| Unit status | What renders |
|---|---|
| `complete` | `<Link>` card → navigates to `/paper/:upc/unit/:unitId` |
| `generating` | Dimmed card with `<Loader2 animate-spin>` + "Generating..." badge |
| `queued` | Dimmed card with "Queued..." badge |
| `failed` | `<PartialDeliveryNotice status="failed" retryAvailable={true} />` |

**Additional renders on this page:**
- `<TierBadge tier={tier} pyqYearsAvailable={count} />` — always visible in header
- `<PYQSubmissionBanner />` — only if `tier === 3 || tier === 4`
- `<Last4HoursToggle />` — exam prep mode toggle (currently visual only, state tracked in `isLast4Hours`)
- PYQ year pills from `paper.pyq_years_available[]`
- Syllabus link (if `paper.syllabus_url` not null)

---

### Route 4: `/paper/:upc/unit/:unitId` — Unit Reading Page (The Core Product)

**File:** [`app/paper/[upc]/unit/[unitId]/page.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/app/paper/%5Bupc%5D/unit/%5BunitId%5D/page.tsx) (258 lines)  
**Mode:** `"use client"`  
**State:** `unit`, `topics[]`, `formulaSheets[]`, `problemSet`, `loading`, `expandedTopicId`

**What it fetches on load:**
```javascript
getUnitsForPaper(upc)         → finds current unit by ID (gets conceptual_summary, status)
getTopicsForUnit(unitId)      → all topics ordered by topic_number
getFormulaSheetsForUnit(unitId) → formula/diagram/key_terms sheets
getProblemSetForUnit(unitId)  → problem set (if exists)
```

**Topic render order** (exact order in JSX, rendered as a `<section>` per topic):
```
1.  RapidRevisionCard          (if rapid_revision exists)
2.  DefinitionBlock            (if definition exists)
3.  CoreConceptBlock           (if core_concept exists)
4.  ExampleBlock               (if examples.length > 0)
5.  DiagramBlock               (if diagram_block exists)
6.  ExaminersNoteBlock         (if examiners_note exists)
7.  CommonMistakesBlock        (if common_mistakes.length > 0)
8.  AnswerWritingTechniqueBlock (if answer_writing_technique exists)
9.  PYQBlock                   (if pyqs.length > 0)
10. QuickChecksBlock           (if quick_checks.length > 0)
11. ConnectsToBlock            (if connects_to.topic_id exists)
```

**Unit-level resources rendered after all topics:**
```
FormulaSheet        (if sheet.sheet_type === 'formula')
DiagramReferenceSheet (if sheet.sheet_type === 'diagram_reference')
KeyTermsSheet       (if sheet.sheet_type === 'key_terms')
ProblemSet          (if problemSet exists)
```

**Topic ID in anchor:** Each topic `<section>` has `id="topic-${topic.topic_id}"` — this enables ConnectsToBlock's deep links (`/paper/:upc/unit/:unitId#topic-:topicId`) to scroll directly to the target topic when navigating cross-unit.

---

## 3. The 15 Note Field Components — Deep Specification

All 15 components live in `components/notes/`. Every single one:
- Returns `null` if its primary data field is null/empty (no renders empty containers)
- Accepts `topicId: string` and renders `<FieldFlagButton fieldName="..." topicId={topicId} />` in its header
- Uses `dangerouslySetInnerHTML={{ __html: renderMath(text) }}` for any text that may contain LaTeX

---

### 1. `RapidRevisionCard.tsx` — The Entry Point to Every Topic

**File:** [`RapidRevisionCard.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/RapidRevisionCard.tsx) (68 lines)

**Purpose:** The first thing rendered for each topic. Functions as the topic header AND a quick-reference card simultaneously. Clicking it toggles the full topic expansion (via `isExpanded`/`onToggle` props, currently tracked by `expandedTopicId` in parent).

**Props:**
```typescript
rapid_revision: {
  definition_one_line: string   // < 15 words. Rendered with renderMath()
  key_formula_or_concept: string // Primary LaTeX expression. Rendered with renderMath() in font-mono text-accent
  examiner_pattern: string      // Exact instruction word + phrasing. Rendered italic/muted
}
topic_name: string
topicId: string
priority: 'high' | 'medium' | 'low' | 'never_asked'
isExpanded: boolean
onToggle: () => void
```

**Visual encoding of priority (left border + background):**
| Priority | CSS classes |
|---|---|
| `high` | `border-l-red-500 bg-red-500/5` |
| `medium` | `border-l-amber-500 bg-amber-500/5` |
| `low` | `border-l-slate-400 bg-slate-500/5` |
| `never_asked` | `border-l-slate-200 bg-transparent opacity-75` |

**Label shown in top-right:**
`HIGH YIELD` / `MEDIUM YIELD` / `LOW YIELD` / `NOT EXAMINED`

**Current limitation:** `isExpanded` prop is received but NOT used to conditionally show/hide the rest of the topic. The toggle controls only the card's styling — the full topic is always rendered. This is intentional for the current personal-use phase: everything is always visible.

---

### 2. `DefinitionBlock.tsx` — The 2-Mark Answer

**File:** [`DefinitionBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/DefinitionBlock.tsx) (29 lines)

**Purpose:** Renders the Agent 5 `definition` field — guaranteed ≤ 40 words with all math in LaTeX. This is exactly what I write for a 2-mark "define X" question. Nothing more, nothing less.

**Renders:** Label "Definition" + `<p dangerouslySetInnerHTML={{ __html: renderMath(definition) }}>`

**Design:** `bg-card/50 rounded-md border border-border/50` — subtle, card-like, deliberately not attention-grabbing. The definition is plain and clinical because that's what examiners want.

---

### 3. `CoreConceptBlock.tsx` — The Human Understanding Layer

**File:** [`CoreConceptBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/CoreConceptBlock.tsx) (44 lines)

**Purpose:** Renders `core_concept` (plain language explanation, no assumed knowledge) + optional `analogy` with a trust signal.

**Analogy trust signal:**
```jsx
{!analogy_verified && <span className="text-warning">⚠️ Unverified</span>}
```
When `analogy_verified = false` (Agent 5 self-flagged it as plausible but not factually certain), a warning shows. When `analogy_verified = true` (Agent 5 confirmed it's factually accurate), no warning — just the analogy.

**Separator:** Analogy is separated from core_concept by `border-t border-border/50` + "Think of it this way:" label.

---

### 4. `ExampleBlock.tsx` — Worked Examples with Verification

**File:** [`ExampleBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/ExampleBlock.tsx) (84 lines)

**Purpose:** Renders the `examples[]` array. Each example has full step-by-step working, an answer box, a verification badge, and a common error callout.

**Conditional step rendering:** Steps only show if `paper_type === 'numerical' || paper_type === 'mixed'`. For `theory` and `life_sciences` papers, only `example.content` is shown (no numbered steps).

**Answer box:** If `example.answer_boxed === true` (always true for numerical by Agent 5 rule), the answer renders inside a bordered, centred box:
```jsx
<div className="p-4 border-2 border-accent/20 bg-accent/5 rounded-md inline-block min-w-full text-center">
```

**`<VerifiedBadge>` placement:** Top-right of each example card, showing verification state from Agent 7.

**Common error:** Rendered in `bg-warning/10 border border-warning/20` amber callout at the bottom of each example — distinct visual so I notice it while solving.

---

### 5. `DiagramBlock.tsx` — SVG Diagrams with Exam Instructions

**File:** [`DiagramBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/DiagramBlock.tsx) (124 lines — largest notes component)

**Purpose:** Renders `diagram_block` JSONB from DB. Three rendering modes:

| `diagram_block` field | What renders |
|---|---|
| `svg_code` present | `dangerouslySetInnerHTML={{ __html: svg_code }}` — inline SVG rendered directly |
| `svg_file_path` present | `<img src={svg_file_path}>` — loads from Supabase storage or CDN |
| Neither present | Placeholder: "Placeholder for: {diagram_name}" |

**Labeled parts:** Renders as a `grid-cols-2` list below the SVG. Each part shows:
- `{idx+1}. {part_name}` (bold)
- `{explanation}` (muted, with renderMath)
- `DU label: {du_expected_label}` (accent mono — exact text DU expects in exam diagram labels)

**"How to draw in exam" accordion:** Collapsible via `instructionsOpen` state. Shows `draw_instructions` text. This is the Agent 5 field telling me exactly how to draw this diagram step-by-step in 10 minutes in the exam hall.

**Screenshot capture:** `html2canvas` captures the `containerRef` div (includes SVG + labeled parts) and downloads as PNG file named `StudyAI_Diagram_{diagram_name}.png`. I can paste this directly into my revision notes.

**Source citation:** If `source_book`, `source_edition`, `source_page` are set → rendered as `Source: Book Title, Edition, p.42` in bottom-right italic.

---

### 6. `ExaminersNoteBlock.tsx` — The Exam Intelligence Block

**File:** [`ExaminersNoteBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/ExaminersNoteBlock.tsx) (64 lines)

**Purpose:** The most exam-critical block. Renders `examiners_note` (what the DU examiner looks for) + PYQ year pills + instruction word frequency table.

**Year pill injection (inline text transformation):**
```javascript
examiners_note_pyq_refs.forEach(year => {
  const pill = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs ...">[$year]</span>`;
  formattedNote = formattedNote.replace(new RegExp(year, 'g'), pill);
});
```
The note text itself references years like "This appeared in 2024 for 6 marks" — and the year numbers are automatically converted into clickable-looking pills inline. No separate citation block needed.

**Instruction word frequency bar:**
```jsx
// "DU says:" → [ find (×2) ] [ prove (×1) ] [ state (×3) ]
Object.entries(instruction_word_frequency).map(([word, count]) => (
  <span>
    {word} <span className="text-accent font-mono">(×{count})</span>
  </span>
))
```

**Visual design:** `bg-accent/5 border border-accent/20` — warm accent tint to make this block feel like the most important thing on the page.

---

### 7. `CommonMistakesBlock.tsx` — What Loses Marks

**File:** [`CommonMistakesBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/CommonMistakesBlock.tsx) (47 lines)

**Purpose:** 1–3 DU-specific common mistakes, each with exact marks impact.

**Visual:** `bg-red-500/5 border border-red-500/10` — the only red-tinted block in the entire UI. The colour is intentional: this is where marks are lost.

**Marks impact pill:** `bg-red-500/10 text-red-500/80` — e.g. "-2 marks if units not shown" rendered as a distinct pill on the right of each mistake.

---

### 8. `AnswerWritingTechniqueBlock.tsx` — The 6-Mark Blueprint

**File:** [`AnswerWritingTechniqueBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/AnswerWritingTechniqueBlock.tsx) (71 lines)

**Purpose:** Renders the `answer_writing_technique` object — ONLY present for topics where Agent 5 judged them as 6+ mark topics. Returns `null` if `!answer_writing_technique.applicable`.

**Three sub-sections (each conditionally rendered):**

1. **Structure** (`structure: string[]`) — Numbered `<ol>` list of what to write sentence-by-sentence. Each item rendered with `renderMath()` since steps may contain LaTeX.

2. **Marks Distribution** (`marks_distribution: Record<string, string>`) — Flex-wrapped pills showing `PartName: Marks`. Example: `Definition: 2` | `Derivation: 3` | `Units: 1`.

3. **Word Count Target** (`word_count_target?: number`) — Italic: `Target: ~{N} words`. Only for theory topics; numerical topics have `null`.

**Min marks threshold badge:** Shows `{threshold}+ marks` — tells me "this technique applies when the question is worth X or more marks".

---

### 9. `PYQBlock.tsx` — Verbatim Past Year Questions

**File:** [`PYQBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/PYQBlock.tsx) (78 lines)

**Purpose:** Renders all past year questions for this topic — exact verbatim text extracted from PDFs by Agent 2C.

**Year confirmation badge:**
```jsx
// GREEN with CheckCircle2 if confirmed, GREY with ~ if unconfirmed:
<span className={pyq.year_confirmed ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'}>
  {pyq.year_confirmed ? <CheckCircle2 /> : '~'} {pyq.year} DU Exam
</span>
```

**"Most Recent" highlight:** If `pyq.recency_weight >= 1.5` → shows `MOST RECENT` accent pill. This is the question that appeared in the most recent exam — highest study priority.

**Key steps:** `pyq.key_steps[]` rendered as `→ step` list below the question text. These are not answers — they are the key points the examiner expects to see.

**Source attribution:** Every PYQ shows `Source: {source}` or `Student submitted` at bottom-right italic.

---

### 10. `QuickChecksBlock.tsx` — Self-Testing Field

**File:** [`QuickChecksBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/QuickChecksBlock.tsx) (43 lines)

**Purpose:** 3 questions for self-testing. No answers provided in the component (by strict Agent 5 rule). The user types their answer in an `<input>` below each question and checks against their notes manually.

**Input element:** Each question renders a live `<input type="text" className="w-full...">` below it with placeholder `"Type your answer here..."` and hint `"Check against your notes"`. The input values are NOT saved anywhere — they are ephemeral study tools.

**Visual design:** `border-2 border-dashed border-border/80` — the dashed border signals "interactive area" distinct from all other read-only content blocks.

---

### 11. `ConnectsToBlock.tsx` — Cross-Topic Navigation

**File:** [`ConnectsToBlock.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/ConnectsToBlock.tsx) (36 lines)

**Purpose:** Renders a clickable link at the bottom of a topic pointing to the next logical topic (as determined by Agent 4's mental model map). Returns null if `connects_to_topic_id || connects_to_unit_id` is null.

**URL generated:**
```javascript
const url = `/paper/${upc}/unit/${connects_to_unit_id}#topic-${connects_to_topic_id}`;
```
This navigates to the target unit page AND scrolls to the exact topic via the `#topic-{id}` fragment. Cross-unit navigation works because every topic section has `id="topic-{topicId}"`.

**Visual:** Hover on `<Link>` → `ArrowRight` turns accent colour + translates right `1px`. Shows `connects_to_reason` as subtitle.

---

### 12. `FormulaSheet.tsx` — Printable Formula Reference

**File:** [`FormulaSheet.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/FormulaSheet.tsx) (83 lines)

**Purpose:** Renders the unit-level formula sheet from `formula_sheets` table where `sheet_type === 'formula'`. Only renders if `sheet.content` is a non-empty array.

**Content format:** `FormulaItem[]` from `sheet.content` JSONB:
```typescript
{ item: string; application_condition: string; marks_value?: string; }
```

Each formula is rendered:
- Large centred display: `dangerouslySetInnerHTML={{ __html: renderMath(item.item) }}` — full KaTeX display rendering
- Below: italic "Condition: {application_condition}"
- Top-right corner: marks badge if `marks_value` exists

**PNG capture:** `html2canvas(containerRef.current, { backgroundColor: '#ffffff' })` captures the entire sheet with proper white background for printing. Downloaded as `StudyAI_{unitName}_FormulaSheet.png`.

**White background override:** The capturable `<div>` uses `bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100` — ensures good contrast in both light and dark mode when saved as image.

---

### 13. `DiagramReferenceSheet.tsx` — Printable Diagram Checklist

**File:** [`DiagramReferenceSheet.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/DiagramReferenceSheet.tsx) (83 lines)

**Purpose:** Renders `sheet_type === 'diagram_reference'` from `formula_sheets` table. A quick-reference list of all examinable diagrams in the unit with their key labels.

**Content format:** `DiagramReferenceItem[]`:
```typescript
{ diagram_name: string; labeled_parts_summary: string; marks_value?: string; }
```

**Grid:** `grid-cols-1 md:grid-cols-2` — each diagram gets a card with name, key labels summary, and marks badge. No actual SVG here — just text reference for rapid revision.

**Same PNG capture as FormulaSheet**, named `StudyAI_{unitName}_Diagrams.png`.

---

### 14. `KeyTermsSheet.tsx` — Printable Key Terms Reference

**File:** [`KeyTermsSheet.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/KeyTermsSheet.tsx) (72 lines)

**Purpose:** Renders `sheet_type === 'key_terms'` — a glossary of technical terms for the unit.

**Content format:** `KeyTermItem[]`:
```typescript
{ term: string; summary: string; }
```

**Grid:** `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` — compact 3-column layout optimised for dense reading / printing.

**Same PNG capture pattern**, named `StudyAI_{unitName}_KeyTerms.png`.

---

### 15. `ProblemSet.tsx` — Reveal-on-Demand Problem Set

**File:** [`ProblemSet.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/notes/ProblemSet.tsx) (124 lines)

**Purpose:** Renders the `problem_sets` table row for this unit — a curated list of problems (PYQ + textbook) with hidden-by-default answers. This is the active practice component.

**State:** `revealed: Record<number, boolean>` — tracks which problem answers are revealed. Starts all hidden.

**Per-question render:**
- Question header: Q number + source badge (`2024 DU Exam` or `Textbook: {book}, Ex.{exercise}`) + marks badge
- Question text: `font-serif leading-relaxed` (matches PYQ style — feels like the actual paper)
- Answer toggle button: Eye/EyeOff icon — "Answer" / "Hide"
- Revealed answer section: `animate-in fade-in slide-in-from-top-2 duration-300` — smooth reveal animation

**Answer formats:**
- If `answer.steps[]` → numbered step-by-step with renderMath on each step
- Else → `answer.full_answer` as paragraph (for theory questions)
- `answer.word_count` → italic "~N words to DU standard"
- `answer.common_error_callout` → amber callout: "Common Pitfall: ..."

---

## 4. The 6 Shared UI Components

### `FieldFlagButton.tsx` — Content Quality Flag

**File:** [`FieldFlagButton.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/FieldFlagButton.tsx) (18 lines)

**Current state:** MVP implementation. The button is rendered on every component that has content (15 note components, all use it). On click: `console.log('Flag clicked:', fieldName, topicId)` — **the Supabase write is not yet wired up.**

**Hover-reveal pattern:** `opacity-0 group-hover:opacity-100` — the flag icon is invisible until I hover the parent container (which must have `className="...group"`). Every note component's wrapper div has `group` — verified in all 15 files.

**Full implementation path** (when ready to connect):
```javascript
// Should call: flagField({ topicId, fieldName, issue, sessionId }) from lib/queries.ts
// Then: incrementFlagCount(upc) from lib/sessions.ts to track rate limit
```

**Rate limit system** (already built in `sessions.ts`): `FLAG_LIMIT = 10` per UPC per browser session.

---

### `VerifiedBadge.tsx` — Agent 7 Verification Signal

**File:** [`VerifiedBadge.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/VerifiedBadge.tsx) (30 lines)

**Shows only if `verified === true` (Agent 7 ran on this example).** Returns `null` if `!verified`.

**Three states:**
| `verificationPassed` | `verificationMode` | Icon | Meaning |
|---|---|---|---|
| `false` | any | `AlertCircle` (warning amber) | Agent 7 ran but flagged an error |
| `true` | `numerical_dual` | `CheckCheck` (double tick, success) | Both intermediate + final answer verified |
| `true` | anything else | `Check` (single tick, success) | Answer verified |

**Hover tooltip:** `title="Mode: {verificationMode}"` — shows exactly which verification mode was used.

---

### `TierBadge.tsx` — Documentation Trust Signal

**File:** [`TierBadge.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/TierBadge.tsx) (41 lines)

**Props:** `tier: 1 | 2 | 3 | 4`, `pyqYearsAvailable?: number`

**Four tiers, four colours:**
| Tier | Border/Text Colour | Label | Description |
|---|---|---|---|
| 1 | Green | `Tier 1 — Fully Calibrated` | N NEP question papers available. All exam-verified. |
| 2 | Amber | `Tier 2 — Partially Calibrated` | 1 question paper. Some content estimated. |
| 3 | Orange | `Tier 3 — Syllabus Based` | No NEP papers publicly available. |
| 4 | Red | `Tier 4 — Insufficient Data` | Notes cannot be generated. |

**Tooltip behaviour:** `showTooltip` state toggles on `onMouseEnter`/`onMouseLeave` + `onClick`. Tooltip div: `animate-in fade-in zoom-in-95 duration-200` — smooth popup showing the full description text.

---

### `PartialDeliveryNotice.tsx` — Failed/Generating Unit Placeholder

**File:** [`PartialDeliveryNotice.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/PartialDeliveryNotice.tsx) (41 lines)

**Props:** `unitName: string`, `status: 'failed' | 'generating'`, `retryAvailable: boolean`

**Two states:**
| `status` | Icon | Message |
|---|---|---|
| `generating` | `Loader2 animate-spin` | "Unit X is generating. Check back shortly. Page will update automatically." |
| `failed` | `AlertCircle opacity-50` | "Unit X could not be generated and has been flagged for manual review." |

When `retryAvailable === true` and `status === 'failed'`: Shows `<button>` with `RefreshCw` icon — "Retry Generation". (Currently logs to console; wiring to `/generate/rerun` endpoint is the next step.)

---

### `PYQSubmissionBanner.tsx` — Tier 3/4 Content Unlock

**File:** [`PYQSubmissionBanner.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/PYQSubmissionBanner.tsx) (50 lines)

**Props:** `upc: string`, `paperName: string`, `tier: 3 | 4`

**Renders only on paper overview page when `tier === 3 || tier === 4`.** Shows: "Help improve {paperName} — No NEP question papers are publicly available."

**File capture button:** Triggers `<input type="file" accept="image/*" capture="environment">` — mobile camera capture. On file selected: `console.log('File captured for', upc, file)` — **Supabase Storage upload not yet wired.**

**Full implementation path** (when ready):
```javascript
// Upload to Supabase Storage → get fileUrl
// Call: submitPYQ({ upc, yearTaggedByStudent, fileUrl, sessionId, rewardType }) from lib/queries.ts
// Call: unlockPaper(upc) from lib/sessions.ts on reward_issued === true
```

---

### `Last4HoursToggle.tsx` — Exam Mode Toggle

**File:** [`Last4HoursToggle.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/ui/Last4HoursToggle.tsx) (24 lines)

**Props:** `isActive: boolean`, `onToggle: () => void`

**Current state:** Visual only. The `Clock` icon pulses (`animate-pulse`) when active. The button turns full accent colour with shadow.

**Intended behaviour (not yet implemented):** When active, the paper overview filters/highlights units by study priority — showing only topics tagged `high` or those appearing in the most recent PYQ year. This is the "4 hours before exam" mode where I want only what matters most.

---

## 5. The 3 Pipeline Components

### `PipelineProgressView.tsx` — The Generation Dashboard

Already documented fully in Route 2. Key facts:
- 12 `AgentStatusCard` components rendered in `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- 1 `UnitProgressBar`
- "Ready to Read" section at bottom — live-updating list of completed unit links
- Auto-redirects to `/paper/:upc` 3 seconds after all units complete

### `AgentStatusCard.tsx` — Individual Agent Status

**File:** [`AgentStatusCard.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/pipeline/AgentStatusCard.tsx) (40 lines)

**Four status states:**
| Status | Icon | Background |
|---|---|---|
| `queued` | `Circle` muted 50% opacity | `bg-muted/30` |
| `running` | `Loader2 animate-spin` accent | `bg-accent/10 border-accent/30` |
| `complete` | `CheckCircle2` success | `bg-success/10 border-success/30` |
| `failed` | `XCircle` destructive | `bg-destructive/10 border-destructive/30` |

Shows: `Agent {N} — {name}` + `{model}` as subtitle.

### `UnitProgressBar.tsx` — Per-Unit Status Bar

**File:** [`UnitProgressBar.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/components/pipeline/UnitProgressBar.tsx) (46 lines)

**Horizontal segmented progress bar:** One segment per unit, `flex-1` (equal width regardless of unit count).

**Segment colours:**
| Status | CSS |
|---|---|
| `complete` | `bg-success` |
| `failed` | `bg-destructive` |
| `generating` | `bg-accent animate-pulse` |
| `queued` | `bg-muted-foreground/20` |

Hover tooltip: `title="Unit N: {name} ({status})"` — exact status per segment on hover.
Counter: `{completed} / {total} ({percentage}%)`.

---

## 6. The KaTeX Rendering Pipeline

**File:** [`lib/katex.ts`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/lib/katex.ts) (88 lines)

Three exported functions — all using KaTeX with `throwOnError: false` (never crashes the UI):

### `renderMath(text: string): string`
**The primary function.** Called by every note component via `dangerouslySetInnerHTML`.

**Algorithm:**
```
1. if !text → return ""
2. if !isMathContent(text) → return text as-is (skip KaTeX entirely — performance optimisation)
3. Replace $$...$$ first → katex.renderToString(latex, { displayMode: true })
4. Replace $...$ (not $$) → katex.renderToString(latex, { displayMode: false })
5. Return HTML string
```

**Delimiter detection:** `isMathContent(text)` = `/\$/.test(text)` — if no `$` in the string, KaTeX is skipped entirely. Most definition/concept text is plain English and skips KaTeX without any regex cost.

**On any KaTeX parse error:** Returns the original `_match` string unchanged (LaTeX source visible rather than blank). Since `throwOnError: false`, this is a visual-only fallback.

### `renderInline(latex: string): string`
**For pure LaTeX expressions** (e.g. the `key_formula_or_concept` field which is known to be 100% LaTeX). Wraps as inline math, no delimiter scanning.

### `renderDisplay(latex: string): string`
**For display-mode LaTeX** (block equations). Wraps as display math. Used for centred answer boxes in `ExampleBlock` and `FormulaSheet`.

---

## 7. Client-Side Session Management

**File:** [`lib/sessions.ts`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/lib/sessions.ts) (148 lines)

**Storage:** `localStorage` only. Two keys:
- `studyai_session_id` — UUID string, persisted across visits
- `studyai_session_data` — JSON blob of `SessionData`

```typescript
interface SessionData {
  sessionId: string;
  flagCounts: Record<string, number>; // upc -> count of flags submitted
  flaggedPapers: string[];            // upcs where I've submitted flags
  unlockedPapers: string[];           // tier 3/4 papers unlocked via PYQ submission reward
}
```

**SSR safety:** All functions check `typeof window !== 'undefined'`. On server → returns `"ssr-placeholder"` or default data. This ensures Next.js SSR doesn't crash on `localStorage` access.

**Flag rate limit:** `FLAG_LIMIT = 10` per UPC. `incrementFlagCount(upc)` returns `false` if limit hit. No API calls made when limit is exceeded.

**Paper unlock system:** `isPaperUnlocked(upc, tier)` — Tier 1/2 always `true`. Tier 3/4 requires `upc` to be in `unlockedPapers[]`.

**UUID generation:** Uses `crypto.randomUUID()` when available (all modern browsers), with a manual fallback for edge cases.

---

## 8. The Realtime + Polling Dual-Subscription Strategy

**Files involved:** `lib/queries.ts` (subscriptions), `PipelineProgressView.tsx` (dual strategy), `app/paper/[upc]/page.tsx` (Realtime only)

### How it Works

**Supabase Realtime (primary):**
```javascript
// queries.ts
supabase
  .channel(`units:upc:${upc}`)
  .on('postgres_changes', { event: '*', table: 'units', filter: `upc=eq.${upc}` }, payload => {
    onUpdate(payload.new as Unit);
  })
  .subscribe();
```
This subscribes to **all PostgreSQL changes** (`INSERT`, `UPDATE`, `DELETE`) on the `units` table filtered by `upc`. When the backend Agent 5 calls `set_unit_status(unit_id, 'complete')`, Supabase broadcasts the row change via WebSocket to the frontend within ~100–500ms.

**Polling fallback (PipelineProgressView only):**
```javascript
const interval = setInterval(() => {
  getUnitsForPaper(upc).then(data => {
    setUnits(prev => {
      // Merge: only update if status changed or new unit appeared
      let changed = false;
      for (const d of data) {
        const idx = newUnits.findIndex(u => u.unit_id === d.unit_id);
        if (idx === -1) { newUnits.push(d); changed = true; }
        else if (d.status !== newUnits[idx].status) { newUnits[idx] = d; changed = true; }
      }
      return changed ? newUnits.sort(...) : prev;
    });
  });
}, 3000); // Every 3 seconds
```

**Merge logic is careful:** Polling only triggers a re-render if something actually changed (`changed === true`). If Realtime is working perfectly, polling silently no-ops every 3 seconds.

**Topic-level Realtime** (`subscribeToTopicStatus`): Same pattern but filtered on `unit_id`. Available in queries.ts but **not currently used in any page** — the Unit page does a one-time fetch on load (no live updates needed since topics don't change after `status === 'complete'`).

**Cleanup:** Both Realtime channels and polling intervals are cleaned up in `useEffect` return functions (`channel.unsubscribe()`, `clearInterval(interval)`, `isMounted = false`).

---

## 9. `lib/queries.ts` — Complete Function Inventory

**File:** [`lib/queries.ts`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/lib/queries.ts) (195 lines)

### Read Functions

| Function | Table | Query | Returns |
|---|---|---|---|
| `getPaper(upc)` | `papers` | `.eq('upc', upc).single()` | `Paper \| null` |
| `getUnitsForPaper(upc)` | `units` | `.eq('upc', upc).order('unit_number')` | `Unit[]` |
| `getTopicsForUnit(unitId)` | `topics` | `.eq('unit_id', unitId).order('topic_number')` | `Topic[]` |
| `getFormulaSheetsForUnit(unitId)` | `formula_sheets` | `.eq('unit_id', unitId)` | `FormulaSheet[]` |
| `getProblemSetForUnit(unitId)` | `problem_sets` | `.eq('unit_id', unitId).limit(1).single()` | `ProblemSet \| null` |

**Error handling:** All reads have `if (error) { console.error(); return null/[] }` — they never throw. A missing row returns `null` gracefully (e.g. `PGRST116` "no rows returned" for `getProblemSetForUnit` is explicitly caught and treated as `null`).

### Realtime Subscriptions

| Function | Channel name | Table | Filter |
|---|---|---|---|
| `subscribeToUnitStatus(upc, onUpdate)` | `units:upc:{upc}` | `units` | `upc=eq.{upc}` |
| `subscribeToTopicStatus(unitId, onUpdate)` | `topics:unit_id:{unitId}` | `topics` | `unit_id=eq.{unitId}` |

Both return `RealtimeChannel` — the caller is responsible for calling `.unsubscribe()` in cleanup.

### Write Functions

| Function | Table | What it inserts |
|---|---|---|
| `flagField({ topicId, fieldName, issue, sessionId })` | `field_flags` | Flag record + `status: 'open'` |
| `submitPYQ({ upc, yearTaggedByStudent, fileUrl, sessionId, rewardType, rewardPaperUpc? })` | `pyq_submissions` | PYQ record + `verification_status: 'pending'` |

Both writes `throw new Error(error.message)` if Supabase returns an error (unlike reads which swallow errors). This is intentional — writes must be reliable and the caller handles the thrown error.

---

## 10. Typography and Theme System

**File:** [`app/layout.tsx`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/app/layout.tsx), [`globals.css`](file:///c:/Users/lenovo/tanmay-projects/StudyAi/frontend/app/globals.css)

### Fonts
```javascript
// Two Google Fonts loaded via next/font (zero layout shift, preloaded):
const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
const playfair = Playfair_Display({ subsets: ['latin'], variable: '--font-serif' });
```

**Usage:**
- `font-sans` (Inter) — UI text, labels, metadata, everything except headings
- `font-serif` (Playfair Display) — Page titles (`text-4xl font-serif font-bold`), PYQ question text (`font-serif leading-relaxed`), problem set question text

The serif font on PYQ text is intentional: it visually matches how question papers look, making it easier to parse the question as I'd read it in the exam hall.

### CSS Variable Tokens
```css
/* --background, --foreground, --card, --accent, --muted, --border, 
   --success, --destructive, --warning, etc. */
```
All components use semantic CSS variables, never hard-coded colours. Dark mode / light mode can be switched by changing variable values — all component styles auto-adapt.

### Providers
```javascript
// app/providers.tsx
<QueryClientProvider client={queryClient}>
  {children}
</QueryClientProvider>
```
TanStack Query with `staleTime: 60 * 1000` — data stays fresh for 60 seconds. For personal use this means rapid navigation between unit pages re-uses cached data rather than refetching Supabase on every tab switch.

---

## 11. Failure and Error States — Every Pathway Documented

There are 7 distinct failure pathways in the frontend. Each has an exact visual treatment.

### Failure 1: Paper Not Found (`/paper/:upc` with invalid UPC)

**Trigger:** `getPaper(upc)` returns `null` (UPC not in `papers` table)  
**Renders:**
```jsx
<div className="min-h-screen flex flex-col items-center justify-center">
  <AlertCircle className="w-12 h-12 text-destructive mb-4" />
  <h1>Paper Not Found</h1>
  <p>{error || "The requested UPC does not exist."}</p>
  <Link href="/">Return Home</Link>
</div>
```
**What I do:** Return to home, check the UPC, run `POST /generate` first.

---

### Failure 2: Unit Not Found (`/paper/:upc/unit/:unitId` with invalid unitId)

**Trigger:** `getUnitsForPaper(upc)` returns units but none match `unitId`  
**Renders:**
```jsx
<div className="min-h-screen flex items-center justify-center flex-col gap-4">
  <h1>Unit Not Found</h1>
  <Link href={`/paper/${upc}`}>Go back to paper</Link>
</div>
```
**What I do:** Navigate back to paper overview, click the correct unit.

---

### Failure 3: Unit Generation Failed (on Paper Overview)

**Trigger:** `unit.status === 'failed'` in the units list  
**Renders:** `<PartialDeliveryNotice status="failed" retryAvailable={true} />`

```
[AlertCircle] Unit 3: Probability Theory unavailable
This unit could not be generated and has been flagged for manual review.
All other completed units remain accessible.
[Retry Generation button]  ← currently logs to console only
```

**What I do (manual, current):** Run `POST /generate/rerun` with `{ upc, from_agent: 5 }` from terminal or Postman. The Retry button will eventually automate this.

---

### Failure 4: Unit Still Generating (on Paper Overview)

**Trigger:** `unit.status === 'generating' || unit.status === 'queued'`  
**Renders:**
```jsx
<div className="p-4 rounded-lg border border-border/50 bg-card/30 flex items-center justify-between">
  <div>Unit {N} / {unit_name} (dimmed)</div>
  <div className="text-accent bg-accent/10 px-3 py-1.5 rounded-full">
    <Loader2 animate-spin /> Generating...
  </div>
</div>
```
This is NOT an error — it's a live status. When the Realtime subscription fires a status update to `complete`, this card automatically transforms into a `<Link>` card without page reload.

---

### Failure 5: No Units at All

**Trigger:** `getUnitsForPaper(upc)` returns `[]`  
**Renders:**
```jsx
<div className="text-center p-8 bg-muted/30 rounded-lg border border-dashed">
  <p className="text-muted-foreground">No units found for this paper.</p>
</div>
```
**Likely cause:** Pipeline failed before Phase A completed (Agent 2 failed). Units were never seeded.  
**What I do:** Check backend logs, run pipeline again from Agent 1.

---

### Failure 6: Loading State (any page, while fetching Supabase)

**All three routes show the same loading state:**
```jsx
<div className="min-h-screen flex items-center justify-center">
  <Loader2 className="w-8 h-8 text-accent animate-spin" />
</div>
```
This renders from `if (loading || !upc)` — covers both the initial data fetch and the async param resolution from `params`.

---

### Failure 7: Backend Not Running (on Home page submit)

**Trigger:** `fetch('http://localhost:8000/generate', ...)` throws `TypeError: Failed to fetch`  
**Behaviour:**
```javascript
} catch (e) {
  console.error("Failed to trigger backend. Ensure FastAPI is running on port 8000.", e);
  // Still routes to /pipeline/:upc
}
```
No error shown to user. The page still routes to `/pipeline/:upc`. On the pipeline page, `getUnitsForPaper(upc)` returns `[]` (no units exist yet), so the progress grid shows all agents as `queued`.

**What I do:** Check that `uvicorn main:app --reload` is running in the backend terminal. The pipeline page will auto-populate as soon as units start appearing in Supabase.

---

### Failure 8: KaTeX Parse Error

**Trigger:** Agent 5 generates LaTeX that KaTeX cannot parse (e.g. missing `{`, unmatched delimiter)  
**Behaviour:**
```javascript
} catch {
  return _match; // Returns the original LaTeX source string, visible as raw text
}
```
The component renders the raw LaTeX source (e.g. `$\frac{x}{y`) as text. The page doesn't crash. I can flag the field using `FieldFlagButton` and later fix it via Agent 12's LaTeX auto-patch or a manual rerun.

---

## 12. Component Interaction Map — How Everything Connects

```
app/page.tsx (Home)
    │── getPaper() [queries.ts]
    │── POST /generate → localhost:8000 [FastAPI backend]
    └── router.push('/pipeline/:upc') or '/paper/:upc'

app/pipeline/[upc]/page.tsx → <PipelineProgressView>
    ├── getUnitsForPaper() [queries.ts] — initial fetch
    ├── subscribeToUnitStatus() [queries.ts] — Realtime WebSocket
    ├── setInterval(3000) — polling fallback
    ├── <AgentStatusCard> × 12 — derived status approximation
    ├── <UnitProgressBar> — derived from units[]
    └── "Ready to Read" link cards — live-updating completed units

app/paper/[upc]/page.tsx (Paper Overview)
    ├── getPaper() [queries.ts]
    ├── getUnitsForPaper() [queries.ts]
    ├── subscribeToUnitStatus() [queries.ts] — Realtime (no polling)
    ├── <TierBadge> [ui/]
    ├── <Last4HoursToggle> [ui/] — exam mode
    ├── <PYQSubmissionBanner> [ui/] — only Tier 3/4
    └── per unit:
        complete   → <Link> card
        generating → spinner card
        queued     → dimmed card
        failed     → <PartialDeliveryNotice> [ui/]

app/paper/[upc]/unit/[unitId]/page.tsx (Unit View — core reading)
    ├── getUnitsForPaper() → find current unit
    ├── getTopicsForUnit() [queries.ts]
    ├── getFormulaSheetsForUnit() [queries.ts]
    ├── getProblemSetForUnit() [queries.ts]
    └── per topic (in strict order):
        <RapidRevisionCard>        [notes/] ← renderMath, FieldFlagButton
        <DefinitionBlock>          [notes/] ← renderMath, FieldFlagButton
        <CoreConceptBlock>         [notes/] ← renderMath, analogy_verified signal
        <ExampleBlock>             [notes/] ← renderMath, VerifiedBadge, FieldFlagButton
        <DiagramBlock>             [notes/] ← SVG render, html2canvas capture
        <ExaminersNoteBlock>       [notes/] ← year pills, instruction_word_frequency
        <CommonMistakesBlock>      [notes/] ← red callout, marks impact
        <AnswerWritingTechniqueBlock> [notes/]
        <PYQBlock>                 [notes/] ← year_confirmed badge, recency_weight
        <QuickChecksBlock>         [notes/] ← self-test input boxes
        <ConnectsToBlock>          [notes/] ← deep link to next topic
    └── unit resources:
        <FormulaSheet>             [notes/] ← html2canvas PNG export
        <DiagramReferenceSheet>    [notes/] ← html2canvas PNG export
        <KeyTermsSheet>            [notes/] ← html2canvas PNG export
        <ProblemSet>               [notes/] ← reveal-on-demand answers
```

---

## 13. What's Built vs. What's Scaffolded

Since this is personal-use only (me, localhost, now), here is the honest state of the frontend:

### ✅ Fully Working (Verified in Code)
- Home → UPC input → backend trigger → pipeline route
- Pipeline live view with Realtime + polling dual strategy and auto-redirect
- Paper overview with live unit status updates via Realtime
- All 15 note components render correctly from DB data
- KaTeX rendering pipeline (`renderMath`, `renderInline`, `renderDisplay`)
- All 3 PNG capture/download features (DiagramBlock, FormulaSheet, DiagramReferenceSheet, KeyTermsSheet)
- TierBadge with tooltip
- VerifiedBadge with 3 states
- ConnectsToBlock deep links
- ProblemSet reveal-on-demand
- Session management (UUID, localStorage)
- Partial delivery notice (generating/failed states)

### 🟡 Scaffolded (UI exists, logic disconnected)
- `FieldFlagButton` — renders everywhere, click only logs to console. Not wired to `flagField()` in queries.ts
- `PYQSubmissionBanner` — file input works, upload not wired to Supabase Storage
- `PartialDeliveryNotice` Retry button — renders, click not wired to `/generate/rerun`
- `Last4HoursToggle` — visual state only, no filtering applied

### ❌ Not Yet Built (Schema exists, components scaffolded)
- Topic-level Realtime updates on Unit page (`subscribeToTopicStatus` exists in queries.ts, not called anywhere)
- Progressive topic reveal as pipeline runs (Unit page always fetches all topics at once on load)
- `problem_sets` and `formula_sheets` pipeline agents not yet writing data (tables exist, frontend ready to render)
- `groq_verdict` on field flags (DB column exists, review flow not built)

---

*This completes the full 3-phase StudyAI PRD. All three documents together constitute the complete technical specification of the system as it exists today — built exclusively from verified source code, schema files, and agent logic.*
