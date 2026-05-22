StudyAI — Phase 8: Frontend Construction
Complete Stage-by-Stage Build Reference
========================================

CREDENTIALS (reference these throughout every stage)
─────────────────────────────────────────────────────
Supabase Project URL   : https://hdtwmmtqfzeuozfgqntt.supabase.co


NOTE: The publishable key goes into NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local.
The secret key NEVER goes into the frontend. It is backend-only (FastAPI / server actions).
In the frontend, only the publishable key is used at all times.

========================================
OVERVIEW OF ALL 6 STAGES
========================================

Stage 8.1 — Project Foundation
Stage 8.2 — Lib Layer (data + render helpers)
Stage 8.3 — Note Components (15 components — the core product)
Stage 8.4 — UI Components (6 utility components)
Stage 8.5 — Pipeline Components (live pipeline view)
Stage 8.6 — Pages & Routing (4 pages, Realtime wired)

Strict build order. Each stage assumes the previous is complete.
Do not skip stages. Do not build 8.3 before 8.2 — components import from lib.

========================================
STAGE 8.1 — PROJECT FOUNDATION
========================================

Purpose:
  Lay the absolute base — config files, dependencies, env vars, and folder
  structure. Nothing from any later stage can exist without this.

Files to create:
  frontend/package.json
  frontend/next.config.ts
  frontend/tailwind.config.ts
  frontend/tsconfig.json
  frontend/.env.local
  frontend/.env.example
  frontend/.gitignore
  frontend/postcss.config.js

Dependencies to install (package.json):
  Core:
    next (latest)
    react
    react-dom
    typescript
    @types/react
    @types/react-dom
    @types/node

  Supabase:
    @supabase/supabase-js
    @supabase/ssr

  Styling:
    tailwindcss
    postcss
    autoprefixer
    framer-motion

  Math rendering:
    katex
    @types/katex
    react-katex          ← wrapper for KaTeX in React

  Data fetching:
    @tanstack/react-query

  Utility:
    clsx
    tailwind-merge
    lucide-react         ← icons throughout the UI
    html2canvas          ← formula sheet PNG export

.env.local contents:
  NEXT_PUBLIC_SUPABASE_URL=https://hdtwmmtqfzeuozfgqntt.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_1jwm0N9ZKtYga04Tz3FuXA_oJTYT0sN

  DO NOT add the secret key here. It is backend only.

.gitignore must include:
  .env.local
  .env*.local
  node_modules/
  .next/
  out/

tailwind.config.ts:
  Content paths: ./app/**/*.{ts,tsx}, ./components/**/*.{ts,tsx}, ./lib/**/*.{ts,tsx}
  Extend theme with:
    - Custom font families (display + body — not Inter, not Roboto)
    - Custom color tokens: background, surface, border, text-primary, text-muted,
      accent, accent-muted, success, warning, danger, tier-1 through tier-4
    - Custom border-radius tokens
    - Custom animation keyframes: pulse-soft, slide-up, fade-in, shimmer

next.config.ts:
  Enable: experimental.turbo (faster dev builds)
  Add KaTeX CSS to global styles via next/head or app layout

Folder structure to create (empty, ready for later stages):
  frontend/
  ├── app/
  │   ├── layout.tsx           ← root layout with providers
  │   ├── globals.css          ← global styles + KaTeX CSS import
  │   ├── page.tsx             ← placeholder (built in Stage 8.6)
  │   ├── paper/[upc]/
  │   │   ├── page.tsx         ← placeholder
  │   │   └── unit/[unitId]/
  │   │       └── page.tsx     ← placeholder
  │   └── pipeline/[upc]/
  │       └── page.tsx         ← placeholder
  ├── components/
  │   ├── notes/               ← 15 files (Stage 8.3)
  │   ├── pipeline/            ← 3 files (Stage 8.5)
  │   └── ui/                  ← 6 files (Stage 8.4)
  ├── lib/                     ← 4 files (Stage 8.2)
  └── types/
      └── database.ts          ← TypeScript types for every DB table

types/database.ts must define interfaces for:
  Paper, Unit, Topic, ProblemSet, FormulaSheet, PYQSubmission
  These must exactly match the Supabase schema column names and JSONB structures.
  All JSONB fields typed as specific interfaces, not `any`.

Completion check:
  [ ] `npm run dev` starts without errors
  [ ] Tailwind applies to a test element in app/page.tsx
  [ ] .env.local is present and not committed to git

========================================
STAGE 8.2 — LIB LAYER
========================================

Purpose:
  Build the 4 library files that every component imports from.
  No component should directly call Supabase or render KaTeX —
  all of that goes through these helpers.

Files to create:
  frontend/lib/supabase.ts
  frontend/lib/queries.ts
  frontend/lib/katex.ts
  frontend/lib/sessions.ts

─────────────────────────
lib/supabase.ts
─────────────────────────
Creates and exports the Supabase client (browser-side only).
Uses @supabase/ssr createBrowserClient.
Reads from NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.
Export a singleton: export const supabase = createBrowserClient(url, key)
This file is imported by both queries.ts and components that subscribe to Realtime.

─────────────────────────
lib/queries.ts
─────────────────────────
All database reads in one file. No component ever writes a raw Supabase query.
Every function is async, typed, and returns typed data or null on error.

Functions to implement:

  getPaper(upc: string): Promise<Paper | null>
    → SELECT * FROM papers WHERE upc = $1

  getUnitsForPaper(upc: string): Promise<Unit[]>
    → SELECT * FROM units WHERE upc = $1 ORDER BY unit_number ASC

  getTopicsForUnit(unitId: string): Promise<Topic[]>
    → SELECT * FROM topics WHERE unit_id = $1 ORDER BY topic_number ASC

  getFormulaSheetForUnit(unitId: string): Promise<FormulaSheet | null>
    → SELECT * FROM formula_sheets WHERE unit_id = $1 LIMIT 1

  getProblemSetForUnit(unitId: string): Promise<ProblemSet | null>
    → SELECT * FROM problem_sets WHERE unit_id = $1 LIMIT 1

  subscribeToUnitStatus(upc: string, onUpdate: (unit: Unit) => void): RealtimeChannel
    → Subscribe to Supabase Realtime on `units` table WHERE upc = $1
    → Fires onUpdate whenever a unit's status changes (generating → complete)
    → Returns the channel so the caller can unsubscribe on unmount

  subscribeToTopicStatus(unitId: string, onUpdate: (topic: Topic) => void): RealtimeChannel
    → Subscribe to `topics` table WHERE unit_id = $1

  flagField(params: { topicId, fieldName, issue, sessionId }): Promise<void>
    → INSERT INTO field_flags — stores a student flag for review

  submitPYQ(params: { upc, yearTaggedByStudent, fileUrl, sessionId, rewardType, rewardPaperUpc }): Promise<void>
    → INSERT INTO pyq_submissions

─────────────────────────
lib/katex.ts
─────────────────────────
KaTeX render helpers. All math rendering goes through here.
Every note component passes content through renderMath() before display.

Functions to implement:

  renderMath(text: string): string
    → Scans text for $...$ (inline) and $$...$$ (display) delimiters
    → Replaces each match with KaTeX-rendered HTML string
    → Uses katex.renderToString() with throwOnError: false
    → Returns full string with math replaced — safe to set as dangerouslySetInnerHTML

  renderInline(latex: string): string
    → Renders a single LaTeX expression as inline math
    → For use in components that know they're rendering pure math (RapidRevisionCard formula)

  renderDisplay(latex: string): string
    → Renders a single LaTeX expression as display (block) math
    → For use in ExampleBlock answer boxes

  isMathContent(text: string): boolean
    → Returns true if text contains $ or $$ delimiters
    → Used to decide whether to apply KaTeX processing at all (performance)

Note: Import KaTeX CSS in globals.css: @import 'katex/dist/katex.min.css'

─────────────────────────
lib/sessions.ts
─────────────────────────
Anonymous session management. No auth — just a persistent session ID in localStorage.
Used for: field flags rate limiting (max 10 per session), PYQ submission tracking,
  reward assignment, access control for Tier 3/4 papers.

Functions to implement:

  getOrCreateSessionId(): string
    → Check localStorage for 'studyai_session_id'
    → If none: generate UUID (crypto.randomUUID()), store it, return it
    → If exists: return it
    → SSR-safe: check typeof window !== 'undefined' before accessing localStorage

  getSessionData(): SessionData
    → Returns { sessionId, flagCount, flaggedPapers, unlockedPapers }
    → All stored in localStorage under 'studyai_session_data'

  incrementFlagCount(upc: string): boolean
    → Increments flag count for this paper in this session
    → Returns false if count already >= 10 (rate limit hit)
    → Returns true if flag is allowed

  unlockPaper(upc: string): void
    → Adds upc to unlockedPapers array in session data
    → Called when reward is granted (cross-paper credit)

  isPaperUnlocked(upc: string): boolean
    → Returns true for Tier 1/2 papers (always accessible)
    → Returns true for Tier 3/4 papers that are in unlockedPapers
    → Returns false for Tier 3/4 papers not yet unlocked

Completion check:
  [ ] supabase.ts exports a working client (test: fetch from papers table in console)
  [ ] queries.ts — getPaper('test-upc') returns null without crashing
  [ ] katex.ts — renderMath('$x^2$') returns a string containing <span class="katex">
  [ ] sessions.ts — getOrCreateSessionId() returns same ID on repeated calls

========================================
STAGE 8.3 — NOTE COMPONENTS
========================================

Purpose:
  Build all 15 components that render topic and unit content.
  This is the core product. Every database field renders through one of these.
  Every component must handle null/undefined data gracefully — pipeline may
  deliver partial content and the UI must never crash.

Design direction:
  Clean academic tool. Not flashy. Every visual decision serves focus and retention.
  Heavy typography hierarchy. Dense but scannable. Dark mode first.
  Components render as a vertical stack inside a topic card.

Common rules for ALL note components:
  - Accept props typed against types/database.ts — no `any`
  - Return null (not empty div) if required data is missing
  - All text content passes through renderMath() from lib/katex.ts
  - Every component has a FieldFlagButton trigger (prop: fieldName, topicId)
  - KaTeX CSS applied globally — components do not import it individually

─────────────────────────
RapidRevisionCard.tsx
─────────────────────────
Props: rapid_revision: { definition_one_line, key_formula_or_concept, examiner_pattern }
       topic_name: string
       priority: 'high' | 'medium' | 'low' | 'never_asked'
       isExpanded: boolean
       onToggle: () => void

Behaviour:
  - Always visible even when topic is collapsed
  - Three lines: definition one-liner, formula/concept (KaTeX), examiner pattern
  - Priority badge top-right: HIGH (red), MEDIUM (amber), LOW (grey), NOT EXAMINED (muted)
  - Tapping the entire card toggles the parent topic open/closed
  - Exam-morning primary use case: scanning all rapid cards across a unit in 2 minutes
  - Visual treatment: slightly elevated card, left border colour-coded by priority

─────────────────────────
DefinitionBlock.tsx
─────────────────────────
Props: definition: string, topic_name: string, topicId: string

Behaviour:
  - Distinct background (slightly lighter/darker than base surface)
  - Slightly larger font size than body — student's eye lands here first on open
  - Full KaTeX rendering
  - FieldFlagButton on hover/always-visible-mobile
  - Label: "DEFINITION" in small caps above the text

─────────────────────────
CoreConceptBlock.tsx
─────────────────────────
Props: core_concept: string, analogy?: string, analogy_verified: boolean, topicId: string

Behaviour:
  - analogy rendered in italics, visually separated (thin top border above it)
  - "Think of it this way:" prefix on analogy in muted colour
  - If analogy_verified is false: small unverified indicator (analogy still shows)
  - If no analogy: renders concept only, no empty space

─────────────────────────
ExampleBlock.tsx
─────────────────────────
Props: examples: Example[], paper_type: 'numerical' | 'theory' | 'mixed' | 'life_sciences'
       topicId: string

Each Example object: { type, content, steps, answer, answer_boxed, common_error,
                       verified, verification_mode, verification_passed }

Numerical mode:
  - Each step on its own numbered line
  - KaTeX throughout steps and answer
  - Final answer: if answer_boxed true → rendered in a box component (border + background)
  - VerifiedBadge top-right: single-check for verified, double-check for dual-verified
  - Common error: yellow/amber callout at bottom of example
  - verification_mode shown in VerifiedBadge tooltip

Theory/Biological mode:
  - Slightly indented block
  - Connection to PYQ pattern shown below as small note (from content field)
  - No step breakdown, no answer box

Multiple examples render as stacked blocks with clear Example 1, Example 2 labels.
Return null if examples array is empty.

─────────────────────────
DiagramBlock.tsx
─────────────────────────
Props: diagram_block: DiagramBlock | null, topicId: string

DiagramBlock object: { diagram_name, svg_source, svg_file_path, svg_code,
                       labeled_parts, marks_value, draw_instructions,
                       source_book, source_edition, source_page }

Behaviour:
  - If svg_code present: render inline SVG
  - If svg_file_path present: render as <img> (path relative to /public/diagrams/)
  - If neither: render placeholder with diagram_name (pipeline still generating)
  - Labeled parts: numbered list below SVG on mobile, beside on desktop (CSS grid)
  - Each part: part_name — explanation — "DU label: [du_expected_label]" in distinct colour
  - Draw instructions: collapsible callout, "How to draw in exam" as toggle label
  - Source citation: small muted text — "[source_book], [source_edition], p.[source_page]"
  - Screenshot button: uses html2canvas to capture the diagram + labels + citation as PNG
    white background, saved to camera roll / downloads
  - marks_value: small badge — "~[X] marks"
  - Return null if diagram_block is null

─────────────────────────
ExaminersNoteBlock.tsx
─────────────────────────
Props: examiners_note: string, examiners_note_pyq_refs: string[],
       instruction_word_frequency: Record<string, number>, topicId: string

Behaviour:
  - Most visually distinct component in the product
  - Different background colour from everything else (accent tint — not alarming, but unmissable)
  - Small "EXAMINER'S NOTE" label with an eye or bookmark icon
  - PYQ year references rendered as inline pill tags (e.g. [2023] [2024])
    Parse examiners_note_pyq_refs and replace year mentions in note text with pill tags
  - Instruction word frequency: small visual at bottom showing "DU says: find (×2), prove (×1)"
    Rendered as frequency bars or just labelled counts — compact
  - The student should feel they are reading insider information. The design reflects that.

─────────────────────────
CommonMistakesBlock.tsx
─────────────────────────
Props: common_mistakes: Array<{ description: string, marks_impact: string }>, topicId: string

Behaviour:
  - Subtly red-tinted background (not alarming — a whisper of red)
  - Label: "COMMON MISTAKES"
  - Each mistake numbered
  - marks_impact as a small badge beside each: e.g. "-1 mark", "-2 marks", "fails question"
  - Return null if array is empty

─────────────────────────
AnswerWritingTechniqueBlock.tsx
─────────────────────────
Props: answer_writing_technique: AnswerWritingTechnique | null, topicId: string

AnswerWritingTechnique: { applicable, min_marks_threshold, structure,
                          marks_distribution, word_count_target }

Behaviour:
  - Renders ONLY when applicable is true
  - Label: "ANSWER WRITING TECHNIQUE" with marks threshold badge
  - structure: numbered steps
  - marks_distribution: small table or inline labels — "Step 1: 2 marks, Step 2: 2 marks..."
  - word_count_target: "Target: ~[X] words"
  - Return null if applicable is false or answer_writing_technique is null

─────────────────────────
PYQBlock.tsx
─────────────────────────
Props: pyqs: PYQ[], topicId: string

PYQ object: { year, year_confirmed, year_confidence, source, marks,
              question_text, key_steps, instruction_word, recency_weight }

Behaviour:
  - Visually distinct from generated content — different font weight for question_text
    (this is source material, not AI output — visual distinction is trust-critical)
  - Year tag: prominent pill — "2023 DU Exam ✓" if year_confirmed, "~2023 DU Exam" if not
    ✓ = confirmed from document text. ~ = student-tagged, unconfirmed. Always visible.
  - marks badge beside year tag
  - source attribution: small muted text — exam.du.ac.in or "Student submitted"
  - instruction_word: shown as a label — "Instruction: find"
  - key_steps: clean numbered list with arrow prefix (→)
  - recency_weight: if 1.5 → small "MOST RECENT" tag on that PYQ
  - Multiple PYQs stack vertically with clear dividers
  - Return null if pyqs array is empty

─────────────────────────
QuickChecksBlock.tsx
─────────────────────────
Props: quick_checks: string[3], topicId: string

Behaviour:
  - Exactly 3 questions. Always.
  - Input field below each question (uncontrolled — just for student to type into)
  - NO answer anywhere in the interface — not hidden, not behind a reveal button
  - "Check against your notes" prompt below each input — not a button, not interactive
  - Label: "QUICK CHECK"
  - Forced active recall is the mechanism. The UI enforces it.
  - Return null if quick_checks is empty or undefined

─────────────────────────
ConnectsToBlock.tsx
─────────────────────────
Props: connects_to_topic_id: string | null, connects_to_reason: string | null,
       topicName?: string  ← resolved topic name (queried by parent or passed down)

Behaviour:
  - Small component. Bottom of every topic.
  - Arrow icon (→) + topic name + reason in one line
  - Entire block is tappable — navigates to that topic's unit page
  - Build URL as: /paper/[upc]/unit/[connects_to_unit_id]#topic-[connects_to_topic_id]
  - Return null if connects_to_topic_id is null

─────────────────────────
FormulaSheet.tsx
─────────────────────────
Props: sheet: FormulaSheet | null, unitName: string

FormulaSheet content item: { item, application_condition, marks_value }

Behaviour:
  - Full-width, high contrast — designed for phone screenshot
  - Each item: LaTeX-rendered formula, application condition below in muted text,
    marks_value badge if present
  - "Screenshot" button: html2canvas captures the entire sheet component as PNG
    White background, clean margins, "StudyAI — [unitName] Formula Sheet" header
    PNG downloaded / saved to camera roll
  - Label: "FORMULA AND THEOREM SHEET"
  - Return null if sheet is null

─────────────────────────
DiagramReferenceSheet.tsx
─────────────────────────
Props: sheet: FormulaSheet | null, unitName: string
  (same FormulaSheet type — sheet_type = 'diagram_reference')

Behaviour:
  - Same screenshot functionality as FormulaSheet
  - Each item: diagram name, labeled parts summary, marks value
  - Label: "DIAGRAM REFERENCE SHEET"
  - Return null if sheet is null

─────────────────────────
KeyTermsSheet.tsx
─────────────────────────
Props: sheet: FormulaSheet | null, unitName: string
  (same FormulaSheet type — sheet_type = 'key_terms')

Behaviour:
  - Same screenshot functionality
  - Each item: term in bold, one-line summary below
  - Label: "KEY TERMS AND CONCEPTS"
  - Return null if sheet is null

─────────────────────────
ProblemSet.tsx
─────────────────────────
Props: problemSet: ProblemSet | null, unitName: string

Question object: { number, source_type, source_year, source_book, source_exercise,
                   marks, question_text, answer }
Answer object: { type, full_answer, steps, word_count, common_error_callout }

Behaviour:
  - Questions numbered Q1 through Q[n]
  - Source badge per question: "2023 DU Exam" or "Textbook: [source_book], Ex.[exercise]"
  - marks badge
  - Answer hidden by default — "Show Answer" toggle per question
  - On reveal: full_answer with KaTeX, steps as numbered list, common_error_callout in callout
  - word_count shown for theory answers: "~[X] words to DU standard"
  - Label: "PROBLEM SET — [n] QUESTIONS"
  - Return null if problemSet is null

Completion check:
  [ ] Each component renders without crash when fed mock data matching types/database.ts
  [ ] Each component returns null cleanly when fed null/undefined
  [ ] KaTeX renders correctly in at least DefinitionBlock and ExampleBlock
  [ ] RapidRevisionCard collapses/expands correctly

========================================
STAGE 8.4 — UI COMPONENTS
========================================

Purpose:
  6 utility components used across pages and note components.
  These are not content components — they are trust layer, navigation, and system state.

─────────────────────────
TierBadge.tsx
─────────────────────────
Props: tier: 1 | 2 | 3 | 4, pyqYearsAvailable?: number

Tier descriptions (from plan):
  Tier 1: "Fully calibrated — based on [X] NEP question papers. All content exam-verified."
  Tier 2: "Partially calibrated — based on [X] NEP question paper(s). Some content estimated."
  Tier 3: "Syllabus-based — no NEP question papers publicly available."
  Tier 4: "Insufficient data — notes cannot be generated yet."

Behaviour:
  - Shown prominently on paper overview page
  - Colour-coded: Tier 1 green, Tier 2 amber, Tier 3 orange, Tier 4 red
  - Full description as tooltip or expandable text on tap
  - Short label always visible: "Tier 1 — Fully Calibrated"

─────────────────────────
FieldFlagButton.tsx
─────────────────────────
Props: fieldName: string, topicId: string, sessionId: string

Behaviour:
  - Flag icon on every note field
  - Desktop: visible on hover. Mobile: always visible (small, unobtrusive)
  - On tap: bottom sheet (mobile) or popover (desktop) with 3 options:
      "This information seems incorrect"
      "This is missing important content"
      "Mathematical error"
  - After selection: calls flagField() from lib/queries.ts
  - Checks incrementFlagCount() before submitting — if rate limit hit: show message
    "You've reached the flag limit for this paper in this session"
  - After successful submit: button shows "Under review" state
  - Rate limit: 10 flags per session per paper (enforced in lib/sessions.ts)
  - Systematic flagging guard: if 5+ flags from same session on same topic within 60s,
    auto-mark as low confidence (handled server-side but noted in submission)

─────────────────────────
Last4HoursToggle.tsx
─────────────────────────
Props: isActive: boolean, onToggle: () => void

Behaviour:
  - Single tap at paper level (shown in paper page header)
  - When active: collapses everything EXCEPT RapidRevisionCards, PYQBlocks,
    and the relevant sheet (formula/diagram/key terms)
  - Sheet pins to top of unit when toggle is active
  - Label: "Last 4 Hours" with a clock icon
  - Active state: distinct filled style, different colour
  - This is a rendering FILTER — same content, different view
  - Passes isLast4Hours: boolean prop down to all topic components
    (each component conditionally renders based on this flag)

─────────────────────────
PYQSubmissionBanner.tsx
─────────────────────────
Props: upc: string, paperName: string, tier: 3 | 4

Behaviour:
  - Shown on paper page when no NEP PYQs exist (tier 3 or 4)
  - Honest statement: "No NEP question papers are publicly available for this paper."
  - Single CTA: "I have this question paper"
  - On tap: opens camera directly (using HTML file input with capture="camera" attribute)
    or navigates to submission flow page
  - Design: informational, not alarming. Warm, inviting. Not a warning banner.

─────────────────────────
VerifiedBadge.tsx
─────────────────────────
Props: verified: boolean, verificationMode: string, verificationPassed: boolean

Modes: 'numerical_single' | 'numerical_dual' | 'proof' | 'none'

Behaviour:
  - Small badge, top-right of ExampleBlock
  - Single check ✓: numerical_single or proof verified
  - Double check ✓✓: numerical_dual (both Mixtral and Llama 3 agreed)
  - Tooltip on hover: explains what was verified and how
    e.g. "Verified by Groq Mixtral — answer checked independently"
    e.g. "Dual-verified — two independent models agree"
  - If verificationPassed is false: show different icon (not a checkmark)
    This case should be rare — but handle it gracefully

─────────────────────────
PartialDeliveryNotice.tsx
─────────────────────────
Props: unitName: string, status: 'failed' | 'generating', retryAvailable: boolean

Behaviour:
  - Renders in place of a unit that failed to generate
  - Status 'failed': "This unit could not be generated. Flagged for manual review."
  - Status 'generating': "This unit is still generating. Check back shortly." with spinner
  - If retryAvailable: "Retry" button (calls API endpoint to re-trigger this unit's pipeline)
  - All other completed units remain accessible — this notice is isolated to the failed unit
  - Design: neutral, not alarming. Clear. No dead ends.

Completion check:
  [ ] TierBadge renders all 4 tiers with correct colours
  [ ] FieldFlagButton bottom sheet opens and closes correctly
  [ ] Last4HoursToggle visual state changes correctly on toggle
  [ ] VerifiedBadge tooltip shows on hover

========================================
STAGE 8.5 — PIPELINE COMPONENTS
========================================

Purpose:
  The first thing a student sees after submitting a UPC.
  Live view of all 12 agents running.
  Builds trust before the student reads a word.

Files to create:
  components/pipeline/PipelineProgressView.tsx
  components/pipeline/AgentStatusCard.tsx
  components/pipeline/UnitProgressBar.tsx

─────────────────────────
AgentStatusCard.tsx
─────────────────────────
Props: agentNumber: number, agentName: string, status: 'queued' | 'running' | 'complete' | 'failed'
       model?: string   ← e.g. "Gemini 2.5 Pro"

Behaviour:
  - Small card per agent
  - Status icons:
      queued  → grey dot
      running → animated pulse (Tailwind animate-pulse or Framer Motion)
      complete → green checkmark
      failed  → red X
  - Agent name displayed: e.g. "Agent 2 — Researcher"
  - Model shown in muted small text below name
  - 12 of these in total — stacked or in a grid

─────────────────────────
UnitProgressBar.tsx
─────────────────────────
Props: totalUnits: number, completedUnits: number
       units: Array<{ unit_number, unit_name, status }>

Behaviour:
  - Progress bar showing completed/total units
  - Each unit shown as a segment that fills/lights up when status → complete
  - Orientation cue only — not gamification
  - When a unit completes: transition to completed state (smooth colour fill)

─────────────────────────
PipelineProgressView.tsx
─────────────────────────
Props: upc: string

Behaviour:
  - Subscribes to Realtime on units table WHERE upc = prop.upc (via subscribeToUnitStatus)
  - Shows all 12 AgentStatusCards in sequence
  - Shows UnitProgressBar below agent cards
  - As each unit flips to 'complete': a UnitCard appears below
    UnitCard: unit name, "Ready to read →" link to /paper/[upc]/unit/[unitId]
  - Student starts reading Unit 1 while Units 3 and 4 are still generating
  - This component IS the pipeline page — used directly in app/pipeline/[upc]/page.tsx
  - Agent status is polled or driven by a separate pipeline_runs table
    (for v1: poll the units table status changes and infer agent state from that)
  - Framer Motion: units reveal with slide-up animation as they complete
  - Auto-navigate to paper overview when all units complete (optional, with countdown)

Completion check:
  [ ] PipelineProgressView renders without crash with mock upc
  [ ] AgentStatusCard shows correct icon for each status
  [ ] UnitProgressBar fills correctly given mock completed/total values
  [ ] Realtime subscription wires up (test: manually flip a unit status in Supabase dashboard
      and confirm the UI updates without page refresh)

========================================
STAGE 8.6 — PAGES & ROUTING
========================================

Purpose:
  4 pages. Full Realtime wiring. The complete student experience end to end.

Files to create:
  app/layout.tsx
  app/globals.css
  app/page.tsx                              ← UPC entry landing page
  app/paper/[upc]/page.tsx                  ← paper overview + tier badge
  app/paper/[upc]/unit/[unitId]/page.tsx    ← full unit view with all topics
  app/pipeline/[upc]/page.tsx               ← live pipeline progress view

─────────────────────────
app/layout.tsx
─────────────────────────
Root layout. Wraps all pages.
Providers to wrap in:
  - ReactQueryProvider (TanStack Query client)
  - Any global context (session, last4Hours toggle state)
Head: KaTeX CSS link. Favicon. Meta title "StudyAI".

─────────────────────────
app/globals.css
─────────────────────────
  @import 'katex/dist/katex.min.css';
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  CSS variables for the full colour system.
  Base body styles: background, text, font.
  Thin scrollbar styles.
  KaTeX override styles if needed (font size, colour in dark mode).

─────────────────────────
app/page.tsx — UPC Entry
─────────────────────────
The landing page. One input. One purpose.

Behaviour:
  - Input field: "Enter your paper code (UPC)"
  - Example shown below input: e.g. "e.g. MATH1001"
  - On submit: call FastAPI POST /generate with { upc }
    If pipeline already exists for that UPC: redirect to /paper/[upc]
    If new: redirect to /pipeline/[upc] to watch it generate
  - One-liner tagline: "Study notes built from your DU question paper."
  - No other content. No navigation. No noise.
  - If UPC not found and pipeline fails to start: clear error message
  - Design: full height, centered, minimal — exam-morning fast access

─────────────────────────
app/pipeline/[upc]/page.tsx — Live Pipeline
─────────────────────────
Behaviour:
  - Renders <PipelineProgressView upc={params.upc} />
  - Paper name shown at top (fetched via getPaper)
  - Auto-redirects to /paper/[upc] when all units complete

─────────────────────────
app/paper/[upc]/page.tsx — Paper Overview
─────────────────────────
Behaviour:
  - Fetches paper data via getPaper(upc)
  - Shows: paper_name, department, programme, semester, paper_type
  - Shows TierBadge prominently
  - Shows PYQSubmissionBanner if tier 3 or 4
  - Shows "Syllabus sourced from [syllabus_url] — last verified [date]" — clickable link
  - Shows pyq_years_available as a list of year tags
  - Lists all units with status + link to unit page
  - Last4HoursToggle in header — state stored at this level, passed to unit pages
  - Units with status 'failed': show PartialDeliveryNotice inline
  - Units still 'generating': show generating state
  - Subscribes to Realtime via subscribeToUnitStatus — list updates live

─────────────────────────
app/paper/[upc]/unit/[unitId]/page.tsx — Unit View
─────────────────────────
Behaviour:
  - Fetches unit, all topics, formula/diagram/key-terms sheet, problem set
  - Renders unit header: unit_name, estimated_study_hours, marks_weightage
  - Renders conceptual_summary at top: what_this_unit_is_about, how_topics_connect, unifying_idea
  - For each topic (ordered by topic_number):
      Renders RapidRevisionCard (always visible, collapses topic)
      On expand: renders full topic stack in order:
        DefinitionBlock
        CoreConceptBlock
        ExampleBlock
        DiagramBlock (if diagram_block present)
        ExaminersNoteBlock
        CommonMistakesBlock
        AnswerWritingTechniqueBlock (if applicable)
        PYQBlock
        QuickChecksBlock
        ConnectsToBlock
  - After all topics: renders the appropriate sheet component based on paper_type:
      'numerical' / 'mixed' / 'theory' → FormulaSheet
      'life_sciences' → DiagramReferenceSheet
      If paper_type is 'theory' (non-math) → KeyTermsSheet
  - Renders unit_closer.exam_ready_checklist as interactive checkboxes (state in localStorage)
  - Renders ProblemSet at the bottom
  - UnitProgressBar pinned at top of page: topics completed tracking via localStorage
  - Last4HoursToggle state passed down — collapses to rapid revision mode when active
  - Subscribes to Realtime via subscribeToTopicStatus — topics appear as pipeline completes

Completion check:
  [X] UPC entry → pipeline page → paper overview → unit view: full navigation works
  [X] Realtime: flip a unit status in Supabase → paper overview updates without refresh
  [X] Last4HoursToggle: activate on paper overview, verify unit page collapses correctly
  [X] KaTeX renders in unit page for a mathematical topic
  [X] TierBadge shows correct tier on paper overview
  [X] Formula sheet screenshot button generates and downloads a PNG

========================================
FULL PHASE 8 COMPLETION CHECKLIST
========================================

Stage 8.1 complete:
  [X] npm run dev starts without errors
  [X] Tailwind working
  [X] .env.local present with correct keys (publishable only)
  [X] All empty folders created

Stage 8.2 complete:
  [X] Supabase client connects
  [X] getPaper() returns data from Supabase
  [X] subscribeToUnitStatus() fires callback on status change
  [X] renderMath() correctly processes LaTeX strings
  [X] getOrCreateSessionId() stable across page reloads

Stage 8.3 complete:
  [X] All 15 note components render with mock data
  [X] All return null cleanly on missing data
  [X] KaTeX renders in Definition and Example blocks
  [X] html2canvas PNG export works on FormulaSheet

Stage 8.4 complete:
  [X] TierBadge all 4 tiers render
  [X] FieldFlagButton submits flag to Supabase and shows rate limit message
  [X] Last4HoursToggle visual state correct
  [X] VerifiedBadge tooltip works

Stage 8.5 complete:
  [X] PipelineProgressView connects to Realtime
  [X] Unit cards appear as status flips to complete (tested via Supabase dashboard)
  [X] Agent status cards animated pulse while running

Stage 8.6 complete:
  [X] All 4 pages render without crash
  [X] Full navigation flow: entry → pipeline → overview → unit
  [X] Realtime unit status updates live on overview page
  [X] Last4HoursToggle filters correctly
  [X] Formula sheet PNG export downloads

========================================
CRITICAL RULES — DO NOT VIOLATE
========================================

1. Secret key NEVER in frontend. Only publishable key in NEXT_PUBLIC_.
2. Every component returns null (not empty fragment) on missing data.
3. All text content passes through renderMath() before rendering.
4. Supabase Realtime subscriptions always unsubscribed on component unmount.
5. No component imports directly from @supabase/supabase-js — always via lib/supabase.ts.
6. Quick checks have NO answers anywhere in the UI. No reveal button. No hidden field.
   This is non-negotiable. Forced active recall is the product mechanism.
7. Year tags: ✓ for confirmed, ~ for unconfirmed. Always visible. Never hidden.
8. Student-submitted PYQs always tagged "Student submitted — ~[Year]". Non-negotiable.

========================================
END OF PHASE 8 BUILD REFERENCE
========================================