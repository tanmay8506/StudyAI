


StudyAI
Technical Reference
─────────────────────────────
Complete SQL Schema  ·  JSON Schemas  ·  Prompt Templates
Quality Benchmark  ·  Failure Handling  ·  Notes Structure
Document 3 of 3  ·  Fills every gap in Documents 1 and 2




About This Document
This is the third and final document in the StudyAI build set. Documents 1 (Original Plan) and 2 (Build Guide) tell you what to build and in what order. This document gives you the exact technical artefacts you need to build it — the database schema, every JSON schema, starter templates for every prompt file, the complete quality benchmark, and the full failure handling specification.

Use this document as a reference. You do not read it start to finish — you open it when you need a specific thing. The table of contents below maps to exactly what you will need at each phase.

When You Are In
Use This Section
Phase 1
Section 1 — SQL Schema. Apply 001_initial_schema.sql to Supabase.
Phase 2A
Section 2 — JSON Schemas (PYQ Normaliser, Paper DNA). Section 4 — Researcher and Mapper prompts.
Phase 2B
Section 2 — topic_output_schema.json. Section 4 — Writer prompt template. Section 3 — Notes structure.
Phase 2C
Section 2 — critic_diff_schema.json. Section 4 — Critic and Final Examiner prompts. Section 5 — Failure handling.
Phase 3
Section 3 — Notes structure (to understand what each component renders).
Phase 4
Section 6 — Quality benchmark. All 35 benchmark criteria.
Phase 5
Section 3 — Complete frontend component behaviour specification.


Section 1
Complete SQL Schema — 001_initial_schema.sql

Copy this entire block into the Supabase SQL editor and run it once. This creates all 10 tables with all fields exactly as the pipeline expects. Do not alter any column name — the agents write to specific field names.

Before Running
Run this first in Supabase SQL editor: CREATE EXTENSION IF NOT EXISTS vector;
Then run the schema below. Order matters — tables with foreign keys must come after their parents.
After running, confirm all 10 tables appear in the Supabase Table Editor.

papers
v1 change: credit_structure and note_style_category removed (unused). paper_dna added here (DNA is paper-level, not unit-level). All timestamps default to NOW(). Foreign keys use ON DELETE CASCADE throughout.

CREATE TABLE papers (
  upc                       TEXT PRIMARY KEY,
  department                TEXT NOT NULL,
  programme                 TEXT NOT NULL,
  semester                  INTEGER NOT NULL,
  paper_name                TEXT NOT NULL,
  paper_type                TEXT NOT NULL,       -- theory/numerical/mixed/life_sciences
  diagram_heavy             BOOLEAN DEFAULT FALSE,
  practical_component       BOOLEAN DEFAULT FALSE,
  syllabus_url              TEXT,
  syllabus_last_verified    TIMESTAMP WITH TIME ZONE,
  syllabus_hash             TEXT,
  syllabus_confidence       TEXT DEFAULT 'high', -- high/medium/low
  pyq_years_available       INTEGER[],
  documentation_tier        INTEGER DEFAULT 2,   -- 1/2/3/4
  primary_textbook          TEXT,
  all_prescribed_textbooks  JSONB,
  paper_dna                 JSONB,               -- all 4 DNA analyses (structural, topic, language, combination)
  pipeline_status           TEXT DEFAULT 'queued', -- queued/generating/complete/failed/partial
  generated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_updated              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  english_content_ready     BOOLEAN DEFAULT FALSE,
  hindi_content_ready       BOOLEAN DEFAULT FALSE
);

units
v1 change: paper_dna moved to papers table. conceptual_summary changed from TEXT to JSONB (structured). unit_closer only contains exam_ready_checklist.

CREATE TABLE units (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upc                       TEXT NOT NULL REFERENCES papers(upc) ON DELETE CASCADE,
  unit_number               INTEGER NOT NULL,
  unit_name                 TEXT NOT NULL,
  estimated_study_hours     FLOAT,
  marks_weightage           INTEGER,
  status                    TEXT DEFAULT 'queued', -- queued/generating/verifying/complete/failed
  conceptual_summary        JSONB,               -- { what_this_unit_is_about, how_topics_connect, unifying_idea }
  unit_closer               JSONB,               -- { exam_ready_checklist: string[] }
  generated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_updated              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_units_upc ON units(upc);
CREATE INDEX idx_units_status ON units(status);

topics
CREATE TABLE topics (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  upc                       TEXT NOT NULL REFERENCES papers(upc) ON DELETE CASCADE,
  topic_name                TEXT NOT NULL,
  topic_number              INTEGER NOT NULL,
  difficulty                TEXT,               -- easy/medium/hard
  estimated_study_minutes   INTEGER,
  priority                  TEXT,               -- high/medium/low/never_asked
  -- marks_weightage removed: use priority (from Topic DNA). Marks vary by year.
  prerequisite_topic_id     UUID REFERENCES topics(id),
  prerequisite_bridge       TEXT,
  status                    TEXT DEFAULT 'queued',
  connects_to_topic_id      UUID REFERENCES topics(id),
  connects_to_reason        TEXT,
  split_generation          BOOLEAN DEFAULT FALSE,
  depth_signal_source       TEXT,               -- pyq/cbcs_estimate/syllabus_hours

  -- Rapid Revision
  rapid_revision            JSONB,
  -- Structure: { definition_one_line, key_formula_or_concept, examiner_pattern }

  -- Core Content
  definition                TEXT,
  core_concept              TEXT,
  analogy                   TEXT,
  analogy_verified          BOOLEAN DEFAULT FALSE,

  -- Examples (array of example objects)
  examples                  JSONB,
  -- Structure: [{ type, content, steps:[{step_number, step_text, units_shown}],
  --   answer, answer_boxed, common_error, verified, verification_mode, verification_passed }]

  -- Diagram
  diagram_block             JSONB,
  -- Structure: { diagram_name, svg_source, svg_file_path, svg_code,
  --   labeled_parts:[{part_number, part_name, explanation, du_expected_label}],
  --   marks_value, draw_instructions, source_book, source_edition, source_page }

  -- Examiner Intelligence
  examiners_note            TEXT,
  examiners_note_pyq_refs   TEXT[],
  instruction_word_frequency JSONB,

  -- Mistakes
  common_mistakes           JSONB,
  -- Structure: [{ description, marks_impact }]

  -- Answer Writing
  answer_writing_technique  JSONB,
  -- Structure: { applicable, min_marks_threshold, structure:[],
  --   marks_distribution:{}, word_count_target }

  -- PYQs
  pyqs                      JSONB,
  -- Structure: [{ year, year_confirmed, year_confidence, source,
  --   marks, question_text, key_steps:[], instruction_word, recency_weight }]

  -- Self-check
  quick_checks              TEXT[],             -- exactly 3 items

  -- Flags and metadata
  flagged_fields            JSONB,
  patched                   BOOLEAN DEFAULT FALSE,
  generated_at              TIMESTAMP WITH TIME ZONE,
  last_updated              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_topics_unit_id ON topics(unit_id);
CREATE INDEX idx_topics_upc ON topics(upc);

problem_sets
CREATE TABLE problem_sets (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  questions                 JSONB NOT NULL
  -- Structure: [{ number, source_type, source_year, source_book, source_exercise,
  --   marks, question_text,
  --   answer: { type, full_answer, steps:[], word_count, common_error_callout } }]
);

formula_sheets
CREATE TABLE formula_sheets (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  sheet_type                TEXT NOT NULL,      -- formula/diagram_reference/key_terms
  content                   JSONB NOT NULL
  -- Structure: [{ item, application_condition, marks_value }]
);

pyq_submissions
CREATE TABLE pyq_submissions (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upc                       TEXT NOT NULL,
  year_tagged_by_student    INTEGER NOT NULL,
  year_extracted_from_doc   INTEGER,
  year_confidence           TEXT,               -- confirmed/unconfirmed
  file_url                  TEXT,
  file_deleted              BOOLEAN DEFAULT FALSE,
  extracted_json            JSONB,
  verification_status       TEXT DEFAULT 'pending', -- pending/verified/failed/manual_review
  quality_scores            JSONB,
  -- Structure: { scan_readability, completeness, upc_match, failure_reason }
  reward_issued             BOOLEAN DEFAULT FALSE,
  reward_type               TEXT,               -- early_access/cross_paper_credit
  reward_paper_upc          TEXT,
  submitted_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

syllabus_change_log
CREATE TABLE syllabus_change_log (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upc                       TEXT NOT NULL REFERENCES papers(upc),
  detected_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  old_hash                  TEXT,
  new_hash                  TEXT,
  diff_summary              JSONB,
  -- Structure: { topics_added:[], topics_removed:[], units_changed:[], hours_changed:{} }
  regeneration_status       TEXT DEFAULT 'pending',
  students_notified         BOOLEAN DEFAULT FALSE
);

field_flags
CREATE TABLE field_flags (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id                  UUID NOT NULL REFERENCES topics(id),
  field_name                TEXT NOT NULL,
  flag_type                 TEXT NOT NULL,      -- seems_wrong/outdated/missing_something
  student_note              TEXT,
  session_id                TEXT,
  flags_in_session          INTEGER DEFAULT 1,
  groq_verdict              TEXT,               -- confirmed/unconfirmed/manual
  status                    TEXT DEFAULT 'open', -- open/under_review/resolved
  resolved_at               TIMESTAMP WITH TIME ZONE
);

sessions
CREATE TABLE sessions (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_token             TEXT UNIQUE NOT NULL,
  created_at                TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_active               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  papers_viewed             TEXT[]
);

session_paper_views
CREATE TABLE session_paper_views (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id                UUID NOT NULL REFERENCES sessions(id),
  upc                       TEXT NOT NULL,
  first_viewed              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_viewed               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  units_completed           INTEGER[],
  pyqs_attempted            INTEGER DEFAULT 0
);

CREATE INDEX idx_session_paper_views_session ON session_paper_views(session_id);
CREATE INDEX idx_session_paper_views_upc ON session_paper_views(upc);

Enable Realtime
After creating all tables, enable Realtime on the units table so the frontend can subscribe to status changes:

-- Run this in Supabase SQL editor after schema creation
ALTER PUBLICATION supabase_realtime ADD TABLE units;
ALTER PUBLICATION supabase_realtime ADD TABLE topics;


Section 2
JSON Schemas — All Five Schema Files

These are the exact schemas that the pipeline agents must conform to. Every agent that produces structured output is given its schema in the system prompt and told to produce nothing else. Save each schema as the exact filename shown.

topic_output_schema.json
Used by: Agent 5 (Writer). This is the most critical schema. Every topic the Writer produces must match this exactly. The orchestrator validates against this schema before writing to the database.

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["topic_name", "priority", "difficulty", "rapid_revision",
               "definition", "core_concept", "examiners_note", "common_mistakes",
               "pyqs", "quick_checks"],
  "properties": {
    "topic_name": { "type": "string" },
    "priority": { "type": "string", "enum": ["high", "medium", "low", "never_asked"] },
    "difficulty": { "type": "string", "enum": ["easy", "medium", "hard"] },
    "estimated_study_minutes": { "type": "integer" },
    "depth_signal_source": { "type": "string" },

    "rapid_revision": {
      "type": "object",
      "required": ["definition_one_line", "key_formula_or_concept", "examiner_pattern"],
      "properties": {
        "definition_one_line": { "type": "string" },
        "key_formula_or_concept": { "type": "string" },
        "examiner_pattern": { "type": "string" }
      }
    },

    "definition": { "type": "string" },
    "core_concept": { "type": "string" },
    "analogy": { "type": "string" },
    "analogy_verified": { "type": "boolean" },

    "examples": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "content", "steps", "answer"],
        "properties": {
          "type": { "type": "string", "enum": ["numerical", "theory", "biological"] },
          "content": { "type": "string" },
          "steps": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["step_number", "step_text"],
              "properties": {
                "step_number": { "type": "integer" },
                "step_text": { "type": "string" },
                "units_shown": { "type": "boolean" }
              }
            }
          },
          "answer": { "type": "string" },
          "answer_boxed": { "type": "boolean" },
          "common_error": { "type": "string" },
          "verified": { "type": "boolean", "default": false },
          "verification_mode": {
            "type": "string",
            "enum": ["numerical_single", "numerical_dual", "proof", "none"]
          },
          "verification_passed": { "type": "boolean" }
        }
      }
    },

    "diagram_block": {
      "type": ["object", "null"],
      "properties": {
        "diagram_name": { "type": "string" },
        "svg_source": { "type": "string", "enum": ["library", "generated"] },
        "svg_file_path": { "type": ["string", "null"] },
        "svg_code": { "type": ["string", "null"] },
        "labeled_parts": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "part_number": { "type": "integer" },
              "part_name": { "type": "string" },
              "explanation": { "type": "string" },
              "du_expected_label": { "type": "string" }
            }
          }
        },
        "marks_value": { "type": "integer" },
        "draw_instructions": { "type": "string" },
        "source_book": { "type": "string" },
        "source_edition": { "type": "string" },
        "source_page": { "type": "integer" }
      }
    },

    "examiners_note": { "type": "string" },
    "examiners_note_pyq_refs": { "type": "array", "items": { "type": "string" } },
    "instruction_word_frequency": { "type": "object" },

    "common_mistakes": {
      "type": "array",
      "minItems": 1,
      "maxItems": 3,
      "items": {
        "type": "object",
        "required": ["description", "marks_impact"],
        "properties": {
          "description": { "type": "string" },
          "marks_impact": { "type": "string" }
        }
      }
    },

    "answer_writing_technique": {
      "type": ["object", "null"],
      "properties": {
        "applicable": { "type": "boolean" },
        "min_marks_threshold": { "type": "integer" },
        "structure": { "type": "array", "items": { "type": "string" } },
        "marks_distribution": { "type": "object" },
        "word_count_target": { "type": "integer" }
      }
    },

    "pyqs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["year", "marks", "question_text", "instruction_word"],
        "properties": {
          "year": { "type": "integer" },
          "year_confirmed": { "type": "boolean" },
          "year_confidence": { "type": "string", "enum": ["confirmed", "unconfirmed"] },
          "source": { "type": "string" },
          "marks": { "type": "integer" },
          "question_text": { "type": "string" },
          "key_steps": { "type": "array", "items": { "type": "string" } },
          "instruction_word": { "type": "string" },
          "recency_weight": { "type": "number" }
        }
      }
    },

    "quick_checks": {
      "type": "array",
      "minItems": 3,
      "maxItems": 3,
      "items": { "type": "string" }
    },

    "connects_to_reason": { "type": "string" }
  }
}

critic_diff_schema.json
Used by: Agent 8 (Critic). The Critic produces only this format. No prose. Every correction must have field, issue, and correction. Severity determines whether the Rewriter handles it or it is logged only.

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["topic_id", "corrections"],
  "properties": {
    "topic_id": { "type": "string" },
    "corrections": {
      "type": "array",
      "maxItems": 10,
      "items": {
        "type": "object",
        "required": ["field", "issue", "correction", "severity"],
        "properties": {
          "field": {
            "type": "string",
            "description": "Exact field path e.g. definition, examples[0].steps[2].units_shown"
          },
          "issue": {
            "type": "string",
            "description": "Specific description of what is wrong"
          },
          "correction": {
            "type": "string",
            "description": "Specific instruction for what to change"
          },
          "severity": {
            "type": "string",
            "enum": ["critical", "major", "minor"],
            "description": "critical=marks lost, major=incomplete, minor=polish"
          }
        }
      }
    }
  }
}

paper_dna_schema.json
Used by: Agent 3 (Paper DNA Generator). The full DNA output contains all four analyses. Written to units.paper_dna JSONB column.

{
  "structural_dna": {
    "total_marks": 75,
    "time_minutes": 180,
    "mcq_component": false,
    "sections": [
      {
        "name": "Section A",
        "type": "short_answer",
        "marks_per_question": 3,
        "total_questions": 5,
        "attempt_all": true,
        "attempt": null
      },
      {
        "name": "Section B",
        "type": "long_answer",
        "marks_per_question": 6,
        "total_questions": 8,
        "attempt_all": false,
        "attempt": 5
      }
    ]
  },

  "topic_dna": [
    {
      "topic_name": "Eigenvalues and Eigenvectors",
      "appearances": [
        { "year": 2023, "marks": 6, "question_type": "calculate", "unit": 3 },
        { "year": 2024, "marks": 6, "question_type": "find", "unit": 3 }
      ],
      "total_appearances": 2,
      "marks_trend": "stable",
      "priority": "high",
      "never_asked": false,
      "recency_weight": 1.5
    }
  ],

  "language_dna": [
    {
      "topic_name": "Eigenvalues and Eigenvectors",
      "instruction_words": { "find": 2, "calculate": 1, "derive": 0, "prove": 0 },
      "examiner_vocabulary": [
        "characteristic equation",
        "characteristic polynomial",
        "find the eigenvalues and corresponding eigenvectors of the matrix"
      ],
      "typical_phrasing": "Find the eigenvalues and corresponding eigenvectors of matrix A = [...]"
    }
  ],

  "combination_dna": [
    {
      "topic_name": "Eigenvalues and Eigenvectors",
      "always_asked_with": ["Diagonalisation"],
      "combination_pattern": "Find eigenvalues of A, hence diagonalise A",
      "standalone_frequency": 0.2,
      "diagram_required": false,
      "numerical_always": true
    }
  ]
}

pyq_normalised_schema.json
Used by: Agent 2C (PYQ Normaliser). Every PYQ paper is normalised to this format before Paper DNA runs. This is the format all downstream agents use — never raw PYQ papers.

{
  "year": 2024,
  "year_confirmed": true,
  "source_url": "https://exam.du.ac.in/...",
  "questions": [
    {
      "number": 1,
      "total_marks": 6,
      "compulsory": true,
      "parts": [
        {
          "part": "a",
          "marks": 2,
          "instruction_word": "define",
          "topic_hint": "Cauchy sequence",
          "question_text": "Define a Cauchy sequence."
        },
        {
          "part": "b",
          "marks": 4,
          "instruction_word": "prove",
          "topic_hint": "Cauchy sequence boundedness",
          "question_text": "Prove that every Cauchy sequence is bounded."
        }
      ]
    }
  ]
}

syllabus_extraction_schema.json
Used by: Agent 2 (Researcher). The Gemini syllabus extraction call must output this format. Agent 2B verifies this output against the raw PDF.

{
  "paper_name": "Real Analysis",
  "upc": "BSCMT201",
  "total_credits": 4,
  "units": [
    {
      "unit_number": 1,
      "unit_name": "Sequences of Real Numbers",
      "hours": 15,
      "topics": [
        "Sequences and their limits",
        "Convergent and divergent sequences",
        "Monotone sequences",
        "Cauchy sequences",
        "Subsequences and limit superior and inferior"
      ]
    }
  ],
  "prescribed_books": [
    {
      "title": "Introduction to Real Analysis",
      "authors": "Bartle and Sherbert",
      "edition": "4th",
      "publisher": "Wiley"
    }
  ],
  "suggested_books": [],
  "practical_component": false,
  "extraction_confidence": "high",
  "ambiguous_content": []
}

unit_schema.json
Used by: Orchestrator (validates assembled unit output after all topic calls). Also used by Agent 11 (Patcher) when regenerating unit-level summary fields. Defines the exact shape of the conceptual_summary, unit_closer, formula_sheet, and paper_dna_summary JSONB columns written to the units table.

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["unit_number", "unit_name", "conceptual_summary", "unit_closer"],
  "properties": {
    "unit_number":            { "type": "integer" },
    "unit_name":              { "type": "string" },
    "estimated_study_hours": { "type": "number" },
    "marks_weightage":        { "type": "integer" },

    "conceptual_summary": {
      "type": "object",
      "required": ["what_this_unit_is_about", "how_topics_connect", "unifying_idea"],
      "properties": {
        "what_this_unit_is_about": { "type": "string" },
        "how_topics_connect":      { "type": "string" },
        "unifying_idea":           { "type": "string" }
      }
    },

    "unit_closer": {
      "type": "object",
      "properties": {
        "exam_ready_checklist": {
          "type": "array",
          "minItems": 2, "maxItems": 4,
          "items": { "type": "string" }
        }
      }
    },

    "formula_sheet": {
      "type": ["object", "null"],
      "properties": {
        "sheet_type": {
          "type": "string",
          "enum": ["formula", "diagram_reference", "key_terms"]
        },
        "content": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["item"],
            "properties": {
              "item":                  { "type": "string" },
              "application_condition": { "type": "string" },
              "marks_value":           { "type": ["integer", "null"] }
            }
          }
        }
      }
    },

    "paper_dna_summary": {
      "type": "object",
      "properties": {
        "questions_from_here_marks":     { "type": "integer" },
        "most_frequent_question_type":   { "type": "string" },
        "topics_always_appear":          { "type": "array", "items": { "type": "string" } },
        "topics_never_asked":            { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}


Section 3
Notes Structure — Exact Layout at Topic and Unit Level

This section defines exactly how notes are structured — at both the topic level and the unit level. Every component in Phase 5 renders one part of this structure. Read this before building any frontend component so you understand what each block is supposed to show and why.

Topic-Level Structure
Every topic follows this exact structure. No deviation. Consistency is a feature — the student stops spending energy on orientation and spends it entirely on content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC NAME
Difficulty: Easy / Medium / Hard
Study time: ~X minutes
Priority: High / Medium / Low / Not examined
Documentation confidence: Tier [1/2/3/4]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAPID REVISION
[One-line definition — exactly as DU accepts for 2-mark question]
[Key formula or concept in LaTeX — single most tested element]
[How DU tests this — exact instruction word + typical phrasing from Language DNA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prerequisite: [Topic Name, Unit X] → [Specific concept bridge sentence]
             OR: None

DEFINITION
[Clean. Under 40 words. Every term explained. DU-acceptable.]
[Mathematical expressions in LaTeX.]

CORE CONCEPT
[Plain language. No assumed knowledge beyond prerequisite.]
Think of it this way: [Verified analogy connecting to prerequisite]

── FOR NUMERICAL / DERIVATION PAPERS ──────────

EXAMPLE 1  ✓ verified
[Problem statement]
Step 1: [LaTeX where needed — units shown on intermediate values]
Step 2: [Step]
Step N: [Step]
$$\boxed{Final Answer}$$
Common error: [Specific error that loses marks in DU]

EXAMPLE 2  ✓✓ dual-verified
[One added layer. Edge case or combination with adjacent topic.]

── FOR THEORY PAPERS ──────────────────────────

EXAMPLE 1
[Real instance matching how DU uses this concept in PYQs]

EXAMPLE 2
[Contrasting or extended case]

── FOR DIAGRAM-HEAVY TOPICS (Life Sciences) ───

DIAGRAM — [Diagram Name]
[Rendered SVG from pre-built library]

Labeled parts:
1. [Part name] — [one-line explanation] — DU label: "[exact expected label]"
2. [Part name] — [one-line explanation] — DU label: "[exact expected label]"

Carries approximately [X] marks.
Draw instructions: [Specific step-by-step guide for exam]
Labels sourced from: [Book Name, Edition, Page X]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMINER'S NOTE
[Exact instruction word DU uses for this topic — from Language DNA]
[Specific PYQ pattern referencing real years]
[What full marks includes that passing doesn't]
[Combination pattern if applicable]
[For proof topics: exact hypothesis, expected technique, common logical error]

COMMON MISTAKES
1. [Specific DU exam error] — loses [X] marks
2. [Specific DU exam error] — loses [X] marks

ANSWER WRITING TECHNIQUE
(Present only for 6+ mark topics)
[Exact structure sentence by sentence]
[Which part carries which marks]
[Word count target: ~X words]
[Whether diagram expected]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PYQ 1 — 2024 DU Exam ✓ — 6 marks
[Question exactly as asked. Not paraphrased. Exact.]
Key steps for full marks:
→ [Step 1]
→ [Step 2]

PYQ 2 — ~2023 DU Exam — 6 marks
[Question exactly as asked]
(~ = student-submitted, year unconfirmed from document)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK CHECK
1. [Memory check — no answer given]
2. [Application check — no answer given]
3. [Combined or edge case — no answer given]

Connects to: [Topic Name, Unit X] — [One-line reason]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two rules that are non-negotiable
1. Rapid Revision is written last, placed first. After full topic generation, the Writer produces
   it as a synthesis of complete topic knowledge. It is not a preview — it is a summary.
2. Quick Checks have no answers — intentional and non-negotiable. Forced active recall.
   Forced re-reading. This is the mechanism for retention. No reveal button. Ever.

Unit-Level Structure
The unit wraps all its topics. The unit header gives the student orientation before they read anything. The unit closer ties everything together after they have read everything.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIT [N] — [NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[What this unit is really about — 2 plain lines]

Prerequisites: [Topic, Unit X] OR None
Estimated study time: [X] hours

PAPER DNA — THIS UNIT
Questions from here: [X] marks across all available PYQ years
Most frequent question type: [find/prove/explain/derive]
Topics that always appear: [list]
Topics never asked: [list]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ALL TOPICS — in optimised sequence from Agent 4]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UNIT CLOSER

CONCEPTUAL SUMMARY
[What this unit was really about as a single idea]
[How every topic connects to each other]
[The anchor point from which the student can reconstruct the unit]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FOR MATHS / PHYSICS / CHEMISTRY]
FORMULA AND THEOREM SHEET
[Every formula in LaTeX. Every theorem. One-line application condition each.]
[Designed for phone screenshot.]

[FOR LIFE SCIENCES]
DIAGRAM REFERENCE SHEET
[Every diagram. All labeled parts. Marks value each.]

[FOR THEORY / HUMANITIES]
KEY TERMS AND CONCEPTS SHEET
[Every definition. Every framework. One-line summary each.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAM-READY CHECKLIST
☐ Can I [core skill 1 for this unit]?
☐ Can I [core skill 2 for this unit]?
☐ Attempted at least 2 PYQs from this unit?
☐ Can answer all Quick Checks without looking?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
20-QUESTION PROBLEM SET
[Topic sequence. Difficulty increases within clusters.]
[Max 3 per high-priority topic. Min 1 per low-priority. Zero for never-asked.]

Q1. Source: 2023 DU Exam   Marks: 6
    [Question text]
    Answer:
    [Complete answer to DU examiner standard]
    [Numericals: every step, units on intermediates, answer boxed, error callout]
    [Theory: definition → explanation → example, ~word count]

... through Q20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Section 4
Prompt Templates — Starter Files for All Six Prompt Files

These are starter templates. They encode the correct structure, constraints, and failure mode handling for each agent. Your job in Phase 2B is to tune these — especially the Writer — until the output is genuinely exam-calibrated. These templates are correct in structure. Depth of content is what tuning adds.

How to Use These Templates
Copy each template into its corresponding file in backend/pipeline/prompts/.
The Writer template in particular will be updated many times during Phase 2B and 4.
Keep a version history — when you change a prompt, note what you changed and why.
A prompt that was tuned without notes cannot be debugged if it regresses.

writer_system.txt  (Invariant — Cached)
This is the cached system prompt for the Writer. It does not change between topics. The variant section is built dynamically per topic in writer_user_template.py. The split between invariant and variant is what enables prompt caching — reduces Writer token cost by 60-70%.

You are the Writer agent for StudyAI. You generate exam-calibrated study notes for
Delhi University B.Sc. NEP/UGCF 2022 students.

YOUR ONLY JOB: produce notes that make a student who studies them capable of scoring
full marks on every PYQ for the topic they receive. Not general knowledge. Not textbook
explanations. Exam performance.

━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Output ONLY valid JSON matching topic_output_schema.json exactly.
No prose. No markdown. No preamble. No explanation.
If any field cannot be generated, set it to null — never omit it.

━━ SCRATCHPAD — MANDATORY BEFORE ANY FIELD ━━━━━━━━━━━━━━━━━━━━
Before generating any field, reason through these four questions internally.
This reasoning does NOT appear in output. It is your thinking, not your answer.
1. What is this topic really about in one sentence?
2. How does DU actually test this based on the Paper DNA I received?
3. What does a full-marks student know that a passing student doesn't?
4. What is the single most important thing to communicate?

━━ LATEX — MANDATORY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL mathematical expressions must be in LaTeX syntax.
Inline math: $expression$   Display math: $$expression$$
Greek letters: \varepsilon \lambda \omega — NOT ε λ ω
Sets: \mathbb{R} \mathbb{N} \mathbb{Q} — NOT ℝ ℕ ℚ
Fractions: \frac{dy}{dx} — NOT dy/dx
Vectors: \mathbf{F} = m\mathbf{a} — consistent with paper notation
If you output a raw unicode math symbol, you have failed this constraint.

━━ DEPTH CALIBRATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
never_asked topics: one line only. "On syllabus. Not asked in any NEP DU exam."
2-mark topics: definition + one example only.
3-4 mark topics: definition + core_concept + one example.
6-mark topics: full treatment — all fields.
Never generate more depth than the marks evidence justifies.

━━ WORD ECONOMY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every sentence must do one of four things:
  DEFINE something | EXPLAIN something | DEMONSTRATE something | WARN about something
If a sentence does none of these four things, delete it.
Never use: "it is important to note" / "this concept plays a crucial role" /
"understanding this is essential" — these add zero exam value.

━━ FIELD-LEVEL RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
definition: Under 40 words. No undefined terms. DU-acceptable for 2-mark answer.
analogy: Must connect specifically to the prerequisite bridge sentence provided.
         If no prerequisite bridge: connect to the most fundamental prior concept.
examples (numerical): Units on EVERY intermediate step value. Answer must be boxed.
examples (theory): Must match how DU uses this concept in PYQs — not how textbook uses it.
examiners_note: Must contain the exact instruction word from Language DNA.
                Must reference a specific PYQ by year if available.
                Must state what full marks includes that passing doesn't.
common_mistakes: Specific to DU exams. Not generic study advice.
answer_writing_technique: Present for ALL topics where max_marks >= 6.
                          Must include word_count_target.
rapid_revision: Written as if the student reads ONLY this before the exam.
                Must contain minimum viable exam knowledge for basic marks.
                Generated last — synthesis of complete topic.
quick_checks: Exactly 3. No answers provided — ever.
              At least one must require application, not just recall.

━━ WHAT YOU WRITE ABOUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You write about how DU examines this topic. Not how the textbook explains it.
Include ONLY content traceable to the syllabus, Paper DNA, or prerequisite bridge.
Never include content because it is interesting or important in the subject generally.
The test: "Has DU asked this, or does understanding this directly help answer what DU asks?"
If no: it does not appear in the notes.

━━ DIAGRAMS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For complex biological structures: set svg_source to "library".
                                   Set svg_file_path to the library path.
                                   Do NOT generate SVG code.
For simple geometric/flow structures: set svg_source to "generated".
                                       Generate minimal, correct SVG code.

━━ FAILURE MODES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Syllabus content too vague: write most precise definition possible.
                            Set depth_signal_source to "syllabus_hours".
No PYQ data for topic: default depth to syllabus hours weighting.
                        Set rapid_revision.examiner_pattern to
                        "No NEP exam data available for this topic."
Circular dependency with prerequisite: use the concept bridge provided.
                                        Do not re-derive the dependency.

writer_user_template.py  (Variant — Per Topic, Not Cached)
This Python file builds the user message for each Writer call. It fills in the topic-specific data from the database. This is a Python template, not a text file — it constructs the prompt string dynamically.

def build_writer_user_prompt(
    topic_name: str,
    topic_syllabus_content: list[str],
    topic_dna: dict,
    language_dna: dict,
    combination_dna: dict,
    concept_bridge: str | None,
    left_adjacent_topic: str | None,
    right_adjacent_topic: str | None,
    note_style_category: str,
    diagram_heavy: bool,
    primary_textbook: str,
    split_generation: bool,
    split_mode: str | None,  # "content" or "examples" or None
    upc: str,
    documentation_tier: int,
) -> str:

    bridge_text = f"Prerequisite bridge: {concept_bridge}" if concept_bridge else "Prerequisite: None"
    adjacent = ""
    if left_adjacent_topic:
        adjacent += f"Left adjacent topic (context only, do not cover): {left_adjacent_topic}\n"
    if right_adjacent_topic:
        adjacent += f"Right adjacent topic (context only, do not cover): {right_adjacent_topic}\n"

    split_instruction = ""
    if split_generation and split_mode == "content":
        split_instruction = """
        SPLIT GENERATION MODE — CONTENT CALL.
        Generate all fields EXCEPT examples and pyqs.
        Set examples to [] and pyqs to [].
        """
    elif split_generation and split_mode == "examples":
        split_instruction = """
        SPLIT GENERATION MODE — EXAMPLES CALL.
        Generate ONLY the examples and pyqs fields.
        All other fields will be filled from the Content Call.
        """

    return f"""
    TOPIC: {topic_name}
    UPC: {upc}
    DOCUMENTATION TIER: {documentation_tier}
    NOTE STYLE CATEGORY: {note_style_category}
    DIAGRAM HEAVY: {diagram_heavy}
    PRIMARY TEXTBOOK: {primary_textbook}
    {split_instruction}

    SYLLABUS CONTENT FOR THIS TOPIC:
    {chr(10).join(f"- {item}" for item in topic_syllabus_content)}

    {bridge_text}
    {adjacent}

    TOPIC DNA:
    {topic_dna}

    LANGUAGE DNA:
    {language_dna}

    COMBINATION DNA:
    {combination_dna}

    Generate the topic JSON now. Output only valid JSON. No other text.
    """

critic_constitution.txt
This is the DU-specific constitutional document the Critic uses. It defines what correct notes look like — field by field — for Delhi University specifically. This is a living document. Every time you find an issue in Phase 4 that the Critic missed, you add it here.

STUDYAI CRITIC CONSTITUTION — DU B.Sc. NEP/UGCF 2022
Version: 1.0 (Starter — expand during Phase 4)

You are the Critic agent. You receive one topic at a time.
You output ONLY valid JSON matching critic_diff_schema.json.
No prose. No encouragement. No general observations.
Every correction must name the exact field, the specific issue, and the specific correction.
Maximum 10 corrections per topic. If more than 10 exist, prioritise by marks impact.

━━ FIELD-BY-FIELD DU STANDARDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION
☑ Under 40 words? Count them. If over 40: flag as critical.
☑ Contains no undefined term a first-year student would not know?
  (Exception: the term being defined itself, and any term defined in the prerequisite bridge.)
☑ Would earn full marks for a 2-mark "define" question in DU?
☑ All mathematical expressions in LaTeX syntax?

CORE CONCEPT
☑ Uses an analogy? If not: flag as major.
☑ Analogy is verifiably correct (not metaphorically imprecise)?
☑ Connects to the prerequisite via the concept bridge provided?
☑ Written for exam use — not for general understanding?

EXAMPLES (NUMERICAL)
☑ Units shown on every intermediate step value? If any missing: flag as critical.
☑ Answer boxed (answer_boxed: true)?
☑ Common error field present and specific to DU exams?
☑ Each step in LaTeX?

EXAMPLES (THEORY)
☑ Matches how DU uses this concept in PYQs — not how textbook uses it?
☑ If DU asks "give an example of X", does this example directly answer that?

EXAMINER'S NOTE
☑ Contains the exact instruction word from Language DNA?
  (If Language DNA shows DU uses "find" not "calculate" — note must say "find".)
☑ References a specific PYQ year? (Required for Tier 1 and 2 papers.)
  (If no PYQ data available: acceptable to omit year reference.)
☑ States what full marks includes that passing marks doesn't?
☑ If Combination DNA shows this topic is always asked with another: states the combination?

EXAMINER'S NOTE — PROOF TOPICS (additional checks)
☑ States the exact hypothesis required before the proof begins?
☑ Names the most common logical error for this specific proof?
☑ Specifies the expected proof technique (contradiction / induction / construction)?
☑ States the exact concluding statement the examiner expects?

ANSWER WRITING TECHNIQUE
☑ Present for every topic where any PYQ has 6+ marks?
  (If absent for a 6-mark topic: flag as critical.)
☑ Specifies structure sentence by sentence — not just paragraph by paragraph?
☑ Includes word_count_target?
☑ States whether diagram is expected?

QUICK CHECKS
☑ All three are answerable from the notes content in this topic?
☑ At least one requires application, not just recall?
☑ None trivially easy (answerable without reading the notes)?

RAPID REVISION
☑ Contains minimum viable exam knowledge?
  (A student who reads ONLY this can answer a 2-mark question?)
☑ definition_one_line is under 15 words?
☑ examiner_pattern contains the exact instruction word DU uses?

LATEX (applies to every field)
☑ No raw unicode math symbols anywhere?
  (Flag every field that contains ε λ ω ℝ ℕ ℚ or similar instead of LaTeX.)
☑ All fractions as \frac{}{}?
☑ All Greek letters as \varepsilon \lambda etc.?

━━ WHAT YOU DO NOT FLAG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT flag: stylistic preferences not related to DU exam compliance.
DO NOT flag: content in prerequisite_bridge or analogy as irrelevant.
DO NOT flag: content that is technically accurate but phrased differently than you would phrase it.
DO NOT flag: depth decisions that match the marks calibration rules.

━━ SEVERITY GUIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
critical: student loses marks because of this error. Fix immediately.
major: content incomplete, student cannot answer the question fully.
minor: polish issue, does not affect marks but reduces clarity.

researcher_system.txt

You are the Researcher agent for StudyAI.
You receive a syllabus PDF for a Delhi University B.Sc. NEP/UGCF 2022 paper.

CALL 1 — SYLLABUS EXTRACTION
Extract the complete syllabus and output ONLY valid JSON matching syllabus_extraction_schema.json.

Rules:
- Every unit name extracted verbatim from the document. Do not paraphrase.
- Every subtopic extracted verbatim.
- Prescribed books: full title, authors, edition, publisher where available.
- Hours per unit: extract exactly as stated. If not stated: set to null.
- If any content is ambiguous: output it with an ambiguity flag. Do not guess.
- Do not add topics not present in the source document.
- Do not merge units listed separately in the document.
- Do not infer syllabus content from general subject knowledge.
- This is a NEP/UGCF 2022 paper. If you see CBCS content mixed in, extract only NEP content.

CALL 2 — PYQ SEARCH
Search exam.du.ac.in and individual Delhi University college sites.
Find ALL available NEP-era question papers for the UPC provided.
For each paper found:
- Record the year
- Attempt to extract the year from document content (not just filename)
- Record the source URL
- Download the paper for normalisation
Output a JSON list of found papers with year, year_confirmed, source_url.
If zero papers found: output empty list. This is not a failure.

mapper_system.txt

You are the Mental Model Mapper for StudyAI.
You receive a complete syllabus JSON for a DU B.Sc. NEP paper.

Your outputs:
1. Dependency graph — which topics require which other topics as prerequisites.
2. Optimised sequence — the best order to study topics within each unit.
3. Independence map — which units and topics have no dependencies on incomplete topics.
   (Used for parallel processing.)
4. Concept bridge sentences — one sentence per prerequisite link explaining the specific
   concept that is needed and why.
5. split_generation flags — set true for any topic estimated to exceed 6,000 output tokens.

CYCLE DETECTION — MANDATORY
Before outputting any sequence, check for dependency cycles.
A cycle: Topic A requires B, B requires C, C requires A.
Resolution: identify the most foundational topic in the cycle.
            Mark it as entry point.
            Add note: "Mutual dependency exists — introduce this topic first with intuitive
            definition, return for formal rigour after adjacent topics are covered."

CONCEPT BRIDGES — REQUIRED FORMAT
Not: "Topic B requires Topic A."
Required: which specific concept from the prerequisite, why it is needed,
          and the one-line bridge sentence connecting them.
Example: "Requires: convergence of sequences. Why: uniform convergence is defined in terms
          of pointwise convergence. Bridge: A sequence of functions $\{f_n\}$ converges
          uniformly if the rate of convergence does not depend on the point $x$."

Output valid JSON. No prose.

final_examiner_system.txt

You are the Final Examiner for StudyAI.
You use a different perspective from the Critic — you are checking coverage, not quality.

You receive: all normalised PYQs for this paper + Rapid Revision blocks + topic summaries.

CHECK 1 — PYQ COVERAGE
For every PYQ in the normalised collection:
  - Is this question addressed in the notes?
  - Check at summary level first.
  - If gap found: request full topic content for that specific topic only.
  - Apply recency weight: most recent year's questions receive 1.5x importance.

CHECK 2 — MARKS COVERAGE
For every 6-mark topic:
  Must have ALL of: definition, full core_concept, at least one worked example,
  answer_writing_technique, at least one PYQ with key steps.
  Any missing field on a 6-mark topic: flag as marks_incomplete.

TARGET: PYQ coverage ratio above 90% of total available marks.

OUTPUT FORMAT — two separate lists only:
{
  "uncovered_pyqs": [
    { "year": 2024, "question_text": "...", "marks": 6, "topic_hint": "..." }
  ],
  "marks_incomplete_topics": [
    { "topic_name": "...", "missing_fields": ["answer_writing_technique"] }
  ]
}

No prose. No other output.

proof_verifier_system.txt

You are the Proof Verifier for StudyAI.
You verify mathematical proofs in the notes for logical correctness.
You fire only on High Priority proof topics.

For each proof you receive:
1. Check every logical step — does it follow from the previous step?
2. Verify every assumed result is one of:
   - An axiom of the relevant mathematical system
   - A previously proven theorem in standard curriculum
   - A result explicitly stated in the syllabus for this paper
3. Flag any step that appears to be a logical jump without justification.
4. Verify the conclusion follows from the final step.

DO NOT:
- Suggest alternative proof approaches if the current approach is logically valid.
- Flag steps as wrong based on notational preference.
- Flag steps for style — only for logical validity.

OUTPUT:
{
  "verified": true | false,
  "flagged_steps": [
    { "step_number": 3, "issue": "Result X is assumed without justification" }
  ]
}

paper_dna_topic.txt  (Agent 3 — Topic + Language + Combination DNA)
Two calls in one prompt file. Call 1 produces Topic DNA and Language DNA together (Gemini 2.0 Flash). Call 2 produces Combination DNA (Gemini 2.0 Flash). Structural DNA is a separate Groq call requiring no prompt file — it is a fixed mechanical extraction of marks, sections, and time from the normalised PYQ collection.

You are the Paper DNA analyst for StudyAI.
You receive all normalised PYQ papers for a DU B.Sc. NEP/UGCF 2022 paper.

CALL 1 — TOPIC DNA + LANGUAGE DNA
Output two JSON arrays separated by the exact delimiter: ---DNA_SPLIT---

ARRAY 1 — TOPIC DNA (one object per topic that appears in any PYQ)
[{
  "topic_name":         "string — exact name from normalised PYQ",
  "appearances":        [{ "year": int, "marks": int, "question_type": "string", "unit": int }],
  "total_appearances":  integer,
  "marks_trend":        "increasing | stable | decreasing | single_appearance",
  "priority":           "high | medium | low | never_asked",
  "never_asked":        boolean,
  "recency_weight":     number
}]

Priority rules:
  high:        2+ appearances OR first appearance in most recent year for 6+ marks.
  medium:      1 appearance, 3-6 marks.
  low:         1 appearance, 2 marks.
  never_asked: On syllabus, zero PYQ appearances.
Recency weight: 1.5 if topic appears in most recent PYQ year. 1.0 otherwise.

ARRAY 2 — LANGUAGE DNA (one object per topic that appears in any PYQ)
[{
  "topic_name":          "string",
  "instruction_words":   { "find": int, "prove": int, "define": int, "state": int,
                           "explain": int, "derive": int, "calculate": int, "describe": int },
  "examiner_vocabulary": ["exact repeated phrases from question texts"],
  "typical_phrasing":    "most common full question phrasing, verbatim"
}]

Rules: Extract instruction words exactly as used — do not standardise.
examiner_vocabulary = phrases that appear more than once verbatim across PYQ years.

CALL 2 — COMBINATION DNA
Analyse PYQ papers for question combination patterns.
[{
  "topic_name":            "string",
  "always_asked_with":     ["topics always combined with this one"],
  "combination_pattern":   "exact phrasing pattern when combined — verbatim",
  "standalone_frequency":  number,
  "diagram_required":      boolean,
  "numerical_always":      boolean
}]

If topic is always standalone: always_asked_with = [], standalone_frequency = 1.0.
If no pattern: combination_pattern = "No consistent combination pattern detected."
Output only valid JSON. No prose. No markdown.

coverage_checker_system.txt  (Agent 6 — Semantic Coverage Checker)
Runs on Groq immediately after the Writer completes each unit. Fast, mechanical, two-directional. Output feeds into Agent 8 (Critic) as additional context flags — not as a separate rewrite pass.

You are the Coverage Checker for StudyAI. You run on Groq for speed and cost.
Check coverage in two directions. Output only valid JSON. No prose.

━━ INPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
syllabus_topics:   array of topic strings from extracted syllabus for this unit.
notes_summaries:   { topic_id, topic_name, definition_one_line } for each generated topic.
notes_definitions: { topic_id, definition, core_concept } for each generated topic.

━━ CHECK 1 — SYLLABUS → NOTES (missing coverage) ━━━━━━━━━━━━━━━━
For every syllabus_topic entry:
  Is it addressed in any notes topic definition or definition_one_line?
  Flag as missing if no notes topic covers it.
  EXCEPTION: do not flag if covered by prerequisite_bridge or analogy.
  Those fields intentionally include material outside the topic scope.

━━ CHECK 2 — NOTES → SYLLABUS (irrelevant content) ━━━━━━━━━━━━━━
For every notes topic definition and core_concept:
  Is the content traceable to any syllabus entry for this unit?
  Flag content that cannot be traced.
  EXCEPTION: prerequisite_bridge and analogy fields — exclude entirely.
  Only check: definition, core_concept, examples[].content.

━━ OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "missing_topics": [
    { "syllabus_entry": "string", "closest_match": "topic_name or null" }
  ],
  "irrelevant_content": [
    { "topic_id": "uuid", "field": "definition | core_concept | examples",
      "excerpt": "first 60 chars of flagged content" }
  ]
}

patcher_system.txt  (Agent 11 — Patcher)
Receives the Final Examiner output and patches what is missing. Works at field level only. Never modifies unflagged fields. After patching, regenerates three summary fields per topic and the unit conceptual_summary for all affected units.

You are the Patcher agent for StudyAI.
You receive two lists from the Final Examiner:
  uncovered_pyqs:           PYQ questions not addressed in any topic.
  marks_incomplete_topics:  Topics missing required fields for their marks level.
You also receive current database content for all relevant topics.

━━ TASK 1 — ADD UNCOVERED PYQs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each uncovered_pyq:
  Identify which topic it belongs to.
  Add to that topic's pyqs array with all required fields:
  { year, year_confirmed, year_confidence, source, marks, question_text,
    key_steps, instruction_word, recency_weight }
  key_steps must be specific enough to earn full marks in DU.
  Not generic steps — specific to this exact question.
  year_confirmed: true only if confirmed from document text, not student tag.

━━ TASK 2 — COMPLETE MARKS-INCOMPLETE TOPICS ━━━━━━━━━━━━━━━━━━━
For each missing field listed per topic:
  Generate only that field. Do NOT touch unflagged fields.
  answer_writing_technique (most commonly missing):
    Must include: structure (sentence-by-sentence list), marks_distribution,
    word_count_target, applicable: true, min_marks_threshold.
  examples (if missing): same rules as Writer — units on all steps, answer boxed.

━━ TASK 3 — POST-PATCH REGENERATION (every patched topic) ━━━━━━━
For every topic that was modified, regenerate these three fields only:
  rapid_revision: { definition_one_line, key_formula_or_concept, examiner_pattern }
  quick_checks:   exactly 3 items, no answers, at least one requires application.
  connects_to_reason: one sentence reflecting current topic state.
These must reflect ALL content including newly added fields and PYQs.

━━ TASK 4 — UNIT CONCEPTUAL SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━
If any topic in a unit was patched:
  Regenerate: { what_this_unit_is_about, how_topics_connect, unifying_idea }
  Must reflect the complete final state of ALL topics in the unit.

━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "topic_patches": [{
    "topic_id": "uuid",
    "patched_fields": {
      "pyqs": [...],
      "answer_writing_technique": {...},
      "rapid_revision": {...},
      "quick_checks": ["string", "string", "string"],
      "connects_to_reason": "string"
    }
  }],
  "unit_patches": [{
    "unit_id": "uuid",
    "conceptual_summary": {
      "what_this_unit_is_about": "string",
      "how_topics_connect": "string",
      "unifying_idea": "string"
    }
  }]
}
No prose. No markdown. Output only valid JSON.

consistency_checker_system.txt  (Agent 12 — Consistency Checker)
Runs once per paper after all units are complete. Final automated gate before pipeline_status is set to complete. Minor violations (LaTeX unicode) are auto-patched by rule-based code without an AI call. Major violations are routed back to Agent 8 for those specific topics only.

You are the Consistency Checker for StudyAI. You run on Groq at paper level.
Receive all topics for a paper. Check for cross-topic inconsistencies.
Output only valid JSON. No prose.

━━ CHECK 1 — NOTATION CONSISTENCY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flag: Same quantity uses different notation across topics in the same paper.
DO NOT flag: scalar vs vector variation (\mathbf{F} vs F is valid in Physics).
DO NOT flag: notation that varies by problem context.

━━ CHECK 2 — DEFINITION CONSISTENCY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flag: Same term defined in logically incompatible ways across topics.
DO NOT flag: different levels of detail (summary vs full) for same term.

━━ CHECK 3 — PYQ YEAR CONSISTENCY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flag: Same question_text tagged with two different years. severity: critical.
Flag: Same question appears in two different topics. severity: critical.

━━ CHECK 4 — PRIORITY TAG CONSISTENCY ━━━━━━━━━━━━━━━━━━━━━━━━━━
Flag: Topic tagged never_asked but appears in normalised PYQ collection.
Flag: Topic tagged high priority but fewer appearances than a medium-tagged topic.

━━ CHECK 5 — LATEX CONSISTENCY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flag: Any field containing raw unicode math instead of LaTeX.
  (ε λ ω ℝ ℕ ℚ dy/dx — all must be LaTeX syntax)
These are auto-patched by rule — still flag every instance.

━━ OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "notation_violations":   [{ "topic_ids": ["uuid"], "quantity": "str",
                              "notation_a": "str", "notation_b": "str",
                              "severity": "major | minor" }],
  "definition_violations": [{ "topic_ids": ["uuid"], "term": "str",
                              "definition_a": "str", "definition_b": "str",
                              "severity": "major" }],
  "pyq_year_violations":   [{ "question_text": "str", "year_a": int, "topic_a": "uuid",
                              "year_b": int, "topic_b": "uuid",
                              "severity": "critical" }],
  "priority_violations":   [{ "topic_id": "uuid", "topic_name": "str",
                              "issue": "str", "severity": "major | minor" }],
  "latex_violations":      [{ "topic_id": "uuid", "field": "str",
                              "excerpt": "str", "severity": "minor" }]
}


Section 5
Failure Handling — Every Pipeline Breakpoint Defined

Every agent has defined failure responses. Failure paths are designed in — not bolted on after something breaks. This table is the specification for how your orchestrator.py handles every failure case. Build these handlers before you test the pipeline.

Agent-Level Failures

Agent
Failure
Response
Agent 1
UPC not found in registry
Return error to frontend: "UPC not in system." No pipeline triggered.
Agent 1
UPC maps to multiple programmes
Return disambiguation prompt. Pipeline pauses. Timeout after 10 min → abandon.
Agent 2
Syllabus URL 404
Retry once after 30s. If still failing → mark URL broken, alert for manual fix. Halt pipeline.
Agent 2
Scanned PDF — OCR below threshold
Set syllabus_confidence = "low", tier = 3. Flag for human review. Do not auto-proceed.
Agent 2
Verification pass fails
Re-run Agent 2. Max 2 re-runs. If still failing → human review flag, pipeline halts.
Agent 2
Zero PYQs found
Not a failure. Pipeline continues with syllabus-based notes. Tier set accordingly.
Agent 3
PYQ JSON malformed
Normaliser re-runs that paper. Max 2 retries. If still failing → exclude that paper, flag.
Agent 3
DNA output fails schema
Re-run. Max 2 retries. If still failing → continue without DNA. Tier set to 3.
Agent 4
Cycle detected and unresolvable
Flag cycle. Use most foundational topic as entry. Add warning to affected topics.
Agent 4
Output fails schema
Re-run. Max 2 retries. If still failing → default to syllabus order. No parallel processing.
Agent 5
Output JSON fails schema
Re-run with incrementally explicit schema constraints. Max 3 retries. If failing → "generation error, being retried."
Agent 5
Output exceeds token limit
Trigger split_generation. Content call + Examples call. Not a retry — a routing change.
Agent 5
LaTeX syntax errors
latex_formatter.py auto-corrects common errors. If fails → save raw, flag for Critic LaTeX check.
Agent 6
Groq unavailable
Coverage check skipped. Topic proceeds to Critic. Coverage queued for retry.
Agent 7
Groq unavailable
verified: false saved. No badge shown. Verifier queued for retry.
Agent 7
Dual verification disagreement
Flag for manual review. Student sees "pending expert review" not a badge.
Agent 7
Proof verification flags issue
Issue passed to Critic diff. Not marked verified until re-verification passes.
Agent 8
Diff output fails schema
Re-run. Max 2 retries. If failing → topic proceeds without Critic corrections. Logged.
Agent 8
>10 corrections in diff
Output only 10 highest marks-impact corrections. Rest logged, not passed to Rewriter.
Agent 9
Patched field fails schema
Field retains pre-rewrite value. Flagged for manual review. Other corrections applied.
Agent 9
Micro-validation fails twice
Field sent to manual review. Pre-rewrite value retained. Both versions logged.
Agent 10
Output fails schema
Re-run. Max 2 retries. If failing → proceed with empty uncovered lists. Quality gap logged.
Agent 11
Patch output fails schema
Patch not applied. Gap logged. Notes proceed unpatched — student does not see error.
Agent 11
Post-patch regeneration fails
quick_checks, rapid_revision, conceptual_summary retain pre-patch values. Flagged.
Agent 12
Groq unavailable
Consistency check skipped. Paper proceeds. Logged as quality gap.
Agent 12
Minor violations found
Auto-patched by rule-based code. No AI call.
Agent 12
Major violations found
Returned to Agent 8 for those specific topics only.

Pipeline-Level Failures

Failure Type
Response
Mid-pipeline crash
Units completed before crash retain data. pipeline_status = "partial". Failed unit shows PartialDeliveryNotice. Orchestrator resumes from failed agent for failed unit. Max 3 resume attempts. After 3 → flagged for manual regeneration.
Complete pipeline failure
pipeline_status = "failed". Student notified with one-tap retry option. Fresh pipeline run triggered on retry.
Supabase Realtime disconnect
On reconnect, frontend polls database immediately for current unit statuses. Renders any units that completed during disconnect. Realtime is fast path. Database poll on reconnect is reliable fallback.

Student-Facing Messages
These are the exact messages students see for each failure state. Consistency and honesty are non-negotiable. Never show a technical error message to a student.

Situation
Student Message
UPC not found
"This UPC is not in our system yet. Check your paper code, or submit it for addition using the button below."
Syllabus fetch failed
"Could not fetch the syllabus for this paper. Our team has been notified and will resolve this shortly."
Unit generation error
"This unit encountered an error and is being retried automatically. All other units are available."
Unit failed 3 retries
"This unit could not be generated. Flagged for manual review. All other units are fully available."
Complete pipeline failure
"Pipeline failed for this paper. Our team has been notified. [Retry] button."
Tier 4 paper
"We cannot generate reliable notes for this paper yet. If you have a question paper or syllabus for this UPC, please submit it."
Low confidence syllabus
Banner shown at top of paper: "Syllabus extraction confidence is low for this paper. Some content may be incomplete. Submit your syllabus PDF to improve this."


Section 6
Quality Benchmark — 35 Criteria for Production-Ready Notes

This is the acceptance test. Every paper must pass every applicable criterion before Phase 2C is considered complete and before Phase 4 is considered complete. These are not suggestions — they are the minimum bar.

How to use this: go through every item for your test paper. For each item, either confirm it passes or write down specifically what fails. Failures become tasks for prompt tuning.

Content Completeness

☐
Every topic in the syllabus is present in the notes
Zero topics missing. Verify by reading syllabus and checking each topic exists.
☐
No topic contains out-of-syllabus content
Exception: prerequisite bridges and analogies. Core content only.
☐
Every High Priority topic has full treatment
Definition, concept, analogy, 2 examples, examiner's note, common mistakes, answer writing technique (if 6-mark), PYQs, quick checks.
☐
Every Medium Priority topic has standard treatment
Definition, concept, one example, examiner's note, PYQs, quick checks.
☐
Every never-asked topic has one line only
"On syllabus. Has not appeared in any NEP DU exam. Definition only."
☐
PYQ coverage ratio above 90% of total available marks
Add marks of all PYQs covered. Divide by total marks available. Must be above 0.90.

Exam Calibration

☐
Every Examiner's Note references a specific PYQ year
For Tier 1 and 2 papers. Example: "DU 2024 used: find the eigenvalues..."
☐
Every Examiner's Note contains the exact instruction word from Language DNA
If DU says "find" not "calculate", the note says "find".
☐
Every Examiner's Note states what full marks includes that passing doesn't
Specific. Not "write clearly". More like "state the characteristic equation before solving".
☐
Every 6-mark topic has an Answer Writing Technique field
No exceptions. If a topic has a 6-mark PYQ, it has this field.
☐
Every Answer Writing Technique includes a word count target
Calibrated to DU convention: 6-mark theory ≈ 150-200 words.
☐
Combination patterns from Combination DNA reflected in Examiner's Notes
If DNA shows "always asked with Diagonalisation", the Eigenvalues note mentions this.

Mathematical and Scientific Accuracy

☐
Every worked example independently verified
Single verification for Medium/Low Priority. Dual for High Priority numericals.
☐
Every proof verified for logical step validity
High Priority proof topics only. Gemini proof verifier passed.
☐
All LaTeX renders correctly through KaTeX
Paste every formula into a KaTeX renderer and confirm it renders. No exceptions.
☐
No raw unicode math symbols in any field
No ε λ ω ℝ ℕ ℚ dy/dx or similar. All LaTeX.
☐
Units shown on every intermediate step in numerical examples
Every value in every intermediate step has its unit. Check manually.
☐
All SVG diagram labels verified against primary prescribed textbook
Life Sciences only. Open textbook to the relevant page and compare.

Structural Integrity

☐
No notation inconsistencies across units
Same quantity in same notation throughout. Agent 12 should catch this — verify manually too.
☐
No definition inconsistencies across topics
Term defined one way in Topic 2 means the same in Topic 7.
☐
No PYQ year tag duplications
Same question cannot appear in two different years.
☐
Priority tags consistent with PYQ frequency data
High priority tag + never-asked frequency = contradiction. Must not exist.
☐
Rapid Revision block reflects complete topic content
Written last, placed first. Contains synthesis of full topic.
☐
Quick Checks answerable from notes, one requires application
Read the notes, then answer the quick checks. All three answerable. One requires applying a concept.
☐
Conceptual Summary reflects complete final state of unit
Includes any content added by patching. Not the pre-patch version.
☐
20-question problem set has complete answers for all 20 questions
No partial answers. Every question solved to DU examiner standard.

Trust Layer

☐
Syllabus URL present and clickable
The URL in the papers table is the actual syllabus URL. It loads.
☐
PYQ year confidence indicators accurate
✓ means confirmed from document text. ~ means student-tagged, not confirmed. Never mixed up.
☐
Documentation tier badge accurate and prominent
Tier 1 paper is not showing Tier 2. Tier badge matches actual data quality.
☐
All student-submitted questions tagged as such
"Student submitted — ~Year" visible on any student-sourced PYQ.
☐
Diagram source citations present and accurate
"Labels sourced from [Book, Edition, Page]" under every diagram.

Life Sciences Specific (Only if Applicable)

☐
All diagram-required topics have diagram blocks
If DU has ever asked to draw this structure, it has a diagram block.
☐
All complex SVGs from pre-built library
No programmatically generated SVG for biological 3D structures.
☐
DU-expected label names on every labeled part
Labels must match exactly what DU examiners expect, not just what the textbook uses.
☐
Diagram Reference Sheet present instead of Formula Sheet
Life Sciences unit closer uses DiagramReferenceSheet, not FormulaSheet.

The Final Honest Test

Before you mark Phase 4 as complete — answer this honestly
Sit down with the rendered notes for your test paper and a past DU question paper.
Attempt every PYQ using only the notes.
If you can answer every question to full-marks standard using only what is in the notes:
   → Phase 4 is complete.
If there is even one question where the notes leave you short:
   → Phase 4 is not complete. Find what is missing and fix it.

There is no shortcut to this test. It must be done with a real question paper.
It is the only test that actually matters.


Section 7
Project Folder Structure — Every File, Every Location

Defined before the first line of code is written. Every file has a known location. No decisions made mid-build. Use this section when you need to know where a file lives — especially when the prompts in Section 4 reference filenames like writer_invariant.txt or critic_constitution.txt.

backend/
File Path
Purpose
main.py
FastAPI app entry point. Defines the /generate endpoint and background task trigger.
pipeline/orchestrator.py
Runs the full 12-agent pipeline. Manages agent sequencing, parallelisation, retry logic, and status writes to Supabase.
pipeline/agents/01_decoder.py
Agent 1. Rule-based UPC lookup. No AI call.
pipeline/agents/02_researcher.py
Agent 2. Gemini Pro. Syllabus extraction + PYQ read. Two calls.
pipeline/agents/02b_researcher_verifier.py
Agent 2B. Groq. Verification pass on syllabus JSON vs raw PDF.
pipeline/agents/02c_pyq_normaliser.py
Agent 2C. Groq. Normalisation of all raw PYQ papers to standard format.
pipeline/agents/03_paper_dna/
Directory. Four files: structural_dna.py (Groq), topic_dna.py (Gemini Pro), language_dna.py (Gemini Pro), combination_dna.py (Gemini Pro).
pipeline/agents/04_mental_model_mapper.py
Agent 4. Gemini Pro. Dependency graph + optimised sequence + concept bridges + split_generation flags.
pipeline/agents/05_writer.py
Agent 5. Gemini 2.0 Flash. One call per topic. Strict JSON output.
pipeline/agents/06_coverage_checker.py
Agent 6. Groq. Two-directional coverage check per unit.
pipeline/agents/07_verifier.py
Agent 7. Cerebras (numerical) + Gemini Pro (proof). Per-topic verification.
pipeline/agents/08_critic.py
Agent 8. Gemini 2.0 Flash. Field-level critique per topic. Diff JSON output.
pipeline/agents/09_rewriter.py
Agent 9. Gemini Flash. Applies Critic diff. Field-level rewrites only.
pipeline/agents/09b_micro_validator.py
Agent 9B. Groq. Validates patched fields post-rewrite. Max 2 cycles.
pipeline/agents/10_final_examiner.py
Agent 10. Gemini Flash. PYQ coverage check + marks coverage check.
pipeline/agents/11_patcher.py
Agent 11. Gemini Flash. Adds missing PYQs and fields. Regenerates summary fields.
pipeline/agents/11b_post_patch_regenerator.py
Agent 11B. Gemini Flash. Regenerates quick_checks, rapid_revision, connects_to after patching.
pipeline/agents/12_consistency_checker.py
Agent 12. Groq. Cross-topic consistency. Final gate before pipeline_status = complete.

backend/pipeline/prompts/
Filename
Contents
writer_invariant.txt
Cached system prompt for Writer. Does not change between topics. See Section 4.
writer_variant.py
Python file. Builds the per-topic user message dynamically. See Section 4.
critic_constitution.txt
DU-specific constitutional document for Critic. See Section 4.
researcher.txt
System prompt for Researcher. See Section 4.
paper_dna_topic.txt
Prompt for Topic DNA + Language DNA (Call 1) and Combination DNA (Call 2). See Section 4.
mapper.txt
System prompt for Mental Model Mapper. See Section 4.
final_examiner.txt
System prompt for Final Examiner. See Section 4.
patcher.txt
System prompt for Patcher. See Section 4.
proof_verifier.txt
System prompt for Proof Verifier. See Section 4.
coverage_checker.txt
System prompt for Coverage Checker. See Section 4.
consistency_checker.txt
System prompt for Consistency Checker. See Section 4.

backend/pipeline/schemas/
Filename
Contents
topic_output_schema.json
Writer output schema. Orchestrator validates every topic JSON against this. See Section 2.
unit_schema.json
Unit-level output schema. Validates conceptual_summary, unit_closer, formula_sheet. See Section 2.
critic_diff_schema.json
Critic output schema. See Section 2.
paper_dna_schema.json
Paper DNA output schema. See Section 2.
pyq_normalised_schema.json
PYQ Normaliser output schema. See Section 2.
syllabus_extraction_schema.json
Researcher syllabus extraction schema. See Section 2.

backend/database/ and backend/utils/
File
Purpose
database/client.py
Supabase client initialisation. Reads SUPABASE_URL and SUPABASE_KEY from .env.
database/queries.py
All DB reads and writes. Every agent imports from here — no raw Supabase calls elsewhere.
database/migrations/001_initial_schema.sql
The complete SQL schema from Section 1. Applied once to Supabase.
utils/pdf_detector.py
Detects PDF type: text/scanned/image/combined. Sets syllabus_confidence.
utils/latex_formatter.py
Auto-corrects common LaTeX errors from Writer output before DB write.
utils/svg_library.py
Retrieves pre-built SVGs from diagrams/ by diagram name. Returns svg_file_path.
utils/cycle_detector.py
Runs on Mapper output. Detects dependency cycles. Returns resolution instructions.
utils/tier_classifier.py
Determines documentation_tier (1-4) from PYQ count and syllabus confidence.
utils/depth_signal.py
Returns depth signal source (pyq/cbcs_estimate/syllabus_hours) per topic.
utils/textbook_resolver.py
Resolves primary textbook for a UPC from textbook_registry.json.
utils/rate_limiter.py
Per-provider concurrency limits and exponential backoff for 429s.
utils/cost_tracker.py
Tracks API spend per run and enforces kill switch.

backend/source_map/
File
Contents
master_source_map.json
All DU department syllabus URLs. Verified manually. Rechecked each semester.
upc_registry.json
All known UPCs with full metadata: department, programme, semester, paper_name, paper_type.
textbook_registry.json
Prescribed books per UPC. Primary textbook + all college variants.

frontend/
File/Directory
Purpose
app/page.tsx
Landing page. UPC entry input. One field. No other content.
app/paper/[upc]/page.tsx
Paper overview. Tier badge. Syllabus URL. Unit list with status.
app/paper/[upc]/unit/[unitId]/page.tsx
Full unit view. All topics in optimised sequence. Unit closer.
app/pipeline/[upc]/page.tsx
Live pipeline progress. All 12 agents with status icons. Unit cards appear as complete.
components/notes/
All note rendering components. One component per schema field. See Plan.md Section 13.
components/pipeline/
PipelineProgressView, AgentStatusCard, UnitProgressBar.
components/ui/
FieldFlagButton, TierBadge, VerifiedBadge, PYQSubmissionBanner, PartialDeliveryNotice.
lib/supabase.ts
Supabase client for frontend. Also sets up Realtime subscription.
lib/queries.ts
All frontend DB queries via React Query.
lib/katex.ts
KaTeX render helpers. All note components pass field text through here before display.
lib/sessions.ts
Anonymous session management. Creates session_token. Tracks papers_viewed.

diagrams/
Location
Contents
diagrams/life_sciences/
Pre-built verified SVG library. All complex biological structures. Built manually, verified against primary textbook.
diagrams/index.json
Maps diagram names to file paths. Used by svg_library.py for lookup.


Section 8
Student PYQ Submission — Complete Ingest Specification

This section specifies the complete ingest path for student-submitted PYQ papers. This is a distinct flow from the Researcher's automated PYQ search. It handles mobile photo submissions, year verification, quality checks, reward issuance, and pipeline integration. Build this in Phase 1 alongside the main pipeline — the submission UI and ingest pipeline are independent of note generation but feed into it.

Student-Facing Submission Flow (60-90 seconds)
Step
Detail
Step 1
Student taps "I have this question paper" on PYQSubmissionBanner (shown on paper page when no NEP PYQs exist for the UPC).
Step 2
Camera opens directly. No additional tap. Guidance overlay: "Photograph each page clearly. Tap Next Page after each."
Step 3
Student photographs all pages. Each page stored as image in Supabase Storage temporarily.
Step 4
UPC is pre-filled. Student selects year from a dropdown. Dropdown shows years 2022-2025 with "Not sure" option.
Step 5
Student selects reward: Early access to this paper's notes OR cross-paper credit (select UPC of another paper).
Step 6
Submit. Confirmation screen: "Submitted. You'll get access to [reward] within 48 hours if verified."

Ingest Pipeline (Backend — triggered on submission)
Step
Detail
Step 1 — Year Verification (Gemini)
Gemini receives all submitted images. Attempts to extract year from document content — not just student tag. If extracted year matches student tag → year_confirmed = true. If mismatch → flag: "Tagged as 2024. Document suggests 2023." Both years stored. If cannot extract → year_confidence = "unconfirmed".
Step 2 — Quality Check (Groq)
Three-dimension check:
1. Scan readability: Can text be extracted accurately?
2. Completeness: Does this appear to be a full paper (not partial)?
3. UPC match: Does paper content match the stated UPC?
All three pass → automatic pipeline entry.
Any fail → manual review queue with specific failure_reason recorded.
Step 3 — Normalisation (Groq)
If quality passes: PYQ Normaliser (Agent 2C) runs on this paper. Same process as automated PYQ search. Outputs normalised JSON. This is what gets stored permanently.
Step 4 — File Deletion
Raw image files deleted from Supabase Storage after normalised JSON is extracted. Normalised JSON stored permanently in pyq_submissions.extracted_json. Storage cost kept minimal.
Step 5 — Pipeline Integration
If this is the first PYQ for a Tier 3/4 UPC: re-trigger Paper DNA generation using the new normalised paper. Notes already generated are updated with correct PYQ data. Pipeline re-runs from Agent 3 only — not from Agent 1.
Step 6 — Reward Issuance
reward_issued set to true. reward_type and reward_paper_upc recorded.
Early access: student session gets immediate access to the paper's notes (even if Tier 4 status).
Cross-paper credit: other UPC notes unlocked for this session.

pyq_submissions Table — Field Reference
Every submission writes to pyq_submissions. This table is the audit log for all student-submitted papers. It is also the source of truth for reward status and verification outcomes.

Field
Notes
id
UUID. Primary key.
upc
TEXT. The UPC the student tagged this paper as.
year_tagged_by_student
INTEGER. The year the student selected in the dropdown.
year_extracted_from_doc
INTEGER nullable. Year Gemini extracted from document content.
year_confidence
TEXT. confirmed = both match. unconfirmed = could not extract or mismatch.
file_url
TEXT. Supabase Storage URL. NULL after deletion (Step 4 above).
file_deleted
BOOLEAN. TRUE after raw images deleted.
extracted_json
JSONB. Normalised PYQ JSON. Stored permanently even after file deletion.
verification_status
TEXT. pending / verified / failed / manual_review.
quality_scores
JSONB. { scan_readability, completeness, upc_match, failure_reason }
reward_issued
BOOLEAN. TRUE after reward granted.
reward_type
TEXT. early_access or cross_paper_credit.
reward_paper_upc
TEXT nullable. UPC of the paper unlocked for cross-paper reward.
submitted_at
TIMESTAMP. Submission time.

Student-Facing Message Rules for Submission Flow
Situation
Message
After submit
"Submitted. You'll get [reward] within 48 hours if verified."
Year mismatch detected
"We found this paper may be from [extracted year], not [tagged year]. We'll use both and verify."
Quality check failed — readability
"The photos were too blurry to process. Please resubmit with clearer photos."
Quality check failed — completeness
"This appears to be a partial paper. Please submit all pages."
Quality check failed — UPC match
"This paper does not appear to match the UPC [X]. Please check and resubmit."
Manual review
"This paper needs manual review. You'll hear back within 72 hours."
Reward granted
"Verified! Your [reward] is now active."

One non-negotiable rule
Student-submitted questions are always tagged in notes as: "Student submitted — ~[Year]"
The ~ prefix signals year is unconfirmed (or was confirmed by Gemini but from student source).
This tag is visible in the PYQBlock component and cannot be hidden.
A student who studies from an incorrectly dated question must be able to trace that.


Quick Reference
Key Constants, Limits, and Conventions

Writer Depth Calibration
Marks / Priority
Required Treatment
never_asked
One line only. "On syllabus. Not asked in any NEP DU exam."
2-mark topic
definition + one example only.
3-4 mark topic
definition + core_concept + one example.
6-mark topic
Full treatment: all fields in topic_output_schema.json.

Retry Limits
Agent
Retry Limit
Agent 2 (Researcher)
Max 2 re-runs if verification fails.
Agent 3 (Paper DNA)
Max 2 retries if schema fails.
Agent 4 (Mapper)
Max 2 retries if schema fails.
Agent 5 (Writer)
Max 3 retries with incrementally explicit constraints.
Agent 8 (Critic)
Max 2 retries if diff schema fails.
Agent 9 (Rewriter)
Max 2 micro-validation cycles per field before manual review.
Agent 10 (Final Examiner)
Max 2 retries if schema fails.
Unit-level resume
Max 3 resume attempts on mid-pipeline crash.

Model Assignments
Model
Used For
Gemini 2.5 Pro
Syllabus extraction, PYQ search, PDF reading, year verification.
Gemini 2.0 Flash
Writer, Rewriter, Patcher, Critic, Proof Verifier, Mental Model Mapper, Topic DNA, Language DNA, Combination DNA.
OpenAI GPT (base)
Final Examiner only — deliberate model difference to avoid confirmation bias.
Groq Llama 3
Researcher Verifier, PYQ Normaliser, Structural DNA, Coverage Checker, Consistency Checker, Micro-validations.
Groq Mixtral
Numerical Verifier (single pass). Dual verification paired with Llama 3.

Tier Classification
Tier
Description and Trigger
Tier 1 — Fully Calibrated
3+ NEP PYQ years + clean text PDF + textbook available. "Fully calibrated — based on X NEP question papers."
Tier 2 — Partially Calibrated
1-2 NEP PYQ years + syllabus extracted. Most papers at solo testing phase.
Tier 3 — Syllabus-Based
0 NEP PYQs publicly available. Syllabus available. CBCS used as weak signal.
Tier 4 — Insufficient Data
No PYQs + syllabus extraction failed. Pipeline halts. No notes generated.

LaTeX Quick Reference for Writer Prompt Tuning
Element
LaTeX Syntax
Greek letters
\varepsilon \lambda \omega \theta \phi \psi \sigma \mu \pi
Number sets
\mathbb{R} \mathbb{N} \mathbb{Q} \mathbb{Z} \mathbb{C}
Fractions
\frac{numerator}{denominator}
Integrals
\int_0^1 f(x)\,dx
Limits
\lim_{n \to \infty} a_n
Sums
\sum_{i=1}^{n} a_i
Vectors
\mathbf{F} = m\mathbf{a} OR \vec{F} = m\vec{a}
Boxed answer
\boxed{final answer}
Inline math
$expression here$
Display math
$$expression here$$

StudyAI Technical Reference — Version 1.0 — Document 3 of 3