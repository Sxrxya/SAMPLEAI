import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Download,
  Eye,
  FileText,
  Filter,
  MapPin,
  MoreHorizontal,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  UsersRound,
  X,
  RefreshCw,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { lazy, Suspense } from "react";
import { Link, useParams } from "react-router-dom";
import { mockPortalService } from "../services/mockPortalService";
import { employerService } from "../services/employerService";
import { matchingService } from "../services/matchingService";
import { candidateService } from "../services/candidateService";
import { authService } from "../services/authService";
import { tokenStore } from "../services/tokenStore";
import { navigation, roleLabels, type MatchResult, type Role } from "../types";

const greetings: Record<Role, string> = {
  candidate: "Your next move, made clearer.",
  recruiter: "Good morning, Maya",
  admin: "The platform at a glance.",
};

const ActivityChart = lazy(() => import("../components/ActivityChart"));

export function PortalPage() {
  const { role: roleParam = "recruiter", section = "overview" } = useParams();
  const role = roleParam as Role;
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showJobForm, setShowJobForm] = useState(false);
  const activeNav = navigation[role].find((item) => item.section === section);
  const rows = mockPortalService.getRows(role);
  const filteredRows = useMemo(
    () =>
      rows.filter((row) =>
        `${row.name} ${row.detail} ${row.status}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [rows, search],
  );
  const heading =
    section === "overview"
      ? greetings[role]
      : (activeNav?.label ?? "Workspace");

  if (section === "overview")
    return <Overview role={role} onCreateJob={() => setShowJobForm(true)} />;

  const isMatchPage = section === "matching";
  const isJobsPage = section === "jobs";
  const isListPage = [
    "applicants",
    "candidates",
    "employers",
    "recruiters",
    "applications",
    "interviews",
    "verification",
    "moderation",
    "processing",
    "audit",
  ].includes(section);
  const helper = isMatchPage
    ? "Explore backend-provided matching results and inspect the evidence behind each score."
    : isJobsPage
      ? role === "candidate"
        ? "Discover roles aligned with your experience and interests."
        : "Create and manage the roles your team is hiring for."
      : section === "profile"
        ? "Keep your experience, preferences, and contact details current."
        : section === "resume"
          ? "Manage your resume and review information extracted from it."
          : section === "settings"
            ? "Manage your account, security, and communication preferences."
            : `Review and manage ${activeNav?.label.toLowerCase() ?? "workspace"} across your ${roleLabels[role].toLowerCase()} portal.`;

  return (
    <>
      <PageHeader
        eyebrow={`${roleLabels[role]} workspace`}
        title={heading}
        description={helper}
        action={
          isJobsPage && role !== "candidate" ? (
            <button
              className="button button-primary"
              onClick={() => setShowJobForm(true)}
            >
              <Plus size={16} /> Create job
            </button>
          ) : (
            <button className="button button-outline">
              <Download size={15} /> Export
            </button>
          )
        }
      />
      {isMatchPage ? (
        <MatchingResults />
      ) : isJobsPage && role === "candidate" ? (
        <JobDiscovery />
      ) : isListPage ? (
        <RecordsTable
          role={role}
          rows={filteredRows}
          search={search}
          onSearch={setSearch}
          page={page}
          setPage={setPage}
        />
      ) : (
        <WorkspaceSection role={role} section={section} />
      )}
      {showJobForm && <JobModal onClose={() => setShowJobForm(false)} />}
    </>
  );
}

function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  );
}

function Overview({
  role,
  onCreateJob,
}: {
  role: Role;
  onCreateJob: () => void;
}) {
  const metrics = mockPortalService.getMetrics(role);
  const rows = mockPortalService.getRows(role);
  return (
    <>
      <div className="overview-heading">
        <div>
          <span className="eyebrow">
            {roleLabels[role]} workspace · Tuesday, November 10
          </span>
          <h1>{greetings[role]}</h1>
          <p>
            {role === "candidate"
              ? "A little progress today can open up a lot of possibility."
              : role === "recruiter"
                ? "Here’s what’s happening across your hiring pipeline."
                : "A healthy marketplace starts with clear visibility."}
          </p>
        </div>
        {role === "recruiter" && (
          <button className="button button-primary" onClick={onCreateJob}>
            <Plus size={16} /> Create a job
          </button>
        )}
        {role === "candidate" && (
          <button className="button button-primary">
            <Search size={16} /> Find a role
          </button>
        )}
      </div>
      <div className="metric-grid">
        {metrics.map((metric, index) => (
          <MetricCard key={metric.label} metric={metric} index={index} />
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">PIPELINE ACTIVITY</span>
              <h2>
                {role === "candidate"
                  ? "Your job search"
                  : role === "admin"
                    ? "Marketplace activity"
                    : "Hiring activity"}
              </h2>
            </div>
            <button className="select-button">
              Last 6 weeks <ChevronDownIcon />
            </button>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-applicants" /> Applicants
            </span>
            <span>
              <i className="legend-interviews" /> Interviews
            </span>
            <span className="chart-trend">
              <ArrowUpRight size={14} /> 18.4%
            </span>
          </div>
          <Suspense
            fallback={
              <div
                className="chart-loading"
                aria-label="Loading activity chart"
              />
            }
          >
            <ActivityChart data={mockPortalService.getActivity()} />
          </Suspense>
        </section>
        <section className="panel action-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">NEXT UP</span>
              <h2>On your radar</h2>
            </div>
            <button className="icon-button" aria-label="More actions">
              <MoreHorizontal size={18} />
            </button>
          </div>
          <div className="action-list">
            {(role === "recruiter"
              ? [
                  [
                    "09:30",
                    "Portfolio review",
                    "Amara Johnson · Product Designer",
                    "Today",
                  ],
                  ["11:00", "Hiring sync", "Senior Product Designer", "Today"],
                  [
                    "14:15",
                    "Screening call",
                    "Theo Williams · Product Designer",
                    "Tomorrow",
                  ],
                ]
              : role === "candidate"
                ? [
                    [
                      "TODAY",
                      "Review your profile",
                      "Add a few details to reach 100%",
                      "12 min",
                    ],
                    [
                      "TOMORROW",
                      "Interview with Fieldwork",
                      "Senior UX Designer · Video call",
                      "10:30 AM",
                    ],
                    [
                      "THU, NOV 12",
                      "New job matches",
                      "12 roles fit your preferences",
                      "View roles",
                    ],
                  ]
                : [
                    [
                      "NOW",
                      "Company verification",
                      "Evergreen Works · 12 min ago",
                      "Review",
                    ],
                    [
                      "IN 38 MIN",
                      "Moderation queue",
                      "3 job descriptions need review",
                      "Open queue",
                    ],
                    [
                      "TODAY",
                      "Pipeline check",
                      "Resume processing · All clear",
                      "View health",
                    ],
                  ]
            ).map(([time, title, detail, tag]) => (
              <div className="action-item" key={title}>
                <span className="action-time">{time}</span>
                <span className="action-marker" />
                <div className="action-copy">
                  <strong>{title}</strong>
                  <span>{detail}</span>
                </div>
                <span className="action-tag">{tag}</span>
              </div>
            ))}
          </div>
          <button className="panel-link">
            View calendar <ArrowRight size={14} />
          </button>
        </section>
      </div>
      <section className="panel table-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">
              {role === "candidate"
                ? "YOUR APPLICATIONS"
                : role === "admin"
                  ? "REQUIRES ATTENTION"
                  : "RECENT APPLICANTS"}
            </span>
            <h2>
              {role === "candidate"
                ? "Application activity"
                : role === "admin"
                  ? "Review queue"
                  : "New applicants"}
            </h2>
          </div>
          <button className="panel-link">
            View all <ArrowRight size={14} />
          </button>
        </div>
        <RecordsTable role={role} rows={rows} compact />
      </section>
    </>
  );
}

function MetricCard({
  metric,
  index,
}: {
  metric: { label: string; value: string; change: string; icon: string };
  index: number;
}) {
  const iconList = [UsersRound, BriefcaseBusiness, CalendarDays, Sparkles];
  const Icon = iconList[index % iconList.length];
  return (
    <div className="metric-card">
      <div className={`metric-icon metric-tone-${index}`}>
        <Icon size={17} />
      </div>
      <span className="metric-label">{metric.label}</span>
      <div className="metric-value-row">
        <strong>{metric.value}</strong>
        <span className={index === 3 ? "metric-change warm" : "metric-change"}>
          {metric.change}
        </span>
      </div>
    </div>
  );
}

function RecordsTable({
  role,
  rows,
  compact = false,
  search,
  onSearch,
  page = 1,
  setPage,
}: {
  role: Role;
  rows: {
    name: string;
    detail: string;
    status: string;
    date: string;
    initials: string;
  }[];
  compact?: boolean;
  search?: string;
  onSearch?: (value: string) => void;
  page?: number;
  setPage?: (page: number) => void;
}) {
  const heading =
    role === "candidate"
      ? "Company / role"
      : role === "admin"
        ? "Account / item"
        : "Candidate";
  return (
    <div className={`records-wrap ${compact ? "records-compact" : ""}`}>
      {!compact && (
        <div className="table-toolbar">
          <label className="table-search">
            <Search size={15} />
            <input
              value={search ?? ""}
              onChange={(event) => onSearch?.(event.target.value)}
              placeholder={`Search ${navigation[role].find((item) => ["applicants", "applications", "candidates", "employers", "recruiters"].includes(item.section))?.label.toLowerCase() ?? "records"}...`}
            />
          </label>
          <button className="button button-outline filter-button">
            <Filter size={15} /> Filters <span className="filter-count">2</span>
          </button>
          <button
            className="icon-button table-more"
            aria-label="More table actions"
          >
            <MoreHorizontal size={18} />
          </button>
        </div>
      )}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>
                <label className="check-wrap">
                  <input type="checkbox" aria-label="Select all rows" />
                </label>
              </th>
              <th>{heading}</th>
              <th>Status</th>
              <th>Updated</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.slice(0, compact ? 3 : 8).map((row, index) => (
                <tr key={`${row.name}-${index}`}>
                  <td>
                    <label className="check-wrap">
                      <input
                        type="checkbox"
                        aria-label={`Select ${row.name}`}
                      />
                    </label>
                  </td>
                  <td>
                    <div className="person-cell">
                      <span
                        className={`avatar table-avatar avatar-${index % 4}`}
                      >
                        {row.initials}
                      </span>
                      <span>
                        <strong>{row.name}</strong>
                        <small>{row.detail}</small>
                      </span>
                    </div>
                  </td>
                  <td>
                    <StatusTag status={row.status} />
                  </td>
                  <td className="date-cell">{row.date}</td>
                  <td>
                    <button
                      className="icon-button row-more"
                      aria-label={`Actions for ${row.name}`}
                    >
                      <MoreHorizontal size={17} />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">
                    <ClipboardList size={22} />
                    <strong>No matching records</strong>
                    <span>Try a different search or filter.</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {!compact && (
        <div className="table-footer">
          <span>
            Showing {rows.length ? (page - 1) * 8 + 1 : 0}–
            {Math.min(page * 8, rows.length)} of {rows.length} records
          </span>
          <div>
            <button
              className="icon-button"
              aria-label="Previous page"
              disabled={page <= 1}
              onClick={() => setPage?.(Math.max(1, page - 1))}
            >
              <ChevronLeft size={16} />
            </button>
            <button className="page-number" aria-current="page">
              {page}
            </button>
            <button
              className="icon-button"
              aria-label="Next page"
              onClick={() => setPage?.(page + 1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusTag({ status }: { status: string }) {
  const className = /shortlisted|approved|healthy|interview/i.test(status)
    ? "status-green"
    : /review|queued|submitted|new/i.test(status)
      ? "status-amber"
      : /reject|closed|error/i.test(status)
        ? "status-red"
        : "status-gray";
  return (
    <span className={`status-tag ${className}`}>
      <i />
      {status}
    </span>
  );
}

function MatchingResults() {
  const [expanded, setExpanded] = useState<string | null>("cand-1048");
  const [jobs, setJobs] = useState<{ id: string; title: string; location?: string }[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [matches, setMatches] = useState<MatchResult[]>(mockPortalService.getMatches());
  const [loading, setLoading] = useState(false);
  const [matchingRunning, setMatchingRunning] = useState(false);
  const [showQuickModal, setShowQuickModal] = useState(false);
  const [quickTitle, setQuickTitle] = useState("");
  const [quickJD, setQuickJD] = useState("");
  const [quickLocation, setQuickLocation] = useState("Remote / Hybrid");

  // Load jobs from employerService
  useEffect(() => {
    let mounted = true;
    async function loadJobs() {
      try {
        const res = await employerService.getJobs();
        const items = res.data?.items || [];
        if (mounted && items.length > 0) {
          setJobs(items);
          setSelectedJobId(items[0].id);
        }
      } catch {
        // Fallback to default demo jobs if API is unavailable
      }
    }
    loadJobs();
    return () => {
      mounted = false;
    };
  }, []);

  // When selectedJobId changes, load top 5 matches
  useEffect(() => {
    if (!selectedJobId) return;
    let mounted = true;
    async function fetchMatches() {
      setLoading(true);
      try {
        const res = await matchingService.getResults(selectedJobId);
        const list = res.data?.items || (Array.isArray(res.data) ? res.data : []);
        if (mounted && list.length > 0) {
          setMatches(list);
          setExpanded(list[0].candidateId);
        }
      } catch (err) {
        console.warn("Could not fetch matches:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchMatches();
    return () => {
      mounted = false;
    };
  }, [selectedJobId]);

  const handleRunMatch = async () => {
    if (!selectedJobId) return;
    setMatchingRunning(true);
    try {
      const res = await matchingService.runMatch(selectedJobId, 5);
      const list = res.data?.items || (Array.isArray(res.data) ? res.data : []);
      if (list.length > 0) {
        setMatches(list);
        setExpanded(list[0].candidateId);
      }
    } catch (err) {
      console.error("Match run error:", err);
    } finally {
      setMatchingRunning(false);
    }
  };

  const handleQuickMatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle || !quickJD) return;
    setMatchingRunning(true);
    try {
      const res = await matchingService.quickMatch({
        title: quickTitle,
        description: quickJD,
        location: quickLocation,
        top_k: 5,
      });
      const list = res.data?.items || [];
      if (list.length > 0) {
        setMatches(list);
        setExpanded(list[0].candidateId);
      }
      if (res.data?.job_id) {
        setJobs((prev) => [
          { id: res.data.job_id, title: res.data.title, location: res.data.location },
          ...prev,
        ]);
        setSelectedJobId(res.data.job_id);
      }
      setShowQuickModal(false);
      setQuickTitle("");
      setQuickJD("");
    } catch (err) {
      console.error("Quick match error:", err);
    } finally {
      setMatchingRunning(false);
    }
  };

  const currentJob = jobs.find((j) => j.id === selectedJobId) || {
    id: "JOB-2048",
    title: "Senior Product Designer",
    location: "New York, NY",
  };

  return (
    <div className="matching-page">
      <div
        className="match-context panel"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
          <span className="job-context-icon">
            <BriefcaseBusiness size={18} />
          </span>
          <div>
            <span className="panel-kicker">AI MATCH RESULTS FOR ROLE</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.2rem" }}>
              {jobs.length > 0 ? (
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                  style={{
                    fontWeight: 700,
                    fontSize: "1.05rem",
                    padding: "0.25rem 0.5rem",
                    borderRadius: "6px",
                    border: "1px solid var(--border, #ccc)",
                    background: "var(--bg-surface, #fff)",
                    color: "inherit",
                    cursor: "pointer",
                  }}
                >
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} {j.location ? `· ${j.location}` : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <strong>{currentJob.title}</strong>
              )}
            </div>
            <span style={{ fontSize: "0.82rem", opacity: 0.8, display: "block", marginTop: "0.2rem" }}>
              {currentJob.location || "Remote"} · {currentJob.id} · AI semantic & requirement matching
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button
            className="button button-outline"
            onClick={handleRunMatch}
            disabled={matchingRunning || loading}
            title="Re-run AI evaluation and pull top 5 resumes"
          >
            <RefreshCw size={15} className={matchingRunning ? "spin" : ""} />
            {matchingRunning ? "Matching..." : "Re-run AI Match"}
          </button>
          <button
            className="button button-primary"
            onClick={() => setShowQuickModal(true)}
          >
            <Plus size={15} /> Paste New JD & Match
          </button>
        </div>
      </div>
      <div className="match-toolbar">
        <span>
          <strong>Top {matches.length}</strong> candidate resumes suited for this role (Ranked by AI match score)
        </span>
        <span className="match-guardrail">
          <CircleHelp size={15} /> Connected only candidate resumes that meet qualifications for this JD.
        </span>
      </div>

      {loading ? (
        <div className="panel" style={{ padding: "2.5rem", textAlign: "center", color: "var(--muted, #666)" }}>
          <p>Analyzing job description and extracting top 5 candidate resumes...</p>
        </div>
      ) : matches.length === 0 ? (
        <div className="panel" style={{ padding: "2.5rem", textAlign: "center" }}>
          <strong>No matching resumes found</strong>
          <p style={{ marginTop: "0.5rem", color: "var(--muted, #666)" }}>
            No candidate resumes met the required qualifications for this JD.
          </p>
        </div>
      ) : (
        matches.map((match, idx) => (
          <MatchCard
            key={match.candidateId || idx}
            match={match}
            rank={idx + 1}
            expanded={expanded === (match.candidateId || String(idx))}
            onToggle={() =>
              setExpanded(
                expanded === (match.candidateId || String(idx)) ? null : (match.candidateId || String(idx)),
              )
            }
          />
        ))
      )}

      {showQuickModal && (
        <div className="modal-backdrop" role="presentation" onClick={() => setShowQuickModal(false)}>
          <section
            className="modal panel"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "600px", width: "90%" }}
          >
            <div className="modal-heading">
              <div>
                <span className="panel-kicker">EMPLOYER JD ANALYSIS</span>
                <h2>Paste Job Description & Pull Top 5 Resumes</h2>
              </div>
              <button className="icon-button" onClick={() => setShowQuickModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleQuickMatch}>
              <label>
                Role Title
                <input
                  required
                  placeholder="e.g. Senior Python & AI Engineer"
                  value={quickTitle}
                  onChange={(e) => setQuickTitle(e.target.value)}
                />
              </label>
              <label>
                Location / Work Style
                <input
                  placeholder="e.g. Remote, Hybrid, or New York, NY"
                  value={quickLocation}
                  onChange={(e) => setQuickLocation(e.target.value)}
                />
              </label>
              <label>
                Job Description (JD)
                <textarea
                  required
                  rows={6}
                  placeholder="Paste the full job description, required qualifications, skills, and experience..."
                  value={quickJD}
                  onChange={(e) => setQuickJD(e.target.value)}
                />
              </label>
              <div className="modal-actions">
                <button
                  type="button"
                  className="button button-outline"
                  onClick={() => setShowQuickModal(false)}
                >
                  Cancel
                </button>
                <button
                  className="button button-primary"
                  type="submit"
                  disabled={matchingRunning}
                >
                  {matchingRunning ? "AI Reading & Matching..." : "Extract & Pull Top 5 Resumes"}
                  <ArrowRight size={15} />
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

function MatchCard({
  match,
  expanded,
  onToggle,
  rank,
}: {
  match: MatchResult;
  expanded: boolean;
  onToggle: () => void;
  rank?: number;
}) {
  return (
    <article className={`match-card panel ${expanded ? "match-expanded" : ""}`}>
      <div className="match-card-main">
        <span className="avatar avatar-xl avatar-blue" style={{ position: "relative" }}>
          {match.initials}
          {rank && (
            <span
              style={{
                position: "absolute",
                bottom: "-4px",
                right: "-4px",
                background: "var(--brand-primary, #2563eb)",
                color: "#fff",
                fontSize: "0.68rem",
                fontWeight: 700,
                borderRadius: "999px",
                padding: "1px 5px",
                lineHeight: "1.2",
              }}
            >
              #{rank}
            </span>
          )}
        </span>
        <div className="match-person">
          <div className="match-name-row">
            <h2>{match.name}</h2>
            <span className="confidence">
              <i />
              {match.confidence} confidence
            </span>
          </div>
          <p>{match.headline}</p>
          <span className="match-location">
            <MapPin size={13} />
            {match.location}
            <span>·</span>
            {match.resumeVersion}
          </span>
          <div className="skill-list">
            {match.skills.map((skill) => (
              <span className="skill-tag" key={skill}>
                {skill}
              </span>
            ))}
            {match.missingSkills.map((skill) => (
              <span className="skill-tag skill-missing" key={skill}>
                Missing · {skill}
              </span>
            ))}
          </div>
        </div>
        <div className="score-column">
          <span className="score-label">MATCH SCORE</span>
          <strong>
            {match.overallScore}
            <small>/100</small>
          </strong>
          <span className="score-note">{rank === 1 ? "Top Match" : "Suiting JD"}</span>
        </div>
        <button
          className="icon-button match-expand"
          aria-label={
            expanded ? "Collapse matching evidence" : "Expand matching evidence"
          }
          onClick={onToggle}
        >
          {expanded ? <X size={17} /> : <ArrowDownRight size={17} />}
        </button>
      </div>
      {expanded && (
        <div className="match-evidence">
          <div className="match-breakdown">
            <div className="evidence-title">
              <Sparkles size={15} />
              <strong>Match breakdown</strong>
              <span>Source: {match.jobReference}</span>
            </div>
            {match.dimensions.map((item) => (
              <div className="breakdown-row" key={item.label}>
                <span>{item.label}</span>
                <div className="breakdown-track">
                  <i style={{ width: `${item.score}%` }} />
                </div>
                <strong>{item.score}%</strong>
              </div>
            ))}
            <div className="completeness-row">
              <span>Information completeness</span>
              <strong>{match.completeness}%</strong>
              <span className="completeness-track">
                <i style={{ width: `${match.completeness}%` }} />
              </span>
            </div>
          </div>
          <div className="evidence-notes">
            <div className="evidence-title">
              <ShieldCheck size={15} />
              <strong>Evidence to inspect</strong>
            </div>
            {match.evidence.map((item) => (
              <p key={item}>
                <span>
                  <Check size={12} />
                </span>
                {item}
              </p>
            ))}
            <div className="evidence-actions">
              <button className="button button-outline">
                <Eye size={14} /> Full profile
              </button>
              <button className="button button-primary">
                <Check size={14} /> Shortlist
              </button>
              <button className="text-button">Pass</button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function JobDiscovery() {
  const [selectedJob, setSelectedJob] = useState<
    ReturnType<typeof mockPortalService.getJobs>[number] | null
  >(null);
  return (
    <>
      <div className="job-results">
        {mockPortalService.getJobs().map((job) => (
          <article className="job-card panel" key={job.title}>
            <span className="company-mark">{job.company.slice(0, 1)}</span>
            <div className="job-copy">
              <span className="panel-kicker">{job.company}</span>
              <h2>{job.title}</h2>
              <span className="job-location">
                <MapPin size={13} />
                {job.location}
              </span>
              <div className="skill-list">
                <span className="skill-tag">Design systems</span>
                <span className="skill-tag">Product strategy</span>
                <span className="skill-tag">+ 3 skills</span>
              </div>
            </div>
            <div className="job-action">
              <StatusTag status={`${job.applicants} applicants`} />
              <button
                className="button button-primary"
                onClick={() => setSelectedJob(job)}
              >
                View role <ArrowRight size={14} />
              </button>
            </div>
          </article>
        ))}
      </div>
      {selectedJob && (
        <JobDetailsModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </>
  );
}

function JobDetailsModal({
  job,
  onClose,
}: {
  job: ReturnType<typeof mockPortalService.getJobs>[number];
  onClose: () => void;
}) {
  const [consent, setConsent] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="modal panel job-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <span className="panel-kicker">
              {job.company} · {job.location}
            </span>
            <h2 id="job-detail-title">{job.title}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close job details"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        {submitted ? (
          <div className="success-state">
            <span>
              <Check size={20} />
            </span>
            <strong>Application preview submitted</strong>
            <p>
              This action is local to the demo. A live application requires
              backend confirmation and your approved resume.
            </p>
            <button className="button button-primary" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <>
            <p className="job-detail-copy">
              Northstar Labs is looking for a thoughtful product designer to
              help teams make complex workflows easier to understand and use.
              You will partner closely with product, engineering, and research.
            </p>
            <div className="job-detail-facts">
              <span>
                <MapPin size={14} />
                {job.location}
              </span>
              <span>
                <UsersRound size={14} />
                {job.applicants} applicants
              </span>
              <span>
                <BriefcaseBusiness size={14} />
                Full time
              </span>
            </div>
            <div className="job-detail-skills">
              <span className="panel-kicker">EXPERIENCE AREAS</span>
              <div className="skill-list">
                <span className="skill-tag">Product strategy</span>
                <span className="skill-tag">Figma</span>
                <span className="skill-tag">Design systems</span>
                <span className="skill-tag">User research</span>
              </div>
            </div>
            <label className="consent-checkbox job-consent">
              <input
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
              />{" "}
              I consent to share my approved profile and resume with this
              employer for this application.
            </label>
            <div className="modal-actions">
              <button className="button button-outline" onClick={onClose}>
                Close
              </button>
              <button
                className="button button-primary"
                disabled={!consent}
                onClick={() => setSubmitted(true)}
              >
                Apply now <ArrowRight size={15} />
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function WorkspaceSection({ role, section }: { role: Role; section: string }) {
  if (section === "profile" || section === "company" || section === "settings")
    return <ProfileWorkspace role={role} section={section} />;
  if (section === "resume")
    return (
      <>
        <ResumeWorkspace />
        <ExtractedReviewPanel />
      </>
    );
  if (section === "onboarding" && role === "candidate")
    return <CandidateOnboarding />;
  const cards =
    role === "admin"
      ? [
          {
            title: "Processing queue",
            value: "18",
            description: "Documents waiting for extraction",
            icon: FileText,
          },
          {
            title: "Model version",
            value: "v2.4.1",
            description: "Current model deployment",
            icon: Sparkles,
          },
          {
            title: "Audit events",
            value: "2,408",
            description: "Recorded in the last 30 days",
            icon: ClipboardList,
          },
        ]
      : [
          {
            title: "Upcoming",
            value: "6",
            description: "Scheduled across active roles",
            icon: CalendarDays,
          },
          {
            title: "In progress",
            value: "14",
            description: "Currently moving through review",
            icon: UsersRound,
          },
          {
            title: "Completed",
            value: "28",
            description: "Updated this month",
            icon: Check,
          },
        ];
  return (
    <>
      <div className="workspace-card-grid">
        {cards.map(({ title, value, description, icon: Icon }) => (
          <div className="workspace-card panel" key={title}>
            <span className="workspace-card-icon">
              <Icon size={18} />
            </span>
            <span className="panel-kicker">{title}</span>
            <strong>{value}</strong>
            <span>{description}</span>
          </div>
        ))}
      </div>
      <section className="panel settings-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">
              {role === "admin" ? "SYSTEM CONFIGURATION" : "WORKSPACE DETAILS"}
            </span>
            <h2>
              {navigation[role].find((item) => item.section === section)
                ?.label ?? "Workspace"}{" "}
              overview
            </h2>
          </div>
          <button className="button button-outline">
            Manage <ArrowRight size={14} />
          </button>
        </div>
        <div className="settings-row">
          <span className="settings-row-icon">
            <ShieldCheck size={17} />
          </span>
          <div>
            <strong>Role-based access</strong>
            <span>Access controls are enforced by the connected backend.</span>
          </div>
          <StatusTag status="Enabled" />
        </div>
        <div className="settings-row">
          <span className="settings-row-icon">
            <FileText size={17} />
          </span>
          <div>
            <strong>Activity and data</strong>
            <span>
              Changes and sensitive access should be recorded by the API.
            </span>
          </div>
          <button className="text-button">
            Review <ArrowRight size={13} />
          </button>
        </div>
        <div className="settings-row">
          <span className="settings-row-icon">
            <CircleHelp size={17} />
          </span>
          <div>
            <strong>Integration status</strong>
            <span>Demo mode is active until an API service is configured.</span>
          </div>
          <span className="status-tag status-amber">
            <i /> Demo mode
          </span>
        </div>
      </section>
    </>
  );
}

function CandidateOnboarding() {
  return (
    <div className="onboarding-layout">
      <section className="panel onboarding-progress">
        <span className="panel-kicker">YOUR STARTING POINT</span>
        <h2>Make room for the right opportunity.</h2>
        <p>
          A few thoughtful steps help employers understand your experience. You
          stay in control of what you share.
        </p>
        <div className="onboarding-meter">
          <span style={{ width: "50%" }} />
        </div>
        <div className="onboarding-count">
          <strong>2 of 4 steps complete</strong>
          <span>About 8 minutes left</span>
        </div>
      </section>
      <section className="panel onboarding-steps">
        <div className="onboarding-step done">
          <span>
            <Check size={14} />
          </span>
          <div>
            <strong>Create your account</strong>
            <small>Your candidate workspace is ready.</small>
          </div>
          <StatusTag status="Done" />
        </div>
        <div className="onboarding-step done">
          <span>
            <Check size={14} />
          </span>
          <div>
            <strong>Add your profile basics</strong>
            <small>Share your role, location, and preferences.</small>
          </div>
          <Link className="text-button" to="/portal/candidate/profile">
            Review <ArrowRight size={13} />
          </Link>
        </div>
        <div className="onboarding-step">
          <span>3</span>
          <div>
            <strong>Upload and review your resume</strong>
            <small>Confirm extracted information before it is added.</small>
          </div>
          <Link className="text-button" to="/portal/candidate/resume">
            Continue <ArrowRight size={13} />
          </Link>
        </div>
        <div className="onboarding-step">
          <span>4</span>
          <div>
            <strong>Choose your sharing consent</strong>
            <small>Only share your resume when you are ready.</small>
          </div>
          <Link className="text-button" to="/portal/candidate/resume">
            Review consent <ArrowRight size={13} />
          </Link>
        </div>
        <div className="onboarding-footer">
          <ShieldCheck size={15} />
          <span>
            Your profile is not visible to employers until you choose to apply
            and share.
          </span>
          <Link className="button button-primary" to="/portal/candidate/jobs">
            Explore jobs <ArrowRight size={14} />
          </Link>
        </div>
      </section>
    </div>
  );
}

function ProfileWorkspace({ role, section }: { role: Role; section: string }) {
  return (
    <div className="profile-layout">
      <section className="panel profile-card">
        <div className="profile-cover">
          <span className="profile-cover-mark">t</span>
        </div>
        <div className="profile-main">
          <span className="avatar avatar-xl avatar-coral">
            {role === "candidate" ? "AJ" : "MC"}
          </span>
          <div className="profile-title">
            <h2>{role === "candidate" ? "Amara Johnson" : "Northstar Labs"}</h2>
            <p>
              {role === "candidate"
                ? "Senior Product Designer · Brooklyn, NY"
                : "A product company making complex work feel simple."}
            </p>
          </div>
          <button className="button button-outline">
            Edit {section === "company" ? "company" : "profile"}
          </button>
        </div>
        <div className="profile-fields">
          <div>
            <span>EMAIL</span>
            <strong>
              {role === "candidate"
                ? "amara.johnson@email.com"
                : "talent@northstarlabs.com"}
            </strong>
          </div>
          <div>
            <span>{role === "candidate" ? "EXPERIENCE" : "TEAM SIZE"}</span>
            <strong>
              {role === "candidate" ? "7 years" : "201–500 people"}
            </strong>
          </div>
          <div>
            <span>{role === "candidate" ? "PREFERRED WORK" : "LOCATION"}</span>
            <strong>
              {role === "candidate" ? "Hybrid · Remote" : "New York, NY"}
            </strong>
          </div>
        </div>
      </section>
      <section className="panel completion-panel">
        <span className="panel-kicker">PROFILE STRENGTH</span>
        <div className="completion-score">
          82<span>%</span>
        </div>
        <div className="completion-track">
          <i style={{ width: "82%" }} />
        </div>
        <p>A few more details will help teams understand your experience.</p>
        <button className="panel-link">
          Complete your profile <ArrowRight size={14} />
        </button>
      </section>
      <section className="panel settings-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">YOUR INFORMATION</span>
            <h2>Skills & experience</h2>
          </div>
          <button className="button button-outline">
            <Plus size={14} /> Add details
          </button>
        </div>
        <div className="skill-list profile-skills">
          <span className="skill-tag">Product strategy</span>
          <span className="skill-tag">Figma</span>
          <span className="skill-tag">Design systems</span>
          <span className="skill-tag">User research</span>
          <span className="skill-tag">Prototyping</span>
        </div>
        <div className="settings-row">
          <span className="settings-row-icon">
            <BriefcaseBusiness size={17} />
          </span>
          <div>
            <strong>Senior Product Designer</strong>
            <span>Fieldwork · 2022 – Present</span>
          </div>
          <button className="icon-button">
            <MoreHorizontal size={17} />
          </button>
        </div>
        <div className="settings-row">
          <span className="settings-row-icon">
            <BriefcaseBusiness size={17} />
          </span>
          <div>
            <strong>Product Designer</strong>
            <span>Goodkind Studio · 2019 – 2022</span>
          </div>
          <button className="icon-button">
            <MoreHorizontal size={17} />
          </button>
        </div>
      </section>
    </div>
  );
}

function ResumeWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const [aiConsent, setAiConsent] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [extractedData, setExtractedData] = useState<any>(null);
  const [reviewed, setReviewed] = useState(false);
  const [sharingConsent, setSharingConsent] = useState(true);
  const [savingReview, setSavingReview] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [hasToken, setHasToken] = useState<boolean>(() => Boolean(tokenStore.get()));
  const [candName, setCandName] = useState("Suriyaprakash");
  const [candEmail, setCandEmail] = useState("suriyaprakash@example.com");
  const [candPass, setCandPass] = useState("Password123456!");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setIsSaved(false);
      setErrorMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setStatus("uploading");
    setErrorMsg(null);
    try {
      // Ensure candidate authentication token is present
      if (!tokenStore.get()) {
        try {
          await authService.register({
            display_name: candName.trim() || candEmail.split("@")[0],
            email: candEmail.trim().toLowerCase(),
            password: candPass,
          });
        } catch (regErr: any) {
          if (regErr.response?.status === 409) {
            await authService.login({
              email: candEmail.trim().toLowerCase(),
              password: candPass,
            });
          } else {
            throw regErr;
          }
        }
        setHasToken(true);
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("consent_to_ai_processing", String(aiConsent));

      const res = await candidateService.uploadResume(formData);
      const newVersionId = res.data.resume_version_id;
      setVersionId(newVersionId);
      setStatus("processing");

      // Poll or fetch extraction
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const extRes = await candidateService.getExtracted(newVersionId);
          if (extRes.data && (extRes.data.skills?.length > 0 || extRes.data.headline || attempts >= 4)) {
            setExtractedData(extRes.data);
            setStatus("complete");
            clearInterval(poll);
          }
        } catch {
          if (attempts >= 8) {
            clearInterval(poll);
            setStatus("complete");
          }
        }
      }, 1500);
    } catch (err: any) {
      console.error("Resume upload error:", err);
      setErrorMsg(err.response?.data?.detail || "Failed to upload resume. Please verify candidate email/password.");
      setStatus("error");
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmReview = async () => {
    if (!versionId || !extractedData) return;
    setSavingReview(true);
    try {
      await candidateService.reviewExtracted(versionId, {
        confirmed: true,
        extraction: extractedData,
      });
      if (sharingConsent) {
        await candidateService.updateSharingConsent(versionId, { consent: true });
      }
      setIsSaved(true);
    } catch (err: any) {
      console.error("Save review error:", err);
      setErrorMsg(err.response?.data?.detail || "Failed to save verified extraction.");
    } finally {
      setSavingReview(false);
    }
  };

  return (
    <div className="resume-layout">
      <section className="panel upload-panel">
        <div className="upload-icon">
          <FileText size={22} />
        </div>
        <span className="panel-kicker">CANDIDATE PORTAL · RESUME UPLOAD</span>
        <h2>{versionId ? "Resume Uploaded" : "Upload Your Resume to SQLite Database"}</h2>
        <p>
          Upload your PDF, DOCX, or TXT file. The AI extracts your skills and qualifications so employers can match your resume against their job descriptions.
        </p>

        <div style={{ margin: "1rem 0" }}>
          <label className="button button-primary upload-button" style={{ cursor: "pointer", display: "inline-flex" }}>
            <Plus size={15} /> {file ? file.name : "Choose Resume File (PDF / DOCX / TXT)"}
            <input
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
          </label>
        </div>

        {!hasToken && (
          <div style={{ margin: "1rem 0", padding: "0.85rem", background: "rgba(255,255,255,0.04)", borderRadius: "8px", border: "1px solid var(--border, #444)" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.05em", color: "#38bdf8", textTransform: "uppercase" }}>Candidate Details (Stored in SQLite)</span>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginTop: "0.5rem" }}>
              <input
                type="text"
                placeholder="Full Name (e.g. Suriyaprakash)"
                value={candName}
                onChange={(e) => setCandName(e.target.value)}
                style={{ padding: "0.4rem 0.6rem", borderRadius: "4px", fontSize: "0.88rem" }}
              />
              <input
                type="email"
                placeholder="Candidate Email"
                value={candEmail}
                onChange={(e) => setCandEmail(e.target.value)}
                style={{ padding: "0.4rem 0.6rem", borderRadius: "4px", fontSize: "0.88rem" }}
              />
            </div>
            <input
              type="password"
              placeholder="Candidate Password (min 12 chars)"
              value={candPass}
              onChange={(e) => setCandPass(e.target.value)}
              style={{ width: "100%", padding: "0.4rem 0.6rem", borderRadius: "4px", fontSize: "0.88rem", marginTop: "0.5rem" }}
            />
          </div>
        )}

        {file && (
          <div style={{ marginTop: "0.5rem", marginBottom: "1rem" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontSize: "0.9rem" }}>
              <input
                type="checkbox"
                checked={aiConsent}
                onChange={(e) => setAiConsent(e.target.checked)}
              />
              <span>Consent to AI parsing and qualification extraction</span>
            </label>
          </div>
        )}

        {file && !versionId && (
          <button
            className="button button-primary"
            onClick={handleUpload}
            disabled={uploading || !aiConsent}
            style={{ width: "100%", marginTop: "0.5rem" }}
          >
            {uploading ? "Uploading & Processing via AI..." : "Upload & Store in Database"}
          </button>
        )}

        {errorMsg && (
          <div style={{ color: "var(--danger, #e53e3e)", fontSize: "0.88rem", marginTop: "0.75rem" }}>
            {errorMsg}
          </div>
        )}

        <span className="upload-consent" style={{ marginTop: "1rem", display: "block" }}>
          <ShieldCheck size={14} /> Candidates retain full control. Resumes are only shared with employer matching after review.
        </span>
      </section>

      <section className="panel process-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">DATABASE & EXTRACTION STATUS</span>
            <h2>SQLite Processing Pipeline</h2>
          </div>
          <StatusTag status={status === "complete" ? "Complete" : status === "processing" ? "Processing" : status === "uploading" ? "Uploading" : "Ready"} />
        </div>
        <div className="process-steps">
          <div className={`process-step ${versionId ? "done" : "active"}`}>
            <span>{versionId ? <Check size={13} /> : "1"}</span>
            <div>
              <strong>1. Store in SQLite & Storage</strong>
              <small>{versionId ? `Stored (Version ID: ${versionId.slice(0, 8)}...)` : "Awaiting file selection"}</small>
            </div>
          </div>
          <div className={`process-step ${extractedData ? "done" : status === "processing" ? "active" : ""}`}>
            <span>{extractedData ? <Check size={13} /> : "2"}</span>
            <div>
              <strong>2. Hugging Face AI Extraction</strong>
              <small>{extractedData ? "Extracted skills, role & work history" : status === "processing" ? "Running AI model..." : "Pending upload"}</small>
            </div>
          </div>
          <div className={`process-step ${isSaved ? "done" : extractedData ? "active" : ""}`}>
            <span>{isSaved ? <Check size={13} /> : "3"}</span>
            <div>
              <strong>3. Candidate Review & Sharing Consent</strong>
              <small>{isSaved ? "Verified & Granted Recruiter Search" : "Pending candidate confirmation"}</small>
            </div>
          </div>
          <div className={`process-step ${isSaved ? "done" : ""}`}>
            <span>{isSaved ? <Check size={13} /> : "4"}</span>
            <div>
              <strong>4. Indexed for Employer Top 5 Matching</strong>
              <small>{isSaved ? "Active in SQLite candidate search index" : "Requires confirmed review"}</small>
            </div>
          </div>
        </div>
      </section>

      {extractedData && (
        <section className="panel extracted-review" style={{ gridColumn: "1 / -1" }}>
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">EXTRACTED QUALIFICATIONS FROM RESUME</span>
              <h2>Review Your Profile Before Employer Matching</h2>
            </div>
            <StatusTag status={isSaved ? "Confirmed" : "Review required"} />
          </div>

          <div className="extracted-fields" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1rem" }}>
            <label>
              Headline / Role
              <input
                value={extractedData.headline || ""}
                onChange={(e) => setExtractedData({ ...extractedData, headline: e.target.value })}
              />
            </label>
            <label>
              Location
              <input
                value={extractedData.location || "Remote"}
                onChange={(e) => setExtractedData({ ...extractedData, location: e.target.value })}
              />
            </label>
          </div>

          <div style={{ marginTop: "1rem" }}>
            <span className="panel-kicker">EXTRACTED SKILLS ({extractedData.skills?.length || 0})</span>
            <div className="skill-list" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem" }}>
              {extractedData.skills && extractedData.skills.length > 0 ? (
                extractedData.skills.map((s: any, idx: number) => (
                  <span className="skill-tag" key={idx} style={{ padding: "0.3rem 0.6rem", borderRadius: "4px" }}>
                    {typeof s === "string" ? s : s.name}
                  </span>
                ))
              ) : (
                <span>No specific skills detected in text</span>
              )}
            </div>
          </div>

          {extractedData.summary && (
            <div style={{ marginTop: "1rem" }}>
              <span className="panel-kicker">SUMMARY</span>
              <p style={{ fontSize: "0.92rem", opacity: 0.9, marginTop: "0.25rem" }}>{extractedData.summary}</p>
            </div>
          )}

          <div style={{ margin: "1.5rem 0", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <label className="review-check" style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
              />
              <span>I reviewed these extracted details and confirm they are accurate.</span>
            </label>
            <label className="review-check" style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={sharingConsent}
                onChange={(e) => setSharingConsent(e.target.checked)}
              />
              <span>I grant active recruiter search consent so employers can find my resume when matching for jobs.</span>
            </label>
          </div>

          <div className="extracted-footer" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <span>
              <ShieldCheck size={14} /> You can update or revoke recruiter search consent at any time.
            </span>
            <button
              className="button button-primary"
              disabled={!reviewed || !sharingConsent || savingReview || isSaved}
              onClick={handleConfirmReview}
            >
              {isSaved ? (
                <>
                  <Check size={14} /> Saved in Database (Ready for Matching!)
                </>
              ) : savingReview ? (
                "Saving..."
              ) : (
                <>
                  Confirm & Save to Candidate Database <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>

          {isSaved && (
            <div style={{ marginTop: "1rem", padding: "1rem", background: "rgba(34, 197, 94, 0.1)", border: "1px solid rgba(34, 197, 94, 0.3)", borderRadius: "6px", color: "var(--text, #fff)" }}>
              <strong>Success!</strong> Your resume has been parsed by AI, verified, and stored in the SQLite database. When any employer posts a matching Job Description, your profile will be evaluated and recommended among the top 5!
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ExtractedReviewPanel() {
  return null;
}

function JobModal({ onClose }: { onClose: () => void }) {
  const [saved, setSaved] = useState(false);
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="modal panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <span className="panel-kicker">NEW OPENING</span>
            <h2 id="job-modal-title">Create a job</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        {saved ? (
          <div className="success-state">
            <span>
              <Check size={20} />
            </span>
            <strong>Job draft saved</strong>
            <p>
              The draft is local to this demo. Connect the API to publish it.
            </p>
            <button className="button button-primary" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setSaved(true);
            }}
          >
            <label>
              Job title
              <input required placeholder="e.g. Senior Product Designer" />
            </label>
            <div className="form-row">
              <label>
                Location
                <input required placeholder="New York, NY" />
              </label>
              <label>
                Work style
                <select defaultValue="Hybrid">
                  <option>Hybrid</option>
                  <option>Remote</option>
                  <option>On-site</option>
                </select>
              </label>
            </div>
            <label>
              Job description
              <textarea
                required
                rows={5}
                placeholder="Describe the role, outcomes, and experience needed..."
              />
            </label>
            <label className="consent-checkbox">
              <input type="checkbox" /> I have permission to publish this role
              for my organization.
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="button button-outline"
                onClick={onClose}
              >
                Cancel
              </button>
              <button className="button button-primary" type="submit">
                Save draft <ArrowRight size={15} />
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}

function ChevronDownIcon() {
  return <ChevronRight className="chevron-down" size={14} />;
}
