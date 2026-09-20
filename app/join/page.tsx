"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/types";
import { Logo } from "@/components/ui";
export default function Join() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") || "");
  }, []);
  async function join() {
    setBusy(true);
    try {
      await api("/invitations/accept", "POST", { token });
      window.location.assign("/workspace");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <main className="account-page">
      <Logo />
      <section className="form-paper account-form">
        <h1>Join a shared pact.</h1>
        <p>
          Sign in with your own client or freelancer account, then accept this
          invitation. Your private brief stays yours.
        </p>
        <p>
          <a href={`/login/client?invite=${encodeURIComponent(token)}`}>
            Client sign-in
          </a>{" "}
          ·{" "}
          <a href={`/login/freelancer?invite=${encodeURIComponent(token)}`}>
            Freelancer sign-in
          </a>
        </p>
        <button
          className="btn primary"
          onClick={join}
          disabled={!token || busy}
        >
          {busy ? "Joining…" : "Accept invitation"}
        </button>
        {error && (
          <p role="alert" className="error-banner">
            {error}
          </p>
        )}
      </section>
    </main>
  );
}
