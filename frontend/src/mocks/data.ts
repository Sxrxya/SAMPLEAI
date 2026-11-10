import type { MatchResult, PortalRow, Role } from "../types";

export const demoMatches: MatchResult[] = [
  {
    candidateId: "cand-1048",
    name: "Amara Johnson",
    initials: "AJ",
    headline: "Senior Product Designer",
    location: "Brooklyn, NY",
    resumeVersion: "Resume v3 · Oct 18, 2025",
    jobReference: "Senior Product Designer · JOB-2048",
    overallScore: 92,
    confidence: "High",
    completeness: 96,
    dimensions: [
      { label: "Required skills", score: 96 },
      { label: "Semantic relevance", score: 91 },
      { label: "Experience", score: 88 },
      { label: "Projects", score: 94 },
      { label: "Education", score: 82 },
    ],
    skills: ["Product strategy", "Figma", "Design systems", "User research"],
    missingSkills: ["B2B SaaS"],
    evidence: [
      "Led a design system adopted by 4 product teams, reducing interface inconsistencies.",
      "Seven years of product design experience, including three years in SaaS.",
      "Portfolio includes workflow redesigns with documented research and iteration.",
    ],
  },
  {
    candidateId: "cand-1192",
    name: "Theo Williams",
    initials: "TW",
    headline: "Product Designer · UX Research",
    location: "New York, NY",
    resumeVersion: "Resume v2 · Oct 20, 2025",
    jobReference: "Senior Product Designer · JOB-2048",
    overallScore: 87,
    confidence: "Medium",
    completeness: 83,
    dimensions: [
      { label: "Required skills", score: 89 },
      { label: "Semantic relevance", score: 91 },
      { label: "Experience", score: 79 },
      { label: "Projects", score: 90 },
      { label: "Education", score: 78 },
    ],
    skills: ["Figma", "Interaction design", "Prototyping", "User research"],
    missingSkills: ["Design systems", "Accessibility"],
    evidence: [
      "Research portfolio includes moderated interviews and usability studies.",
      "Four years of experience across consumer and enterprise product teams.",
      "Resume does not provide enough detail to verify design-system ownership.",
    ],
  },
];

export const demoRows: Record<Role, PortalRow[]> = {
  candidate: [
    {
      name: "Northstar Labs",
      detail: "Product Designer",
      status: "In review",
      date: "Oct 22",
      initials: "NL",
    },
    {
      name: "Fieldwork",
      detail: "Senior UX Designer",
      status: "Interview",
      date: "Oct 19",
      initials: "FW",
    },
    {
      name: "Goodkind",
      detail: "Design Systems Lead",
      status: "Submitted",
      date: "Oct 16",
      initials: "GK",
    },
  ],
  recruiter: [
    {
      name: "Amara Johnson",
      detail: "Senior Product Designer · 7 yrs",
      status: "New",
      date: "2h ago",
      initials: "AJ",
    },
    {
      name: "Theo Williams",
      detail: "Product Designer · 4 yrs",
      status: "Reviewing",
      date: "5h ago",
      initials: "TW",
    },
    {
      name: "Priya Shah",
      detail: "Product Designer · 6 yrs",
      status: "Shortlisted",
      date: "Yesterday",
      initials: "PS",
    },
    {
      name: "Malik Foster",
      detail: "UX Designer · 5 yrs",
      status: "Interview",
      date: "Yesterday",
      initials: "MF",
    },
  ],
  admin: [
    {
      name: "Evergreen Works",
      detail: "Employer verification",
      status: "Needs review",
      date: "12m ago",
      initials: "EW",
    },
    {
      name: "Brightpath Health",
      detail: "Job moderation · 3 roles",
      status: "Queued",
      date: "38m ago",
      initials: "BH",
    },
    {
      name: "Resume pipeline",
      detail: "Document processing",
      status: "Healthy",
      date: "1h ago",
      initials: "RP",
    },
    {
      name: "Olive & Oak",
      detail: "Company verification",
      status: "Approved",
      date: "Today",
      initials: "OO",
    },
  ],
};

export const demoJobs = [
  {
    title: "Senior Product Designer",
    company: "Northstar Labs",
    location: "New York · Hybrid",
    applicants: 48,
    status: "Active",
  },
  {
    title: "Product Design Lead",
    company: "Northstar Labs",
    location: "Remote · US",
    applicants: 31,
    status: "Active",
  },
  {
    title: "UX Researcher",
    company: "Northstar Labs",
    location: "New York · Hybrid",
    applicants: 16,
    status: "Draft",
  },
];

export const metricSets: Record<
  Role,
  { label: string; value: string; change: string; icon: string }[]
> = {
  candidate: [
    {
      label: "Profile completion",
      value: "82%",
      change: "+12% this week",
      icon: "user",
    },
    {
      label: "Applications sent",
      value: "8",
      change: "3 in review",
      icon: "send",
    },
    {
      label: "Profile views",
      value: "24",
      change: "+6 this week",
      icon: "eye",
    },
    {
      label: "New matches",
      value: "12",
      change: "Updated today",
      icon: "sparkles",
    },
  ],
  recruiter: [
    {
      label: "Open roles",
      value: "12",
      change: "+2 this month",
      icon: "briefcase",
    },
    {
      label: "New applicants",
      value: "84",
      change: "+18% this week",
      icon: "users",
    },
    {
      label: "Interviews booked",
      value: "16",
      change: "Across 6 roles",
      icon: "calendar",
    },
    {
      label: "Time to shortlist",
      value: "4.2d",
      change: "1.3d faster",
      icon: "timer",
    },
  ],
  admin: [
    {
      label: "Active accounts",
      value: "8,420",
      change: "+4.8% this month",
      icon: "users",
    },
    {
      label: "Pending reviews",
      value: "23",
      change: "8 need attention",
      icon: "shield",
    },
    {
      label: "Jobs moderated",
      value: "1,284",
      change: "This month",
      icon: "briefcase",
    },
    {
      label: "Processing health",
      value: "99.8%",
      change: "All systems normal",
      icon: "activity",
    },
  ],
};

export const activitySeries = [
  { week: "Sep 30", applicants: 34, interviews: 9 },
  { week: "Oct 07", applicants: 48, interviews: 12 },
  { week: "Oct 14", applicants: 42, interviews: 14 },
  { week: "Oct 21", applicants: 67, interviews: 19 },
  { week: "Oct 28", applicants: 58, interviews: 16 },
  { week: "Nov 04", applicants: 84, interviews: 22 },
];
