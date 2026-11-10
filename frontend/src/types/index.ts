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
    { label: "Overview", section: "overview", icon: "layout" },
    { label: "Getting started", section: "onboarding", icon: "check" },
    { label: "My profile", section: "profile", icon: "user" },
    { label: "Resume & skills", section: "resume", icon: "file" },
    { label: "Explore jobs", section: "jobs", icon: "briefcase" },
    { label: "Applications", section: "applications", icon: "send" },
    { label: "Notifications", section: "notifications", icon: "bell" },
    { label: "Settings", section: "settings", icon: "settings" },
  ],
  recruiter: [
    { label: "Overview", section: "overview", icon: "layout" },
    { label: "Job openings", section: "jobs", icon: "briefcase" },
    { label: "Applicants", section: "applicants", icon: "users" },
    { label: "AI matching", section: "matching", icon: "sparkles" },
    { label: "Interviews", section: "interviews", icon: "calendar" },
    { label: "Analytics", section: "analytics", icon: "chart" },
    { label: "Company profile", section: "company", icon: "building" },
    { label: "Notifications", section: "notifications", icon: "bell" },
    { label: "Settings", section: "settings", icon: "settings" },
  ],
  admin: [
    { label: "Overview", section: "overview", icon: "layout" },
    { label: "Candidates", section: "candidates", icon: "user" },
    { label: "Employers", section: "employers", icon: "building" },
    { label: "Recruiters", section: "recruiters", icon: "users" },
    { label: "Verification", section: "verification", icon: "shield" },
    { label: "Job moderation", section: "moderation", icon: "briefcase" },
    { label: "Resume processing", section: "processing", icon: "file" },
    { label: "Model settings", section: "models", icon: "sparkles" },
    { label: "Matching settings", section: "matching", icon: "sliders" },
    { label: "Permissions", section: "permissions", icon: "key" },
    { label: "Data retention", section: "retention", icon: "database" },
    { label: "Audit log", section: "audit", icon: "list" },
    { label: "System health", section: "health", icon: "activity" },
  ],
};
