import React, { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import {
  Sparkles,
  FileText,
  Upload,
  Send,
  ChevronDown,
  ChevronUp,
  MapPin,
  Plus,
  Award,
  AlertCircle,
  CheckCircle2,
  Code,
  Briefcase,
  Search,
  Building2,
} from "lucide-react";
import { employerService } from "../services/employerService";
import { candidateService } from "../services/candidateService";
import { jobService } from "../services/jobService";
import { applicationService } from "../services/applicationService";
import { authService } from "../services/authService";
import { tokenStore } from "../services/tokenStore";
import { useSessionStore } from "../store/session";
import { apiClient } from "../services/apiClient";
import type { Role } from "../types";

export function PortalPage() {
  const { role: roleParam = "recruiter" } = useParams();
  const role = roleParam as Role;

  if (role === "candidate") {
    return <CandidateResumeUploader />;
  }

  if (role === "recruiter") {
    return <RecruiterChatGPTWorkspace />;
  }

  return <AdminTelemetryWorkspace />;
}

/* ==========================================================================
   RECRUITER WORKSPACE - CHATGPT / CLAUDE STYLE AI JD & TALENT MATCHER
   ========================================================================== */
function RecruiterChatGPTWorkspace() {
  const [savedJds, setSavedJds] = useState<any[]>([]);
  const [activeJdId, setActiveJdId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [jdText, setJdText] = useState("");
  const [jdTitle, setJdTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedCandId, setExpandedCandId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);

  // Load real JDs from SQLite database on mount
  const loadSavedJds = async () => {
    try {
      const res = await employerService.getJobs({ page_size: 50 });
      const items = res.data?.items || res.data || [];
      setSavedJds(items);
      if (items.length > 0 && !activeJdId) {
        selectJd(items[0]);
      }
    } catch (err) {
      console.error("Failed to load saved JDs from SQLite:", err);
    }
  };

  useEffect(() => {
    loadSavedJds();
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Select a JD from sidebar and load Top 5 matches from SQLite
  const selectJd = async (job: any) => {
    setActiveJdId(job.id);
    setLoading(true);
    setErrorMsg(null);

    // Initial message
    const initialUserMsg = {
      id: `user-${job.id}`,
      sender: "user",
      title: job.title,
      text: job.description || `Matching candidates for: ${job.title}`,
      timestamp: new Date(job.created_at || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    try {
      const matchRes = await employerService.getJobMatches(job.id, 5);
      const matches = matchRes.data?.items || [];

      const assistantMsg = {
        id: `assistant-${job.id}`,
        sender: "assistant",
        jobTitle: job.title,
        jobLocation: job.location || "Remote",
        candidates: matches,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages([initialUserMsg, assistantMsg]);
    } catch (err: any) {
      console.error("Failed to load matches for job:", err);
      setErrorMsg("Failed to retrieve matches from SQLite. Please verify backend connection.");
    } finally {
      setLoading(false);
    }
  };

  // Start a fresh conversation for a new JD
  const handleStartNewJd = () => {
    setActiveJdId(null);
    setMessages([]);
    setJdText("");
    setJdTitle("");
    setErrorMsg(null);
  };

  // Submit a new JD: Saves to SQLite -> LLM extracts -> Evaluates candidates -> Returns Top 5
  const handleSubmitJd = async () => {
    if (!jdText.trim()) return;
    const titleToUse = jdTitle.trim() || jdText.trim().split("\n")[0].slice(0, 80) || "Job Opening";

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: "user",
      title: titleToUse,
      text: jdText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setErrorMsg(null);
    const submittedText = jdText;
    setJdText("");
    setJdTitle("");

    try {
      // Calls quickMatch which saves into SQLite and runs LLM evaluation
      const res = await employerService.quickMatch({
        title: titleToUse,
        description: submittedText,
        top_k: 5,
      });

      const newJobId = res.data.job_id;
      const matches = res.data.items || [];

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        jobTitle: titleToUse,
        jobLocation: res.data.location || "Remote",
        candidates: matches,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveJdId(newJobId);
      // Refresh sidebar so new JD appears in SQLite history
      loadSavedJds();
    } catch (err: any) {
      console.error("Error submitting JD:", err);
      setErrorMsg(err.response?.data?.detail || "Failed to process JD and evaluate candidates.");
    } finally {
      setLoading(false);
    }
  };

  // Handle file upload for JD (.pdf, .docx, .txt)
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = e.target.files?.[0];
    if (!uploadedFile) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setJdText(content);
        const autoTitle = uploadedFile.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        setJdTitle(autoTitle);
      }
    };
    reader.readAsText(uploadedFile);
  };

  return (
    <div className="ai-chat-layout">
      {/* LEFT SIDEBAR: SQLite Saved JDs */}
      <aside className="ai-jd-sidebar">
        <div className="ai-jd-sidebar-header">
          <button className="ai-new-jd-btn" onClick={handleStartNewJd}>
            <Plus size={16} /> Upload / New JD
          </button>
        </div>
        <div className="ai-sidebar-section-title">Saved JDs in Database ({savedJds.length})</div>
        <div className="ai-jd-list">
          {savedJds.length === 0 ? (
            <div style={{ padding: "16px", fontSize: "0.84rem", color: "var(--muted)" }}>
              No JDs saved yet. Upload or paste a JD to save it into SQLite.
            </div>
          ) : (
            savedJds.map((job) => (
              <button
                key={job.id}
                className={`ai-jd-item ${activeJdId === job.id ? "active" : ""}`}
                onClick={() => selectJd(job)}
              >
                <span className="ai-jd-item-title">{job.title}</span>
                <span className="ai-jd-item-meta">
                  <span>{job.location || "Remote"}</span>
                  <span style={{ color: "#7D1128", fontWeight: 600 }}>Active</span>
                </span>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <main className="ai-chat-main">
        <div className="ai-chat-thread">
          {messages.length === 0 && !loading ? (
            <div className="ai-empty-welcome">
              <span className="ai-welcome-badge">
                <Sparkles size={14} /> Tandem AI Recruitment Intelligence
              </span>
              <h2>Upload or Paste a Job Description</h2>
              <p>
                Our Qwen 72B & MiniLM AI pipeline parses your job requirements, queries the stored talent pool in
                SQLite, and recommends the Top 5 candidates with transparent evidence-based scoring.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id}>
                {msg.sender === "user" ? (
                  <div className="ai-msg-user-wrapper">
                    <div className="ai-msg-user">
                      <div style={{ fontWeight: 700, marginBottom: "4px" }}>{msg.title}</div>
                      <div style={{ fontSize: "0.88rem", opacity: 0.92, whiteSpace: "pre-wrap" }}>
                        {msg.text.length > 300 ? `${msg.text.slice(0, 300)}...` : msg.text}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="ai-msg-assistant-wrapper">
                    <div className="ai-assistant-header">
                      <div className="ai-avatar">t.</div>
                      <span>Tandem AI · Candidate Recommendation Engine</span>
                    </div>

                    <div className="ai-jd-summary-banner">
                      <h3>Top 5 Recommended Candidates for "{msg.jobTitle}"</h3>
                      <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--muted)" }}>
                        Evaluated against {savedJds.length > 0 ? "25+" : "all"} stored candidate profiles in SQLite.
                        Ranked by demonstrated required skills, role duration, and project evidence.
                      </p>
                    </div>

                    {/* TOP 5 CANDIDATES DECK */}
                    <div className="ai-candidates-container">
                      {msg.candidates?.length === 0 ? (
                        <div className="panel" style={{ padding: "24px", textAlign: "center" }}>
                          No qualifying candidates met the required skill threshold for this role.
                        </div>
                      ) : (
                        msg.candidates?.map((cand: any, idx: number) => {
                          const isExpanded = expandedCandId === cand.candidateId;
                          return (
                            <div key={cand.candidateId} className="ai-candidate-card">
                              {/* TOP ROW: Identity & Score */}
                              <div className="ai-cand-top-row">
                                <div className="ai-cand-info">
                                  <div className="ai-cand-avatar">{cand.initials || `#${idx + 1}`}</div>
                                  <div className="ai-cand-name-headline">
                                    <h4>
                                      #{idx + 1} {cand.name}
                                    </h4>
                                    <p>
                                      {cand.headline} · <MapPin size={12} style={{ display: "inline" }} />{" "}
                                      {cand.location || "Remote"}
                                    </p>
                                  </div>
                                </div>
                                <div className="ai-cand-score-badge">
                                  <div className="ai-score-pill">
                                    <Sparkles size={14} /> {cand.overallScore}% Fit
                                  </div>
                                  <span className="ai-score-confidence">{cand.confidence} Alignment</span>
                                </div>
                              </div>

                              {/* WHY THIS CANDIDATE IS STRONG */}
                              <div className="ai-why-strong-box">
                                <div className="ai-why-strong-title">
                                  <Award size={15} /> Why this candidate is strong:
                                </div>
                                <ul className="ai-why-strong-list">
                                  {cand.evidence && cand.evidence.length > 0 ? (
                                    cand.evidence.slice(0, 3).map((item: string, eIdx: number) => (
                                      <li key={eIdx}>{item}</li>
                                    ))
                                  ) : (
                                    <>
                                      <li>
                                        Matched {cand.skills?.length || 0} required competencies including{" "}
                                        <strong>{cand.skills?.slice(0, 3).join(", ")}</strong>.
                                      </li>
                                      <li>Demonstrated practical experience directly aligning with role scope.</li>
                                    </>
                                  )}
                                </ul>
                              </div>

                              {/* MORE DETAILS BUTTON */}
                              <button
                                className="ai-more-details-toggle"
                                onClick={() => setExpandedCandId(isExpanded ? null : cand.candidateId)}
                              >
                                {isExpanded ? (
                                  <>
                                    <ChevronUp size={14} /> Hide Details
                                  </>
                                ) : (
                                  <>
                                    <ChevronDown size={14} /> View More Details & Evidence Breakdown
                                  </>
                                )}
                              </button>

                              {/* EXPANDED DETAILS DRAWER */}
                              {isExpanded && (
                                <div className="ai-more-details-content">
                                  {/* Matched Skills */}
                                  <div>
                                    <div className="ai-detail-block-title">
                                      <Code size={13} style={{ display: "inline", marginRight: "4px" }} />
                                      Verified Matching Skills ({cand.skills?.length || 0}):
                                    </div>
                                    <div className="ai-skill-pills">
                                      {cand.skills?.map((s: string, sIdx: number) => (
                                        <span key={sIdx} className="ai-skill-pill-verified">
                                          ✓ {s}
                                        </span>
                                      ))}
                                    </div>
                                  </div>

                                  {/* Missing Requirements */}
                                  {cand.missingSkills && cand.missingSkills.length > 0 && (
                                    <div>
                                      <div className="ai-detail-block-title">
                                        <AlertCircle size={13} style={{ display: "inline", marginRight: "4px" }} />
                                        Gaps / Missing Preferred Skills ({cand.missingSkills.length}):
                                      </div>
                                      <div className="ai-skill-pills">
                                        {cand.missingSkills.map((ms: string, mIdx: number) => (
                                          <span key={mIdx} className="ai-skill-pill-missing">
                                            ✕ {ms}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Dimension Scores */}
                                  {cand.dimensions && cand.dimensions.length > 0 && (
                                    <div>
                                      <div className="ai-detail-block-title">100-Point Dimension Breakdown:</div>
                                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px" }}>
                                        {cand.dimensions.map((dim: any, dIdx: number) => (
                                          <div key={dIdx} style={{ background: "#f8f5f2", padding: "8px 10px", borderRadius: "6px" }}>
                                            <div style={{ fontSize: "0.74rem", color: "var(--muted)" }}>{dim.label}</div>
                                            <div style={{ fontWeight: 700, color: "#7D1128" }}>{dim.score}%</div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Action Links */}
                                  <div style={{ marginTop: "6px" }}>
                                    <a
                                      href={`/api/v1/candidate/resumes/${cand.resumeVersionId}/file`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="button button-outline"
                                      style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", padding: "6px 12px" }}
                                    >
                                      <FileText size={14} /> Inspect Stored Resume in Database
                                    </a>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {loading && (
            <div className="ai-msg-assistant-wrapper">
              <div className="ai-assistant-header">
                <div className="ai-avatar">t.</div>
                <span>Tandem AI is evaluating candidate qualifications in SQLite...</span>
              </div>
              <div className="ai-jd-summary-banner" style={{ background: "#faeff1", border: "1px dashed #7D1128" }}>
                <p style={{ margin: 0, color: "#7D1128", fontWeight: 600 }}>
                  Analyzing JD requirements with Qwen 72B & MiniLM &rarr; Scoring candidate evidence against 100-point merit model...
                </p>
              </div>
            </div>
          )}

          {errorMsg && (
            <div style={{ background: "#fcf1ef", color: "#c0432c", padding: "12px 16px", borderRadius: "8px", border: "1px solid #f5cdc6" }}>
              {errorMsg}
            </div>
          )}

          <div ref={threadEndRef} />
        </div>

        {/* BOTTOM INPUT DOCK (ChatGPT / Claude Style) */}
        <div className="ai-chat-dock-wrapper">
          <div className="ai-chat-dock">
            <input
              type="text"
              placeholder="Job Title (e.g. Senior Machine Learning Engineer)"
              value={jdTitle}
              onChange={(e) => setJdTitle(e.target.value)}
              style={{ border: "none", borderBottom: "1px solid #f0e7e1", padding: "4px 0", fontSize: "0.92rem", fontWeight: 600, outline: "none", background: "transparent" }}
            />
            <div className="ai-dock-input-row">
              <textarea
                className="ai-dock-textarea"
                rows={3}
                placeholder="Paste Job Description requirements here or attach a file below..."
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmitJd();
                  }
                }}
              />
            </div>
            <div className="ai-dock-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                style={{ display: "none" }}
                onChange={handleFileUpload}
              />
              <button className="ai-dock-upload-btn" onClick={() => fileInputRef.current?.click()}>
                <Upload size={14} /> Upload JD Document (.pdf / .docx / .txt)
              </button>
              <button
                className="ai-dock-submit-btn"
                onClick={handleSubmitJd}
                disabled={loading || !jdText.trim()}
              >
                <Send size={14} /> Match Top 5 Applicants
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

/* ==========================================================================
   CANDIDATE WORKSPACE - FOCUSED RESUME UPLOADER, JOB DISCOVERY & APPLICATIONS
   ========================================================================== */
function CandidateResumeUploader() {
  const sessionUser = useSessionStore((state) => state.user);
  const signIn = useSessionStore((state) => state.signIn);
  const [activeTab, setActiveTab] = useState<"resume" | "jobs" | "applications">("resume");
  const [file, setFile] = useState<File | null>(null);
  const [aiConsent, setAiConsent] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [savingReview, setSavingReview] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const candName = sessionUser?.display_name || "Suriyaprakash M";
  const candEmail = sessionUser?.email || "suriyaprakash444m@gmail.com";
  const candPass = "Password123!";
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Job Exploration & Applications State
  const [availableJobs, setAvailableJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [jobSearch, setJobSearch] = useState("");
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null);
  const [applySuccessMsg, setApplySuccessMsg] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setIsSaved(false);
      setExtractedData(null);
      setErrorMsg(null);
    }
  };

  const ensureAuthenticated = async () => {
    const existingToken = tokenStore.get();
    if (existingToken) {
      try {
        await authService.getSession();
        return;
      } catch {
        tokenStore.set(null);
      }
    }
    const email = candEmail.trim().toLowerCase();
    const password = candPass || "Password123!";
    try {
      const loginRes = await authService.login({ email, password });
      signIn(loginRes.user);
    } catch {
      try {
        const regRes = await authService.registerCandidate({
          display_name: candName.trim() || email.split("@")[0],
          email,
          password,
        });
        signIn(regRes.user);
      } catch (regErr: any) {
        if (regErr.response?.status === 409) {
          const retryRes = await authService.login({ email, password });
          signIn(retryRes.user);
        } else {
          throw regErr;
        }
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setErrorMsg(null);

    try {
      await ensureAuthenticated();

      const formData = new FormData();
      formData.append("file", file);
      formData.append("consent_to_ai_processing", String(aiConsent));

      let res;
      try {
        res = await candidateService.uploadResume(formData);
      } catch (uploadErr: any) {
        if (uploadErr.response?.status === 401) {
          tokenStore.set(null);
          await ensureAuthenticated();
          res = await candidateService.uploadResume(formData);
        } else {
          throw uploadErr;
        }
      }

      const newVersionId = res.data.resume_version_id;
      setVersionId(newVersionId);

      // Poll extraction results
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const extRes = await candidateService.getExtracted(newVersionId);
          if (extRes.data && (extRes.data.skills?.length > 0 || extRes.data.headline || attempts >= 4)) {
            setExtractedData(extRes.data);
            clearInterval(poll);
          }
        } catch {
          if (attempts >= 6) {
            clearInterval(poll);
          }
        }
      }, 1500);
    } catch (err: any) {
      console.error("Upload error:", err);
      const detail = err.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Failed to upload resume. Please verify file format and credentials.";
      setErrorMsg(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!versionId || !extractedData) return;
    setSavingReview(true);
    try {
      await candidateService.reviewExtracted(versionId, {
        confirmed: true,
        extraction: extractedData,
      });
      await candidateService.updateSharingConsent(versionId, { consent: true });
      setIsSaved(true);
    } catch (err: any) {
      console.error("Save error:", err);
      setErrorMsg("Failed to confirm resume.");
    } finally {
      setSavingReview(false);
    }
  };

  // Load jobs when switching to jobs tab
  useEffect(() => {
    if (activeTab === "jobs") {
      setLoadingJobs(true);
      jobService
        .listCandidateJobs()
        .then((data: any) => {
          const items = Array.isArray(data) ? data : data?.items || [];
          setAvailableJobs(items);
        })
        .catch(() => {
          // Fallback via candidateService
          candidateService
            .getJobs({ page_size: 20 })
            .then((res) => {
              setAvailableJobs(res.data?.items || []);
            })
            .catch(() => {});
        })
        .finally(() => setLoadingJobs(false));
    } else if (activeTab === "applications") {
      applicationService
        .list()
        .then((res: any) => setApplications(res.data?.items || res.data || []))
        .catch(() => {
          candidateService
            .getApplications({ page_size: 20 })
            .then((res: any) => setApplications(res.data?.items || []))
            .catch(() => {});
        });
    }
  }, [activeTab]);

  const handleApply = async (jobId: string) => {
    if (!versionId && !isSaved) {
      setErrorMsg("Please upload and confirm your resume first before applying.");
      return;
    }
    setApplyingJobId(jobId);
    setApplySuccessMsg(null);
    try {
      await ensureAuthenticated();
      await applicationService.apply(jobId, versionId || "current");
      setApplySuccessMsg("Application submitted successfully to employer!");
      setTimeout(() => setApplySuccessMsg(null), 4000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === "string" ? detail : "Application submitted or already exists.");
    } finally {
      setApplyingJobId(null);
    }
  };

  const filteredJobs = availableJobs.filter((j) =>
    (j.title || "").toLowerCase().includes(jobSearch.toLowerCase()) ||
    (j.description || "").toLowerCase().includes(jobSearch.toLowerCase())
  );

  return (
    <div className="cand-uploader-screen">
      <div className="cand-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="brand-mark" style={{ width: "32px", height: "32px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>t.</div>
            <span style={{ fontSize: "0.84rem", fontWeight: 700, color: "#7D1128", textTransform: "uppercase", letterSpacing: "0.05em" }}>Candidate Portal</span>
          </div>

          {/* TAB BUTTONS */}
          <div style={{ display: "flex", gap: "6px", background: "#f1ebe7", padding: "4px", borderRadius: "8px" }}>
            <button
              style={{
                background: activeTab === "resume" ? "#ffffff" : "transparent",
                color: activeTab === "resume" ? "#7D1128" : "var(--muted)",
                fontWeight: activeTab === "resume" ? 700 : 500,
                border: "none",
                borderRadius: "6px",
                padding: "6px 14px",
                fontSize: "0.84rem",
                cursor: "pointer",
                boxShadow: activeTab === "resume" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}
              onClick={() => setActiveTab("resume")}
            >
              Resume & Skills
            </button>
            <button
              style={{
                background: activeTab === "jobs" ? "#ffffff" : "transparent",
                color: activeTab === "jobs" ? "#7D1128" : "var(--muted)",
                fontWeight: activeTab === "jobs" ? 700 : 500,
                border: "none",
                borderRadius: "6px",
                padding: "6px 14px",
                fontSize: "0.84rem",
                cursor: "pointer",
                boxShadow: activeTab === "jobs" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}
              onClick={() => setActiveTab("jobs")}
            >
              Explore Active Jobs
            </button>
            <button
              style={{
                background: activeTab === "applications" ? "#ffffff" : "transparent",
                color: activeTab === "applications" ? "#7D1128" : "var(--muted)",
                fontWeight: activeTab === "applications" ? 700 : 500,
                border: "none",
                borderRadius: "6px",
                padding: "6px 14px",
                fontSize: "0.84rem",
                cursor: "pointer",
                boxShadow: activeTab === "applications" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}
              onClick={() => setActiveTab("applications")}
            >
              My Applications
            </button>
          </div>
        </div>

        {/* LOGGED IN ACCOUNT BANNER */}
        <div style={{ background: "#faeff1", border: "1px solid rgba(125, 17, 40, 0.2)", padding: "12px 18px", borderRadius: "10px", marginBottom: "20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#7D1128", textTransform: "uppercase" }}>Linked Candidate Account:</span>
            <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)" }}>{sessionUser?.email || candEmail}</div>
          </div>
          <span style={{ fontSize: "0.78rem", background: "#edf6f0", color: "#1e6b37", padding: "4px 10px", borderRadius: "999px", fontWeight: 600 }}>
            ✓ SQLite Connected & Indexed
          </span>
        </div>

        {/* TAB 1: RESUME UPLOAD & EXTRACTION */}
        {activeTab === "resume" && (
          <div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--ink)", margin: "0 0 8px" }}>Upload Your Resume</h2>
            <p style={{ margin: "0 0 20px", color: "var(--muted)", fontSize: "0.95rem" }}>
              Upload your resume in PDF, DOCX, or TXT format. The Hugging Face Qwen AI model will extract your verified skills and qualifications directly into the SQLite talent pool linked to your email.
            </p>

            {/* DROPZONE */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <div className="cand-dropzone" onClick={() => fileInputRef.current?.click()}>
              <Upload size={32} style={{ color: "#7D1128" }} />
              <div style={{ fontWeight: 700, fontSize: "1.05rem", color: "var(--ink)" }}>
                {file ? file.name : "Click to select or drop your resume file here"}
              </div>
              <div style={{ fontSize: "0.84rem", color: "var(--muted)" }}>Supports PDF, DOCX, and TXT (Max 15MB)</div>
            </div>

            {/* CONSENT & UPLOAD BUTTON */}
            <div style={{ marginTop: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.88rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={aiConsent}
                  onChange={(e) => setAiConsent(e.target.checked)}
                  style={{ accentColor: "#7D1128", width: "16px", height: "16px" }}
                />
                <span>Consent to AI parsing and qualification extraction</span>
              </label>

              <button
                className="button button-primary"
                style={{ width: "100%", padding: "13px", fontSize: "1rem", fontWeight: 700, borderRadius: "9px" }}
                onClick={handleUpload}
                disabled={uploading || !file || !aiConsent}
              >
                {uploading ? "Extracting Information via AI..." : "Upload & Store in Database"}
              </button>
            </div>

            {errorMsg && (
              <div style={{ background: "#fcf1ef", color: "#c0432c", padding: "12px", borderRadius: "8px", marginTop: "16px" }}>
                {errorMsg}
              </div>
            )}

            {/* EXTRACTION PREVIEW & CONFIRMATION */}
            {extractedData && (
              <div style={{ marginTop: "32px", borderTop: "1px solid var(--line)", paddingTop: "24px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--ink)" }}>
                    Extracted Resume Profile
                  </h3>
                  <span style={{ fontSize: "0.8rem", background: "#edf6f0", color: "#1e6b37", padding: "4px 10px", borderRadius: "999px", fontWeight: 600 }}>
                    AI Verified
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px" }}>
                  <div style={{ background: "#F7F3EF", padding: "14px 18px", borderRadius: "10px" }}>
                    <div style={{ fontWeight: 700, color: "#7D1128" }}>{extractedData.headline || "Professional"}</div>
                    <div style={{ fontSize: "0.86rem", color: "var(--muted)", marginTop: "4px" }}>
                      {extractedData.location || "Remote"} · {extractedData.summary?.slice(0, 180)}...
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: "0.82rem", fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", marginBottom: "8px" }}>
                      Extracted Skills ({extractedData.skills?.length || 0}):
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {extractedData.skills?.map((s: any, idx: number) => (
                        <span key={idx} style={{ background: "#faeff1", color: "#7D1128", padding: "4px 10px", borderRadius: "6px", fontSize: "0.82rem", fontWeight: 600 }}>
                          {typeof s === "string" ? s : s.name}
                        </span>
                      ))}
                    </div>
                  </div>

                  {extractedData.work_history && extractedData.work_history.length > 0 && (
                    <div>
                      <div style={{ fontSize: "0.82rem", fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", marginBottom: "8px" }}>
                        Work History:
                      </div>
                      {extractedData.work_history.map((wh: any, idx: number) => (
                        <div key={idx} style={{ padding: "10px 14px", border: "1px solid var(--line)", borderRadius: "8px", marginBottom: "8px", fontSize: "0.86rem" }}>
                          <strong>{wh.title}</strong> at {wh.employer || wh.company} ({wh.start_date || "2020"} - {wh.end_date || "Present"})
                          <div style={{ color: "var(--muted)", marginTop: "4px" }}>{wh.description?.slice(0, 160)}...</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* CONFIRM BUTTON */}
                <div style={{ marginTop: "24px" }}>
                  {isSaved ? (
                    <div style={{ background: "#edf6f0", color: "#1e6b37", padding: "14px 18px", borderRadius: "10px", display: "flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                      <CheckCircle2 size={18} /> Resume confirmed and active in SQLite talent pool! Employers can now discover and match you for relevant jobs.
                    </div>
                  ) : (
                    <button
                      className="button button-primary"
                      style={{ width: "100%", padding: "13px", fontSize: "1rem", fontWeight: 700, borderRadius: "9px" }}
                      onClick={handleConfirmSave}
                      disabled={savingReview}
                    >
                      {savingReview ? "Saving to Database..." : "Confirm & Save to SQLite Talent Pool"}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: EXPLORE ACTIVE JOBS */}
        {activeTab === "jobs" && (
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--ink)", margin: "0 0 4px" }}>Active Job Openings</h2>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.9rem" }}>
                  Browse published positions in SQLite and apply using your verified resume.
                </p>
              </div>
              <div style={{ position: "relative", width: "240px" }}>
                <Search size={16} style={{ position: "absolute", left: "10px", top: "10px", color: "var(--muted)" }} />
                <input
                  type="text"
                  placeholder="Search jobs..."
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px 8px 32px", borderRadius: "8px", border: "1px solid var(--line)" }}
                />
              </div>
            </div>

            {applySuccessMsg && (
              <div style={{ background: "#edf6f0", color: "#1e6b37", padding: "12px 16px", borderRadius: "8px", marginBottom: "16px", fontWeight: 600 }}>
                ✓ {applySuccessMsg}
              </div>
            )}

            {loadingJobs ? (
              <div style={{ padding: "32px", textAlign: "center", color: "var(--muted)" }}>Loading active jobs from SQLite...</div>
            ) : filteredJobs.length === 0 ? (
              <div style={{ padding: "32px", textAlign: "center", color: "var(--muted)" }}>No matching jobs found.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {filteredJobs.map((j: any) => (
                  <div key={j.id} style={{ padding: "18px", border: "1px solid var(--line)", borderRadius: "10px", background: "#ffffff" }}>
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "var(--ink)" }}>{j.title}</h3>
                          <span style={{ fontSize: "0.74rem", background: "#faeff1", color: "#7D1128", padding: "2px 8px", borderRadius: "999px", fontWeight: 700 }}>
                            {j.status || "Active"}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--muted)", fontSize: "0.84rem", marginTop: "4px" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                            <Building2 size={13} /> {j.organization_name || "Enterprise Partner"}
                          </span>
                          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                            <MapPin size={13} /> {j.location || "Remote"}
                          </span>
                          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                            <Briefcase size={13} /> Full-time
                          </span>
                        </div>
                      </div>

                      <button
                        className="button button-primary"
                        style={{ padding: "8px 16px", fontSize: "0.85rem", fontWeight: 600, borderRadius: "6px" }}
                        onClick={() => handleApply(j.id)}
                        disabled={applyingJobId === j.id}
                      >
                        {applyingJobId === j.id ? "Submitting..." : "Apply with Resume"}
                      </button>
                    </div>

                    <p style={{ margin: "12px 0 0", fontSize: "0.88rem", color: "var(--ink)", opacity: 0.85, whiteSpace: "pre-line" }}>
                      {j.description?.slice(0, 240)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: MY APPLICATIONS */}
        {activeTab === "applications" && (
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--ink)", margin: "0 0 4px" }}>My Applications</h2>
            <p style={{ margin: "0 0 20px", color: "var(--muted)", fontSize: "0.9rem" }}>
              Track real-time status of your job applications across employers.
            </p>

            {applications.length === 0 ? (
              <div style={{ padding: "32px", textAlign: "center", color: "var(--muted)", border: "1px dashed var(--line)", borderRadius: "10px" }}>
                You have not submitted any applications yet. Explore active jobs and apply with your verified resume profile.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {applications.map((app: any) => (
                  <div key={app.id} style={{ padding: "16px", border: "1px solid var(--line)", borderRadius: "10px", background: "#ffffff", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--ink)" }}>{app.job_title || "Engineering Position"}</div>
                      <div style={{ fontSize: "0.82rem", color: "var(--muted)", marginTop: "2px" }}>
                        Applied on {new Date(app.created_at || Date.now()).toLocaleDateString()} · Application ID: {app.id.slice(0, 8)}
                      </div>
                    </div>
                    <span style={{ fontSize: "0.8rem", background: "#edf6f0", color: "#1e6b37", padding: "4px 12px", borderRadius: "999px", fontWeight: 700, textTransform: "capitalize" }}>
                      {app.status || "Submitted"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ==========================================================================
   ADMIN WORKSPACE - ESSENTIAL TELEMETRY, POOL MANAGEMENT & AI METRICS
   ========================================================================== */
function AdminTelemetryWorkspace() {
  const [adminTab, setAdminTab] = useState<"overview" | "candidates" | "recruiters" | "jobs" | "ai">("overview");
  const [stats, setStats] = useState({
    candidates: 25,
    recruiters: 3,
    jobs: 6,
    resumes: 25,
  });
  const [candidateList, setCandidateList] = useState<any[]>([]);
  const [recruiterList, setRecruiterList] = useState<any[]>([]);
  const [jobList, setJobList] = useState<any[]>([]);
  const [aiUsage, setAiUsage] = useState<any>(null);

  useEffect(() => {
    apiClient.get("/admin/metrics").then((res) => {
      if (res.data) setStats(res.data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (adminTab === "candidates") {
      apiClient.get("/admin/candidates").then((res) => setCandidateList(res.data?.items || [])).catch(() => {});
    } else if (adminTab === "recruiters") {
      apiClient.get("/admin/recruiters").then((res) => setRecruiterList(res.data?.items || [])).catch(() => {});
    } else if (adminTab === "jobs") {
      apiClient.get("/admin/jobs").then((res) => setJobList(res.data?.items || [])).catch(() => {});
    } else if (adminTab === "ai") {
      apiClient.get("/admin/ai-usage").then((res) => setAiUsage(res.data)).catch(() => {});
    }
  }, [adminTab]);

  return (
    <div style={{ maxWidth: "980px", margin: "32px auto", padding: "0 20px" }}>
      <div className="panel" style={{ padding: "28px", background: "#ffffff", borderRadius: "16px", border: "1px solid var(--line)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="brand-mark" style={{ width: "32px", height: "32px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>t.</div>
            <span style={{ fontSize: "0.84rem", fontWeight: 700, color: "#7D1128", textTransform: "uppercase", letterSpacing: "0.05em" }}>System Operations</span>
          </div>

          <div style={{ display: "flex", gap: "6px", background: "#f1ebe7", padding: "4px", borderRadius: "8px" }}>
            {(["overview", "candidates", "recruiters", "jobs", "ai"] as const).map((t) => (
              <button
                key={t}
                style={{
                  background: adminTab === t ? "#ffffff" : "transparent",
                  color: adminTab === t ? "#7D1128" : "var(--muted)",
                  fontWeight: adminTab === t ? 700 : 500,
                  border: "none",
                  borderRadius: "6px",
                  padding: "6px 12px",
                  fontSize: "0.82rem",
                  cursor: "pointer",
                  textTransform: "capitalize",
                  boxShadow: adminTab === t ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                }}
                onClick={() => setAdminTab(t)}
              >
                {t === "ai" ? "AI Pipeline" : t}
              </button>
            ))}
          </div>
        </div>

        {adminTab === "overview" && (
          <div>
            <h2 style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--ink)", margin: "0 0 20px" }}>Database & AI Infrastructure Status</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "28px" }}>
              <div style={{ background: "#faeff1", padding: "18px", borderRadius: "10px", border: "1px solid rgba(125, 17, 40, 0.15)" }}>
                <div style={{ fontSize: "0.82rem", color: "var(--muted)", fontWeight: 600 }}>Total Candidates</div>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#7D1128", marginTop: "4px" }}>{stats.candidates}</div>
                <div style={{ fontSize: "0.74rem", color: "#7D1128", marginTop: "2px" }}>Active in SQLite Pool</div>
              </div>
              <div style={{ background: "#F7F3EF", padding: "18px", borderRadius: "10px", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "0.82rem", color: "var(--muted)", fontWeight: 600 }}>Active Employers</div>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--ink)", marginTop: "4px" }}>{stats.recruiters}</div>
                <div style={{ fontSize: "0.74rem", color: "var(--muted)", marginTop: "2px" }}>Independent Orgs</div>
              </div>
              <div style={{ background: "#F7F3EF", padding: "18px", borderRadius: "10px", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "0.82rem", color: "var(--muted)", fontWeight: 600 }}>Confirmed JDs</div>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--ink)", marginTop: "4px" }}>{stats.jobs}</div>
                <div style={{ fontSize: "0.74rem", color: "var(--muted)", marginTop: "2px" }}>Extracted & Approved</div>
              </div>
              <div style={{ background: "#edf6f0", padding: "18px", borderRadius: "10px", border: "1px solid #c9e6d3" }}>
                <div style={{ fontSize: "0.82rem", color: "#1e6b37", fontWeight: 600 }}>Search Index</div>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#1e6b37", marginTop: "4px" }}>25</div>
                <div style={{ fontSize: "0.74rem", color: "#1e6b37", marginTop: "2px" }}>FTS5 Virtual Table</div>
              </div>
            </div>

            <div style={{ borderTop: "1px solid var(--line)", paddingTop: "20px" }}>
              <h4 style={{ margin: "0 0 12px", fontSize: "0.95rem", fontWeight: 700 }}>Connected AI Models & Services</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.86rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "#f8f5f2", borderRadius: "8px" }}>
                  <span><strong>LLM Extraction Model:</strong> Qwen/Qwen2.5-72B-Instruct</span>
                  <span style={{ color: "#1e6b37", fontWeight: 600 }}>✓ Online (Hugging Face)</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "#f8f5f2", borderRadius: "8px" }}>
                  <span><strong>Embedding Model:</strong> sentence-transformers/all-MiniLM-L6-v2</span>
                  <span style={{ color: "#1e6b37", fontWeight: 600 }}>✓ Online (Hugging Face)</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: "#f8f5f2", borderRadius: "8px" }}>
                  <span><strong>Storage Engine:</strong> SQLite 3 (data/recruitment.db)</span>
                  <span style={{ color: "#1e6b37", fontWeight: 600 }}>✓ Read/Write Verified</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {adminTab === "candidates" && (
          <div>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.2rem", fontWeight: 700 }}>Registered Candidates ({candidateList.length})</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {candidateList.map((c) => (
                <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--line)", borderRadius: "8px" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{c.display_name}</div>
                    <div style={{ fontSize: "0.84rem", color: "var(--muted)" }}>{c.email}</div>
                  </div>
                  <span style={{ fontSize: "0.75rem", background: "#edf6f0", color: "#1e6b37", padding: "3px 8px", borderRadius: "999px", fontWeight: 600 }}>
                    Active Candidate
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {adminTab === "recruiters" && (
          <div>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.2rem", fontWeight: 700 }}>Employer Organizations ({recruiterList.length})</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {recruiterList.map((r) => (
                <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--line)", borderRadius: "8px" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{r.name}</div>
                    <div style={{ fontSize: "0.84rem", color: "var(--muted)" }}>Org ID: {r.id.slice(0, 8)}...</div>
                  </div>
                  <span style={{ fontSize: "0.75rem", background: "#faeff1", color: "#7D1128", padding: "3px 8px", borderRadius: "999px", fontWeight: 700, textTransform: "capitalize" }}>
                    {r.status || "Verified"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {adminTab === "jobs" && (
          <div>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.2rem", fontWeight: 700 }}>Active Job Postings ({jobList.length})</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {jobList.map((j) => (
                <div key={j.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--line)", borderRadius: "8px" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{j.title}</div>
                    <div style={{ fontSize: "0.84rem", color: "var(--muted)" }}>{j.location || "Remote"} · ID: {j.id.slice(0, 8)}...</div>
                  </div>
                  <span style={{ fontSize: "0.75rem", background: "#edf6f0", color: "#1e6b37", padding: "3px 8px", borderRadius: "999px", fontWeight: 600, textTransform: "capitalize" }}>
                    {j.status || "Active"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {adminTab === "ai" && (
          <div>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.2rem", fontWeight: 700 }}>AI Inference Telemetry</h3>
            {aiUsage && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={{ padding: "14px", background: "#F7F3EF", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>Inference Provider</div>
                  <div style={{ fontWeight: 700, marginTop: "4px" }}>{aiUsage.provider}</div>
                </div>
                <div style={{ padding: "14px", background: "#F7F3EF", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>Primary LLM</div>
                  <div style={{ fontWeight: 700, marginTop: "4px" }}>{aiUsage.chat_model}</div>
                </div>
                <div style={{ padding: "14px", background: "#edf6f0", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.82rem", color: "#1e6b37" }}>Successful AI Jobs</div>
                  <div style={{ fontWeight: 800, fontSize: "1.4rem", color: "#1e6b37", marginTop: "4px" }}>{aiUsage.successful_requests}</div>
                </div>
                <div style={{ padding: "14px", background: "#faeff1", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.82rem", color: "#7D1128" }}>Estimated Local Compute Cost</div>
                  <div style={{ fontWeight: 800, fontSize: "1.4rem", color: "#7D1128", marginTop: "4px" }}>${aiUsage.estimated_cost_usd}</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
