"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, type Role } from "@/lib/types";
import { Logo } from "./ui";
export default function AccountLogin({ role }: { role: Role }) {
  const [step, setStep] = useState<
    "login" | "register" | "confirm" | "forgot" | "reset"
  >("login");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [configured, setConfigured] = useState(false);
  useEffect(() => {
    api<{ configured: boolean }>("/auth/config")
      .then((x) => setConfigured(x.configured))
      .catch(() => setError("Sign-in is temporarily unavailable."));
  }, []);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const f = new FormData(e.currentTarget);
    try {
      const data = {
        email,
        password: f.get("password"),
        role,
        name: f.get("name"),
        code: f.get("code"),
      };
      await api(`/auth/${step}`, "POST", data);
      if (step === "login") {
        const invite = new URLSearchParams(window.location.search).get(
          "invite",
        );
        window.location.assign(
          invite ? `/join?token=${encodeURIComponent(invite)}` : "/workspace",
        );
      } else if (step === "register") {
        setStep("confirm");
        setNotice("Check your email for the verification code.");
      } else if (step === "forgot") {
        setStep("reset");
        setNotice(
          "If this account can be recovered, a code will arrive by email.",
        );
      } else {
        setStep("login");
        setNotice(
          step === "confirm"
            ? "Email verified. You can sign in now."
            : "Password reset. Sign in with your new password.",
        );
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const label = role === "client" ? "Client" : "Freelancer";
  return (
    <main className="account-page">
      <a href="/" aria-label="ProofPact home">
        <Logo />
      </a>
      <section className="form-paper account-form">
        <p className="eyebrow">{label} account</p>
        <h1>
          {step === "register"
            ? "Start with clear expectations."
            : step === "confirm"
              ? "Verify your email."
              : step === "forgot" || step === "reset"
                ? "Recover your account."
                : `Sign in as a ${label.toLowerCase()}.`}
        </h1>
        <p>
          {role === "client"
            ? "Tell your agent what you need, review the scope, and approve the delivered work."
            : "Give your agent your requirements, capacity and price limits. Agree on the scope before you build."}
        </p>
        <form onSubmit={submit}>
          <label className="field">
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              maxLength={254}
            />
          </label>
          {step === "register" && (
            <label className="field">
              Your name
              <input
                name="name"
                autoComplete="name"
                required
                minLength={2}
                maxLength={80}
              />
            </label>
          )}
          {(step === "confirm" || step === "reset") && (
            <label className="field">
              Email verification code
              <input
                name="code"
                autoComplete="one-time-code"
                required
                minLength={4}
                maxLength={16}
              />
            </label>
          )}
          {(step === "login" || step === "register" || step === "reset") && (
            <label className="field">
              {step === "reset" ? "New password" : "Password"}
              <input
                name="password"
                type="password"
                autoComplete={
                  step === "login" ? "current-password" : "new-password"
                }
                required
                minLength={step === "login" ? 1 : 12}
                maxLength={256}
              />
              {step !== "login" && (
                <small>
                  At least 12 characters, with uppercase, lowercase, a number
                  and a symbol.
                </small>
              )}
            </label>
          )}
          {error && (
            <p className="error-banner" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="demo-disclosure" role="status">
              {notice}
            </p>
          )}
          {!configured && (
            <p className="demo-disclosure">
              Account service is connecting. If this persists, please try again
              later.
            </p>
          )}
          <button className="btn primary" disabled={busy || !configured}>
            {busy
              ? "Please wait…"
              : step === "login"
                ? "Sign in"
                : step === "register"
                  ? "Create account"
                  : step === "confirm"
                    ? "Verify email"
                    : step === "forgot"
                      ? "Send recovery code"
                      : "Reset password"}
          </button>
        </form>
        <div className="account-links">
          {step !== "login" && (
            <button
              onClick={() => {
                setStep("login");
                setError("");
              }}
            >
              Back to sign in
            </button>
          )}
          {step === "login" && (
            <>
              <button onClick={() => setStep("register")}>
                Create a {label.toLowerCase()} account
              </button>
              <button onClick={() => setStep("forgot")}>
                Forgot password?
              </button>
              <button onClick={() => setStep("confirm")}>
                Verify an existing account
              </button>
            </>
          )}
          {step === "confirm" && (
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/auth/resend", "POST", { email });
                  setNotice("A new code has been requested.");
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Resend verification code
            </button>
          )}
        </div>
        <p className="demo-disclosure">
          Your role is fixed for this account. The other participant has a
          separate sign-in and private brief.
        </p>
        <a href={role === "client" ? "/login/freelancer" : "/login/client"}>
          Use {role === "client" ? "freelancer" : "client"} sign-in instead
        </a>
        <p>
          <a href="/workspace?demo=1">Try the separate demo workspace</a>
        </p>
      </section>
    </main>
  );
}
