CREATE EXTENSION IF NOT EXISTS vector;

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

CREATE TABLE topics (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  upc                       TEXT NOT NULL REFERENCES papers(upc) ON DELETE CASCADE,
  topic_name                TEXT NOT NULL,
  topic_number              INTEGER NOT NULL,
  difficulty                TEXT,               -- easy/medium/hard
  estimated_study_minutes   INTEGER,
  priority                  TEXT,               -- high/medium/low/never_asked
  prerequisite_topic_id     UUID REFERENCES topics(id),
  prerequisite_bridge       TEXT,
  status                    TEXT DEFAULT 'queued',
  connects_to_topic_id      UUID REFERENCES topics(id),
  connects_to_reason        TEXT,
  split_generation          BOOLEAN DEFAULT FALSE,
  depth_signal_source       TEXT,               -- pyq/cbcs_estimate/syllabus_hours

  -- Rapid Revision
  rapid_revision            JSONB,

  -- Core Content
  definition                TEXT,
  core_concept              TEXT,
  analogy                   TEXT,
  analogy_verified          BOOLEAN DEFAULT FALSE,

  -- Examples (array of example objects)
  examples                  JSONB,

  -- Diagram
  diagram_block             JSONB,

  -- Examiner Intelligence
  examiners_note            TEXT,
  examiners_note_pyq_refs   TEXT[],
  instruction_word_frequency JSONB,

  -- Mistakes
  common_mistakes           JSONB,

  -- Answer Writing
  answer_writing_technique  JSONB,

  -- PYQs
  pyqs                      JSONB,

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

CREATE TABLE problem_sets (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  questions                 JSONB NOT NULL
);

CREATE TABLE formula_sheets (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id                   UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  sheet_type                TEXT NOT NULL,      -- formula/diagram_reference/key_terms
  content                   JSONB NOT NULL
);

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
  reward_issued             BOOLEAN DEFAULT FALSE,
  reward_type               TEXT,               -- early_access/cross_paper_credit
  reward_paper_upc          TEXT,
  submitted_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE syllabus_change_log (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upc                       TEXT NOT NULL REFERENCES papers(upc),
  detected_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  old_hash                  TEXT,
  new_hash                  TEXT,
  diff_summary              JSONB,
  regeneration_status       TEXT DEFAULT 'pending',
  students_notified         BOOLEAN DEFAULT FALSE
);

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

CREATE TABLE sessions (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_token             TEXT UNIQUE NOT NULL,
  created_at                TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_active               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  papers_viewed             TEXT[]
);

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

-- Enable Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE units;
ALTER PUBLICATION supabase_realtime ADD TABLE topics;
