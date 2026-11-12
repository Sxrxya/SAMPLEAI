export type Role = "candidate" | "recruiter" | "admin";

export type NavigationItem = {
  label: string;
  section: string;
  icon: string;
};

export type MatchResult = {
  candidateId: string;
  name: string;
  initials: string;
  headline: string;
  location: string;
  resumeVersion: string;
  jobReference: string;
  overallScore: number;
  confidence: "High" | "Medium" | "Low";
  completeness: number;
  dimensions: { label: string; score: number }[];
  skills: string[];
  missingSkills: string[];
  evidence: string[];
  ragEvaluation?: {
    candidate_name: string;
    overall_match_score: number;
    recommendation_verdict: "STRONG_HIRE" | "HIRE" | "CONSIDER" | "DO_NOT_RECOMMEND";
    executive_summary: string;
    parameter_scores: Record<
      string,
      {
        score: number;
        weight_pct: number;
        findings?: string;
        supporting_evidence?: string[];
        identified_gaps?: string[];
        mitigation_difficulty?: string;
      }
    >;
    key_strengths?: string[];
    potential_risks?: string[];
    tailored_interview_questions?: {
      topic: string;
      question: string;
      what_to_listen_for: string;
    }[];
  };
};

export type PortalRow = {
  name: string;
  detail: string;
  status: string;
  date: string;
  initials: string;
};

export const roleLabels: Record<Role, string> = {
  candidate: "Candidate",
  recruiter: "Recruiter",
  admin: "Super admin",
};

export const navigation: Record<Role, NavigationItem[]> = {
  candidate: [
    { label: "Resume Uploader", section: "resume", icon: "file" },
  ],
  recruiter: [
    { label: "AI JD Matching", section: "overview", icon: "sparkles" },
  ],
  admin: [
    { label: "System Telemetry", section: "overview", icon: "layout" },
  ],
};
