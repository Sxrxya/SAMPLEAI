import {
  Activity,
  Bell,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  ChartNoAxesCombined,
  CircleCheck,
  ChevronDown,
  Database,
  FileText,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Timer,
  UserRound,
  UsersRound,
  Eye,
} from "lucide-react";
import { useState } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useNavigate,
  useParams,
} from "react-router-dom";
import { usesDemoData } from "../services/apiClient";
import { useSessionStore } from "../store/session";
import { navigation, roleLabels, type Role } from "../types";

const icons = {
  activity: Activity,
  bell: Bell,
  briefcase: BriefcaseBusiness,
  building: Building2,
  calendar: CalendarDays,
  chart: ChartNoAxesCombined,
  check: CircleCheck,
  database: Database,
  file: FileText,
  key: KeyRound,
  layout: LayoutDashboard,
  list: ListChecks,
  settings: Settings,
  shield: ShieldCheck,
  sliders: SlidersHorizontal,
  sparkles: Sparkles,
  timer: Timer,
  user: UserRound,
  users: UsersRound,
  eye: Eye,
};

export function PortalLayout() {
  const { role: roleParam, section = "overview" } = useParams();
  const navigate = useNavigate();
  const activeRole = roleParam as Role;
  const signOut = useSessionStore((state) => state.signOut);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [noticeOpen, setNoticeOpen] = useState(false);

  const changeRole = (role: Role) => {
    navigate(`/login/${role}`);
    setSidebarOpen(false);
  };

  const logout = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <Link className="brand-lockup" to="/">
          <span className="brand-mark">t</span>
          <span>
            tandem<span className="brand-period">.</span>
          </span>
        </Link>
        <button
          className="workspace-switcher"
          onClick={() =>
            changeRole(
              activeRole === "candidate"
                ? "recruiter"
                : activeRole === "recruiter"
                  ? "admin"
                  : "candidate",
            )
          }
        >
          <span className="workspace-avatar">
            {activeRole === "candidate"
              ? "AJ"
              : activeRole === "recruiter"
                ? "N"
                : "S"}
          </span>
          <span className="workspace-meta">
            <strong>
              {activeRole === "candidate"
                ? "Amara Johnson"
                : activeRole === "recruiter"
                  ? "Northstar Labs"
                  : "Platform ops"}
            </strong>
            <small>{roleLabels[activeRole]} workspace</small>
          </span>
          <ChevronDown size={15} />
        </button>
        <div className="nav-caption">WORKSPACE</div>
        <nav
          className="side-nav"
          aria-label={`${roleLabels[activeRole]} navigation`}
        >
          {navigation[activeRole].map((item) => {
            const Icon =
              icons[item.icon as keyof typeof icons] ?? LayoutDashboard;
            return (
              <NavLink
                key={item.section}
                to={`/portal/${activeRole}/${item.section}`}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `nav-link ${isActive || (section === "overview" && item.section === "overview") ? "nav-active" : ""}`
                }
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>{item.label}</span>
                {item.section === "applicants" && (
                  <span className="nav-count">8</span>
                )}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="support-note">
            <span className="support-dot" />
            <div>
              <strong>All systems operational</strong>
              <small>Last checked just now</small>
            </div>
          </div>
          <button className="nav-link signout-link" onClick={logout}>
            <LogOut size={17} />
            <span>Sign out</span>
          </button>
          <div className="user-mini">
            <span className="avatar avatar-green">
              {activeRole === "candidate"
                ? "AJ"
                : activeRole === "recruiter"
                  ? "MC"
                  : "SO"}
            </span>
            <div>
              <strong>
                {activeRole === "candidate"
                  ? "Amara Johnson"
                  : activeRole === "recruiter"
                    ? "Maya Chen"
                    : "Sam Ortega"}
              </strong>
              <small>
                {activeRole === "candidate"
                  ? "Candidate account"
                  : activeRole === "recruiter"
                    ? "Talent partner"
                    : "Platform admin"}
              </small>
            </div>
            <button
              className="icon-button tiny"
              aria-label="Account settings"
              onClick={() => navigate(`/portal/${activeRole}/settings`)}
            >
              <Settings size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={19} />
          </button>
          <div className="breadcrumbs">
            <span>{roleLabels[activeRole]} portal</span>
            <span className="crumb-divider">/</span>
            <strong>
              {navigation[activeRole].find((item) => item.section === section)
                ?.label ?? "Overview"}
            </strong>
          </div>
          <div className="topbar-actions">
            <label className="top-search">
              <Search size={16} />
              <input
                placeholder="Search anything..."
                aria-label="Search anything"
              />
              <kbd>⌘ K</kbd>
            </label>
            <div className="notice-wrap">
              <button
                className="icon-button notice-button"
                aria-label="Notifications"
                onClick={() => setNoticeOpen((open) => !open)}
              >
                <Bell size={18} />
                <i />
              </button>
              {noticeOpen && (
                <div className="notice-popover">
                  <strong>You're all caught up</strong>
                  <p>New updates will show here.</p>
                </div>
              )}
            </div>
            <span className="topbar-divider" />
            <div className="top-user">
              <span className="avatar avatar-coral">
                {activeRole === "candidate"
                  ? "AJ"
                  : activeRole === "recruiter"
                    ? "MC"
                    : "SO"}
              </span>
              <span>
                {activeRole === "candidate"
                  ? "Amara"
                  : activeRole === "recruiter"
                    ? "Maya Chen"
                    : "Sam Ortega"}
              </span>
              <ChevronDown size={14} />
            </div>
          </div>
        </header>
        {usesDemoData && (
          <div className="demo-strip">
            <Sparkles size={14} />
            <span>DEMO ENVIRONMENT</span>
            <span className="demo-strip-copy">
              Sample records are shown for UI preview. Connect your FastAPI
              service to use live data.
            </span>
          </div>
        )}
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
