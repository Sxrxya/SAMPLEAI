import {
  ArrowLeft,
  ArrowRight,
  Check,
  LockKeyhole,
  Mail,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authSchema, type AuthInput } from "../schemas/auth";
import { authService } from "../services/authService";
import { useSessionStore } from "../store/session";
import type { Role } from "../types";

export function AuthPage() {
  const { role: roleParam = "candidate" } = useParams();
  const role = roleParam as Role;
  const navigate = useNavigate();
  const signIn = useSessionStore((state) => state.signIn);
  const [isRegister, setIsRegister] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AuthInput>({ resolver: zodResolver(authSchema) });

  const submit = handleSubmit(async (data) => {
    setLoading(true);
    setAuthError(null);
    try {
      if (isRegister) {
        await authService.register({
          display_name: data.name || data.email.split("@")[0],
          email: data.email,
          password: data.password,
        });
      } else {
        await authService.login({
          email: data.email,
          password: data.password,
        });
      }
      signIn(role);
      navigate(`/portal/${role}/overview`);
    } catch (err: any) {
      console.error("Auth error:", err);
      // If registration fails with conflict, try logging in
      if (isRegister && err.response?.status === 409) {
        try {
          await authService.login({ email: data.email, password: data.password });
          signIn(role);
          navigate(`/portal/${role}/overview`);
          return;
        } catch {
          // ignore
        }
      }
      setAuthError(err.response?.data?.detail || "Authentication failed. Make sure your password has at least 12 characters.");
    } finally {
      setLoading(false);
    }
  });

  return (
    <main className="auth-page">
      <Link className="brand-lockup auth-brand" to="/">
        <span className="brand-mark">t</span>
        <span>
          tandem<span className="brand-period">.</span>
        </span>
      </Link>
      <section className="auth-panel">
        <Link className="back-link" to="/">
          <ArrowLeft size={15} /> Back to home
        </Link>
        <span className="auth-symbol">
          <Sparkles size={19} />
        </span>
        <span className="eyebrow">
          {role === "candidate"
            ? "YOUR NEXT CHAPTER"
            : role === "recruiter"
              ? "BUILD YOUR TEAM"
              : "PLATFORM OPERATIONS"}
        </span>
        <h1>{isRegister ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-intro">
          {isRegister
            ? "Start with a workspace tailored to your role."
            : `Sign in to your ${role} workspace.`}
        </p>
        <form className="auth-form" onSubmit={submit} noValidate>
          {isRegister && (
            <label>
              Full name
              <input
                autoComplete="name"
                placeholder="Your name"
                {...register("name")}
              />
            </label>
          )}
          <label>
            Email address
            <span className="input-icon">
              <Mail size={16} />
              <input
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                {...register("email")}
              />
            </span>
            {errors.email && (
              <span className="form-error" role="alert">
                {errors.email.message}
              </span>
            )}
          </label>
          <label>
            Password
            <span className="input-icon">
              <LockKeyhole size={16} />
              <input
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                placeholder="At least 8 characters"
                {...register("password")}
              />
            </span>
            {errors.password && (
              <span className="form-error" role="alert">
                {errors.password.message}
              </span>
            )}
          </label>
          {authError && (
            <div className="form-error" style={{ marginBottom: "0.75rem", color: "var(--danger, #e53e3e)", fontSize: "0.85rem" }}>
              {authError}
            </div>
          )}
          <button className="button button-primary auth-submit" type="submit" disabled={loading}>
            {loading ? "Signing in..." : isRegister ? "Create account" : "Continue"}{" "}
            <ArrowRight size={16} />
          </button>
        </form>
        <p className="auth-toggle">
          {isRegister ? "Already have an account?" : "New to Tandem?"}{" "}
          <button onClick={() => setIsRegister((value) => !value)}>
            {isRegister ? "Sign in" : "Create an account"}
          </button>
        </p>
        <div className="auth-divider">
          <span>DEMO ACCESS</span>
        </div>
        <button
          className="button button-outline auth-submit"
          onClick={() => {
            signIn(role);
            navigate(`/portal/${role}/overview`);
          }}
        >
          <Check size={15} /> Preview as {role}
        </button>
        <p className="auth-fineprint">
          Demo access is local only. Live sign-in requires a connected backend
          authentication service.
        </p>
      </section>
      <div className="auth-footer">
        Secure access <span>·</span> Candidate data stays private
      </div>
    </main>
  );
}
