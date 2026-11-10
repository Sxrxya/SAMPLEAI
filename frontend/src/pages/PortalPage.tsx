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
} from "lucide-react";
import { useMemo, useState } from "react";
import { lazy, Suspense } from "react";
import { Link, useParams } from "react-router-dom";
import { usesDemoData } from "../services/apiClient";
import { mockPortalService } from "../services/mockPortalService";
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

  if (!usesDemoData) return <LiveEmptyPage role={role} title={heading} />;
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

function LiveEmptyPage({ role, title }: { role: Role; title: string }) {
  return (
    <>
      <PageHeader
        eyebrow={`${roleLabels[role]} workspace`}
        title={title}
        description="This view is ready for FastAPI data."
      />
      <section className="panel live-empty">
        <span className="live-empty-icon">
          <CircleHelp size={20} />
        </span>
        <strong>Live API not connected</strong>
        <p>
          No backend endpoint has been verified or configured. Review the
          proposed routes in API_CONTRACT.md before enabling live services.
        </p>
        <span>Sample data is intentionally hidden while demo mode is off.</span>
      </section>
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
  const matches = mockPortalService.getMatches();
  return (
    <div className="matching-page">
      <div className="match-context panel">
        <span className="job-context-icon">
          <BriefcaseBusiness size={18} />
        </span>
        <div>
          <span className="panel-kicker">MATCH RESULTS FOR</span>
          <strong>Senior Product Designer</strong>
          <span>Northstar Labs · JOB-2048 · Updated 2 hours ago</span>
        </div>
        <button className="button button-outline">
          <Filter size={15} /> Refine list
        </button>
      </div>
      <div className="match-toolbar">
        <span>
          <strong>{matches.length}</strong> candidates ranked by backend match
          score
        </span>
        <span className="match-guardrail">
          <CircleHelp size={15} /> Scores are evidence, not hiring
          probabilities.
        </span>
      </div>
      {matches.map((match) => (
        <MatchCard
          key={match.candidateId}
          match={match}
          expanded={expanded === match.candidateId}
          onToggle={() =>
            setExpanded(
              expanded === match.candidateId ? null : match.candidateId,
            )
          }
        />
      ))}
    </div>
  );
}

function MatchCard({
  match,
  expanded,
  onToggle,
}: {
  match: MatchResult;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <article className={`match-card panel ${expanded ? "match-expanded" : ""}`}>
      <div className="match-card-main">
        <span className="avatar avatar-xl avatar-blue">{match.initials}</span>
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
          <span className="score-note">Demo response</span>
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
  const [uploaded, setUploaded] = useState(false);
  return (
    <div className="resume-layout">
      <section className="panel upload-panel">
        <div className="upload-icon">
          <FileText size={22} />
        </div>
        <span className="panel-kicker">RESUME DOCUMENT</span>
        <h2>{uploaded ? "Resume uploaded" : "Add your latest resume"}</h2>
        <p>
          PDF or DOCX · up to 10 MB. Your file stays private until you choose to
          share it.
        </p>
        <label className="button button-primary upload-button">
          <Plus size={15} /> Choose a file
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={() => setUploaded(true)}
          />
        </label>
        <span className="upload-consent">
          <ShieldCheck size={14} /> Only you control who can view your resume.
        </span>
      </section>
      <section className="panel process-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">AI EXTRACTION</span>
            <h2>Processing status</h2>
          </div>
          <StatusTag status={uploaded ? "Queued" : "Complete"} />
        </div>
        <div className="process-steps">
          <div className="process-step done">
            <span>
              <Check size={13} />
            </span>
            <div>
              <strong>Document received</strong>
              <small>Resume v3 · Oct 18, 2025</small>
            </div>
          </div>
          <div className={`process-step ${uploaded ? "active" : "done"}`}>
            <span>{uploaded ? "2" : <Check size={13} />}</span>
            <div>
              <strong>Extract information</strong>
              <small>
                {uploaded
                  ? "Waiting for processing service"
                  : "Completed in 14 seconds"}
              </small>
            </div>
          </div>
          <div className="process-step">
            <span>3</span>
            <div>
              <strong>Review extracted details</strong>
              <small>Confirm before adding to your profile</small>
            </div>
          </div>
          <div className="process-step">
            <span>4</span>
            <div>
              <strong>Set sharing consent</strong>
              <small>Choose visibility before applying</small>
            </div>
          </div>
        </div>
        <button
          className="button button-outline process-review"
          disabled={uploaded}
        >
          Review extracted information <ArrowRight size={14} />
        </button>
      </section>
      <section className="panel consent-panel">
        <span className="consent-icon">
          <ShieldCheck size={18} />
        </span>
        <div>
          <strong>Your consent, always</strong>
          <p>
            Extracted details do not become visible to employers until you
            review them and choose to share.
          </p>
        </div>
        <button className="text-button">
          Privacy settings <ArrowRight size={13} />
        </button>
      </section>
    </div>
  );
}

function ExtractedReviewPanel() {
  const [reviewed, setReviewed] = useState(false);
  const [consent, setConsent] = useState(false);
  const [saved, setSaved] = useState(false);
  return (
    <section className="panel extracted-review">
      <div className="panel-heading">
        <div>
          <span className="panel-kicker">
            EXTRACTED INFORMATION · DEMO PREVIEW
          </span>
          <h2>Review before adding to your profile</h2>
        </div>
        <StatusTag status="Review required" />
      </div>
      <p className="extracted-intro">
        These example fields illustrate the review step. In production, this
        panel must show only the parsing result returned for your resume.
      </p>
      <div className="extracted-fields">
        <label>
          Full name
          <input defaultValue="Amara Johnson" />
        </label>
        <label>
          Current role
          <input defaultValue="Senior Product Designer" />
        </label>
        <label>
          Experience
          <input defaultValue="7 years" />
        </label>
        <label>
          Location
          <input defaultValue="Brooklyn, NY" />
        </label>
      </div>
      <div className="skill-list">
        <span className="skill-tag">Product strategy</span>
        <span className="skill-tag">Figma</span>
        <span className="skill-tag">Design systems</span>
        <button className="text-button">+ Add skill</button>
      </div>
      <label className="review-check">
        <input
          type="checkbox"
          checked={reviewed}
          onChange={(event) => setReviewed(event.target.checked)}
        />{" "}
        I reviewed these extracted details and confirm they are accurate.
      </label>
      <label className="review-check">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
        />{" "}
        I consent to include this approved information when I apply to jobs.
      </label>
      <div className="extracted-footer">
        <span>
          <ShieldCheck size={14} /> You can change or revoke sharing consent
          later.
        </span>
        <button
          className="button button-primary"
          disabled={!reviewed || !consent}
          onClick={() => setSaved(true)}
        >
          {saved ? (
            <>
              <Check size={14} /> Saved in demo
            </>
          ) : (
            <>
              Confirm review <ArrowRight size={14} />
            </>
          )}
        </button>
      </div>
    </section>
  );
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
