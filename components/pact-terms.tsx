"use client";
import { useState } from "react";
import { api, type Pact, type Role } from "@/lib/types";
export default function PactTerms({
  pact,
  role,
  update,
}: {
  pact: Pact;
  role: Role;
  update: (p: Pact) => void;
}) {
  const [invite, setInvite] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState("");
  const [ids, setIds] = useState<string[]>([]);
  const a = pact.current;
  const revision = a?.revision_policy;
  const end =
    pact.first_delivery_at && revision
      ? new Date(
          new Date(pact.first_delivery_at).getTime() + revision.days * 86400000,
        )
      : null;
  return (
    <div className="two-column">
      <section className="form-paper">
        <h2>Define what done means.</h2>
        <p>
          These terms are part of the version both people approve. A proposed
          addition stays separate until both accept it.
        </p>
        <h3>Deliverables</h3>
        <ul>
          {(a?.included || pact.requirements).map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <h3>Acceptance criteria</h3>
        <ul>
          {(
            a?.criteria.map((c) => c.description) ||
            pact.acceptance_criteria ||
            []
          ).map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <h3>Who approves?</h3>
        <p>
          Both participants approve the agreement.{" "}
          {a?.delivery_approver?.name || pact.client} (client) reviews delivery
          and accepts manual checks.
        </p>
        <h3>Revision window</h3>
        <p>
          {a && !revision
            ? "This older agreement has no revision window. Propose an amendment for both participants to approve."
            : `${revision?.days || pact.revision_days || 7} days from the first delivery submission. Corrections must reference agreed criteria; new features require an amendment.`}
        </p>
        {end && <p>Revision requests close {end.toLocaleString()}.</p>}
        <p className="demo-disclosure">
          The window ending does not approve the work or release a payment.
        </p>
        {role === "client" &&
          a &&
          end &&
          ["SUBMITTED", "NEEDS_FIX", "NEEDS_HUMAN_REVIEW", "VERIFIED"].includes(
            pact.state,
          ) && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                try {
                  update(
                    await api<Pact>(`/projects/${pact.id}/revisions`, "POST", {
                      criterion_ids: ids,
                      notes,
                    }),
                  );
                  setNotes("");
                  setIds([]);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <h3>Request a correction</h3>
              {a.criteria.map((c) => (
                <label className="check-label" key={c.id}>
                  <input
                    type="checkbox"
                    checked={ids.includes(c.id)}
                    onChange={(e) =>
                      setIds(
                        e.target.checked
                          ? [...ids, c.id]
                          : ids.filter((x) => x !== c.id),
                      )
                    }
                  />
                  {c.title}
                </label>
              ))}
              <label className="field">
                What needs correcting?
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  required
                  minLength={5}
                  maxLength={2000}
                />
              </label>
              <button
                className="btn primary"
                disabled={busy || !ids.length || new Date() > end}
              >
                Request revision
              </button>
            </form>
          )}
        {(pact.revisions || []).map((r) => (
          <div className="demo-disclosure" key={r.id}>
            <strong>Revision requested</strong>
            <p>{r.notes}</p>
          </div>
        ))}
      </section>
      <aside className="form-paper">
        <h3>Two people. Separate accounts.</h3>
        {pact.identity_mode === "account" ? (
          <>
            <p>
              Client:{" "}
              {pact.participants_joined?.client
                ? "Joined"
                : "Invitation needed"}
            </p>
            <p>
              Freelancer:{" "}
              {pact.participants_joined?.builder
                ? "Joined"
                : "Invitation needed"}
            </p>
            {!Object.values(pact.participants_joined || {}).every(Boolean) && (
              <button
                className="btn"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    const r = await api<{ token: string }>(
                      `/projects/${pact.id}/invite`,
                      "POST",
                    );
                    setInvite(
                      `${window.location.origin}/join?token=${encodeURIComponent(r.token)}`,
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Create invitation link
              </button>
            )}
            {invite && (
              <label className="field">
                Share this with the other participant
                <textarea readOnly value={invite} />
                <small>
                  Single-use invitation, valid for seven days. Anyone with this
                  link and the matching role can join until claimed.
                </small>
              </label>
            )}
            <button className="btn" onClick={() => window.location.reload()}>
              Refresh participant status
            </button>
          </>
        ) : (
          <p>
            This is the synthetic demo. <a href="/login/client">Sign in</a> to
            create a pact with another person.
          </p>
        )}
        <p>
          Your private budget, availability and notes are only available to you
          and your advocate.
        </p>
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
      </aside>
    </div>
  );
}
