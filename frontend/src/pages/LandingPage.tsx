import {
  ArrowDownRight,
  ArrowRight,
  BriefcaseBusiness,
  Check,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSessionStore } from "../store/session";
import type { Role } from "../types";

const portals: {
  role: Role;
  title: string;
  detail: string;
  icon: typeof UsersRound;
  tone: string;
}[] = [
  {
    role: "candidate",
    title: "Candidate",
    detail: "Build your profile and find work that fits.",
    icon: UsersRound,
    tone: "mint",
  },
  {
    role: "recruiter",
    title: "Recruiter",
    detail: "Meet the people behind stronger teams.",
    icon: BriefcaseBusiness,
    tone: "peach",
  },
  {
    role: "admin",
    title: "Platform admin",
    detail: "Keep the marketplace healthy and fair.",
    icon: ShieldCheck,
    tone: "blue",
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const signIn = useSessionStore((state) => state.signIn);

  const previewPortal = (role: Role) => {
    signIn(role);
    navigate(`/portal/${role}/overview`);
  };

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <a className="brand-lockup" href="/">
          <span className="brand-mark">t</span>
          <span>
            tandem<span className="brand-period">.</span>
          </span>
        </a>
        <span className="landing-nav-label">
          AI recruitment, built around people
        </span>
        <button
          className="button button-quiet"
          onClick={() => navigate("/login/candidate")}
        >
          Sign in <ArrowRight size={15} />
        </button>
      </header>
      <main>
        <section className="landing-hero">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="eyebrow-dot" /> A clearer way to find your next
            </span>
            <h1>
              Good work starts
              <br />
              with <em>good people.</em>
            </h1>
            <p className="hero-description">
              A more considered way to bring talent and opportunity together.
              Less noise in the process, more room for the right conversations.
            </p>
            <div className="hero-actions">
              <button
                className="button button-primary"
                onClick={() => navigate("/login/candidate")}
              >
                Get started <ArrowRight size={16} />
              </button>
              <a className="text-link" href="#portals">
                Explore the platform <ArrowDownRight size={15} />
              </a>
            </div>
            <div className="hero-proof">
              <div className="proof-avatars">
                <span>AJ</span>
                <span>TW</span>
                <span>PS</span>
                <b>+</b>
              </div>
              <span>Made for people, not just profiles</span>
            </div>
          </div>
          <div
            className="hero-visual"
            aria-label="Recruitment workspace preview"
          >
            <div className="visual-topline">
              <span>
                <i /> YOUR NEXT CHAPTER
              </span>
              <span>01 — 03</span>
            </div>
            <div className="visual-heading">
              <span>
                Better matches.
                <br />
                <strong>More human hiring.</strong>
              </span>
              <span className="visual-spark">
                <Sparkles size={19} />
              </span>
            </div>
            <div className="visual-match">
              <div className="visual-match-top">
                <div className="avatar avatar-xl avatar-blue">AJ</div>
                <div>
                  <strong>Amara Johnson</strong>
                  <span>Product designer · Brooklyn, NY</span>
                </div>
                <span className="match-score">
                  92<small> match</small>
                </span>
              </div>
              <div className="visual-meter">
                <span style={{ width: "92%" }} />
              </div>
              <div className="visual-tags">
                <span>Product strategy</span>
                <span>Design systems</span>
                <span>User research</span>
              </div>
              <div className="visual-evidence">
                <span className="evidence-check">
                  <Check size={12} />
                </span>
                <span>7 years experience across product teams</span>
                <span>
                  See evidence <ArrowRight size={12} />
                </span>
              </div>
            </div>
            <div className="visual-note">
              <span>
                Thoughtful matches,
                <br />
                <b>transparent by design.</b>
              </span>
              <span className="note-mark">✳</span>
            </div>
            <div className="visual-stamp">
              BUILT
              <br />
              FOR PEOPLE
            </div>
          </div>
        </section>
        <section id="portals" className="portal-chooser">
          <div className="section-heading">
            <div>
              <span className="eyebrow">ONE PLATFORM, THREE PERSPECTIVES</span>
              <h2>Choose your workspace</h2>
            </div>
            <span className="section-side-note">
              Preview the product experience
            </span>
          </div>
          <div className="portal-grid">
            {portals.map(({ role, title, detail, icon: Icon, tone }) => (
              <button
                className="portal-card"
                key={role}
                onClick={() => previewPortal(role)}
              >
                <span className={`portal-icon ${tone}`}>
                  <Icon size={19} />
                </span>
                <span className="portal-card-copy">
                  <strong>{title}</strong>
                  <span>{detail}</span>
                </span>
                <span className="portal-arrow">
                  <ArrowRight size={17} />
                </span>
              </button>
            ))}
          </div>
          <p className="landing-disclaimer">
            Demo workspace access is for interface preview only. Authentication
            and live data require a connected backend.
          </p>
        </section>
      </main>
      <footer className="landing-footer">
        <span>
          tandem<span className="brand-period">.</span>
        </span>
        <span>Thoughtful technology for better work.</span>
        <span>© 2025 Tandem</span>
      </footer>
    </div>
  );
}
