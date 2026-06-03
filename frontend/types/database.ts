export interface Paper {
  upc: string;
  paper_name: string;
  department: string;
  programme: string;
  semester: number;
  paper_type: string;
  tier?: number;
  pyq_years_available?: number[];
  syllabus_url?: string;
  syllabus_last_verified?: string;
}

export interface Unit {
  id: string;
  unit_id?: string; // alias for compatibility
  upc: string;
  unit_number: number;
  unit_name: string;
  estimated_study_hours: number;
  marks_weightage: number;
  status: 'queued' | 'generating' | 'complete' | 'failed';
  conceptual_summary?: string;
}

export interface Topic {
  id: string;
  topic_id?: string; // alias for compatibility
  unit_id: string;
  topic_number: number;
  topic_name: string;
  content: any;
}


export interface FormulaSheet {
  unit_id: string;
  sheet_type: string;
  content: any;
}

export interface ProblemSet {
  unit_id: string;
  content: any;
}

export interface PYQSubmission {
  id: string;
  upc: string;
  year_tagged_by_student: number;
  file_url: string;
  reward_type: string;
  reward_paper_upc: string;
  verification_status: string;
  reward_issued: boolean;
  file_deleted: boolean;
}
