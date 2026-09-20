"use client";
import { useEffect, useState } from "react";
import { Bot, KeyRound, ShieldCheck } from "lucide-react";
import { api, type Pact, type Role } from "@/lib/types";
import { Badge } from "./ui";

type Access = { active: boolean; expires?: number; scopes?: string[] };
type Task = {
  id: string;
  status: { state: string; message?: { parts: { text?: string }[] } };
  artifacts?: {
    parts: { data?: { name: string; state: string; hash: string } }[];
  }[];
};
export default function AgentAccess({
  pact,
  role,
}: {
  pact: Pact;
  role: Role;
}) {
  const [access, setAccess] = useState<Access>({ active: false });
  const [token, setToken] = useState("");
  const [allowWork, setAllowWork] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [task, setTask] = useState<Task | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let current = true;
    api<Access>(`/projects/${pact.id}/agent-access`)
      .then((a) => {
        if (current) setAccess(a);
      })
      .catch((e) => {
        if (current) setError(e.message);
      })
      .finally(() => {
        if (current) setLoaded(true);
      });
    return () => {
      current = false;
    };
  }, [pact.id]);
  async function issue() {
    setBusy(true);
    setError("");
    setCopied(false);
    setTask(null);
    try {
      const a = await api<Access & { token: string }>(
        `/projects/${pact.id}/agent-access`,
        "POST",
        { allow_work: allowWork },
      );
      setToken(a.token);
      setAccess({ ...a, active: true });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function revoke() {
    setBusy(true);
    setError("");
    try {
      await api(`/projects/${pact.id}/agent-access`, "DELETE");
      setToken("");
      setTask(null);
      setAccess({ active: false });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function testConnection() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/a2a", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "A2A-Version": "1.0",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: crypto.randomUUID(),
          method: "SendMessage",
          params: {
            message: {
              messageId: crypto.randomUUID(),
              role: "ROLE_USER",
              contextId: pact.id,
              parts: [{ data: { action: "get_pact" } }],
            },
          },
        }),
      });
      const data = await response.json();
      if (!response.ok || data.error)
        throw new Error(
          data.error?.message || data.detail || "Connection failed",
        );
      setTask(data.result.task);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const result = task?.artifacts?.[0]?.parts?.[0]?.data;
  return (
    <div className="two-column">
      <section className="form-paper">
        <Badge tone="violet">A2A 1.0 · Agent connection</Badge>
        <h2>Bring your agent. Keep your say.</h2>
        <p>
          Connect an external agent to this pact as the {role}. Its access is
          limited to the permissions you choose and expires within one hour.
        </p>
        <div className="verification-header">
          <Bot size={24} />
          <div>
            <strong>{pact.name}</strong>
            <small>
              {loaded
                ? access.active
                  ? "Agent access is active"
                  : "No active agent access"
                : "Checking access…"}
            </small>
          </div>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={allowWork}
            onChange={(e) => setAllowWork(e.target.checked)}
            disabled={busy}
          />
          <span>
            Allow proposal requests, delivery verification, and{" "}
            {role === "builder" ? "delivery submission" : "scope-change checks"}
            . Leave unchecked for read-only access.
          </span>
        </label>
        <div className="change-options">
          <button
            className="btn primary"
            disabled={busy || !loaded}
            onClick={issue}
          >
            <KeyRound size={16} />
            {access.active ? "Replace access key" : "Create access key"}
          </button>
          {access.active && (
            <button className="btn" disabled={busy} onClick={revoke}>
              Revoke access
            </button>
          )}
        </div>
        {access.active && (
          <p className="demo-disclosure">
            Permissions:{" "}
            {access.scopes?.map((s) => s.replaceAll("_", " ")).join(", ")}.{" "}
            {access.expires &&
              `Expires ${new Date(access.expires * 1000).toLocaleTimeString()}.`}{" "}
            Replacing or revoking a key blocks future requests; work already
            running may finish.
          </p>
        )}
        {token && (
          <div className="agent-key-panel">
            <p>
              This key is shown only now. Store it in your agent’s secret
              settings. It is not saved in this browser.
            </p>
            <label htmlFor="agent-token">Agent access key</label>
            <input
              id="agent-token"
              type="password"
              readOnly
              value={token}
              autoComplete="off"
              spellCheck={false}
            />
            <div className="change-options">
              <button
                className="btn"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(token);
                    setCopied(true);
                  } catch {
                    setError(
                      "Copy failed. Select the key field to copy it manually.",
                    );
                  }
                }}
              >
                {copied ? "Copied" : "Copy key"}
              </button>
              <button className="btn" disabled={busy} onClick={testConnection}>
                Test connection
              </button>
              <button className="btn" onClick={() => setToken("")}>
                Hide key
              </button>
            </div>
          </div>
        )}
        {task && (
          <div className="demo-disclosure" role="status">
            <strong>
              {task.status.state === "TASK_STATE_COMPLETED"
                ? "Agent connection verified"
                : "Agent task needs attention"}
            </strong>
            <p>
              {result
                ? `${result.name} · ${result.state.replaceAll("_", " ")}`
                : task.status.message?.parts.map((p) => p.text).join(" ")}
            </p>
            <p className="mono wrap">Task {task.id}</p>
            <p>
              This check used a real A2A request to read this pact. It did not
              change the agreement.
            </p>
          </div>
        )}
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
      </section>
      <aside className="form-paper">
        <ShieldCheck size={28} />
        <h3>You approve the commitments.</h3>
        <p>
          Agents cannot approve agreements or amendments, accept manual checks,
          publish receipts, or release money. Private briefs and payment details
          are never returned through this connection.
        </p>
        <h3>Connect an A2A client</h3>
        <p>
          Discover the agent, supply the access key as a Bearer token, and send
          structured commands using A2A version 1.0.
        </p>
        <p>
          <a
            href="/.well-known/agent-card.json"
            target="_blank"
            rel="noreferrer"
          >
            View Agent Card ↗
          </a>
        </p>
        <p>
          <a
            href="https://github.com/himanshu748/proofpact/blob/main/docs/a2a.md"
            target="_blank"
            rel="noreferrer"
          >
            Connection guide and examples ↗
          </a>
        </p>
        <p className="demo-disclosure">
          Demo participants are synthetic. The A2A connection works, but this is
          not production identity verification. Streaming and push notifications
          are not supported.
        </p>
      </aside>
    </div>
  );
}
